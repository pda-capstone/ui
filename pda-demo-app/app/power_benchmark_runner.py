# power_benchmark_runner.py
# Runs INA219 or simulated power benchmarks on a background thread.
# Falls back to simulated readings on non-Pi hardware (Mac development).
# Owner: Camellia Tran
# Last updated: August 2026


import csv
import os
import random
import subprocess
import sys
import threading
import time
from pathlib import Path

from gi.repository import GLib

from app.governor_controller import GovernorControllerError


DEFAULT_INA219_SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "power"
    / "hardware"
    / "ina219"
    / "ina219_sample.py"
)
MOCK_SAMPLE_RATE_HZ = 4
INA219_CURRENT_LIMIT_MA = 3200.0


class PowerBenchmarkRunnerError(RuntimeError):
    """
    Base exception for recoverable benchmark runner failures.
    """


class BenchmarkUnavailableError(PowerBenchmarkRunnerError):
    """
    Report that neither live nor simulated benchmark execution is available.
    """


class BenchmarkAlreadyRunningError(PowerBenchmarkRunnerError):
    """
    Report that a benchmark is already active.
    """


def get_default_ina219_script():
    """
    Return the configured INA219 script path.

    PDA_INA219_SCRIPT can override the default sibling-repository layout.
    """
    configured_path = os.environ.get("PDA_INA219_SCRIPT")

    if configured_path:
        return Path(configured_path).expanduser()

    return DEFAULT_INA219_SCRIPT


def parse_benchmark_csv(csv_path):
    """
    Parse an INA219 CSV file and return summary statistics.

    Raises:
        PowerBenchmarkRunnerError: If the file cannot be read or contains no
            valid samples.
    """
    watts_values = []
    voltage_values = []
    clipped = False

    try:
        with csv_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as csv_file:
            reader = csv.DictReader(csv_file)

            for row in reader:
                try:
                    power_mw = float(row["power_mW"])
                    voltage_v = float(row["voltage_V"])
                    current_ma = float(row["current_mA"])
                except (KeyError, TypeError, ValueError):
                    continue

                watts_values.append(power_mw / 1000.0)
                voltage_values.append(voltage_v)

                if current_ma >= INA219_CURRENT_LIMIT_MA:
                    clipped = True
    except OSError as error:
        raise PowerBenchmarkRunnerError(
            f"Could not read benchmark CSV '{csv_path}': {error}"
        ) from error

    if not watts_values:
        raise PowerBenchmarkRunnerError(
            f"No valid readings were found in '{csv_path}'. "
            "Check the INA219 connection and CSV column names."
        )

    return {
        "average_watts": sum(watts_values) / len(watts_values),
        "min_watts": min(watts_values),
        "max_watts": max(watts_values),
        "average_voltage": sum(voltage_values) / len(voltage_values),
        "sample_count": len(watts_values),
        "clipped": clipped,
    }


def create_mock_result(request):
    """
    Return plausible simulated readings for development systems.
    """
    base_watts = {
        "powersave": 1.8,
        "schedutil": 2.3,
        "performance": 2.9,
    }.get(request.governor, 2.3)

    workload_factor = {
        "idle": 0.80,
        "display": 1.10,
        "peripheral": 1.35,
    }.get(request.workload, 1.0)

    expected_average = base_watts * workload_factor
    average_watts = expected_average + random.uniform(-0.05, 0.05)

    return {
        "average_watts": round(average_watts, 2),
        "min_watts": round(expected_average * 0.88, 2),
        "max_watts": round(expected_average * 1.12, 2),
        "average_voltage": 4.97,
        "sample_count": (request.duration_seconds * MOCK_SAMPLE_RATE_HZ),
        "clipped": False,
    }


def write_mock_csv(csv_path, statistics):
    """
    Write simulated samples so development runs still produce a CSV file.
    """
    try:
        with csv_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["voltage_V", "current_mA", "power_mW"])

            for _sample_index in range(statistics["sample_count"]):
                voltage_v = statistics["average_voltage"]
                power_watts = statistics["average_watts"] + random.uniform(
                    -0.05,
                    0.05,
                )
                current_ma = (power_watts / voltage_v) * 1000.0

                writer.writerow(
                    [
                        f"{voltage_v:.4f}",
                        f"{current_ma:.2f}",
                        f"{power_watts * 1000.0:.2f}",
                    ]
                )
    except OSError as error:
        raise PowerBenchmarkRunnerError(
            f"Could not write simulated CSV '{csv_path}': {error}"
        ) from error


class PowerBenchmarkRunner:
    """
    Execute one power benchmark at a time on a background thread.
    """

    def __init__(
        self,
        governor_controller,
        ina219_script=None,
        allow_mock=True,
        status_dispatcher=None,
    ):
        """
        Initialize the runner and its injected dependencies.

        Args:
            governor_controller: Shared GovernorController instance.
            ina219_script: Optional path to the INA219 sampling script.
            allow_mock: Permit simulated readings when the script is absent.
            status_dispatcher: Function used to dispatch callbacks onto the
                UI thread. GLib.idle_add is used by default.
        """
        self._governor_controller = governor_controller
        self._ina219_script = Path(ina219_script or get_default_ina219_script())
        self._allow_mock = allow_mock
        self._status_dispatcher = status_dispatcher or GLib.idle_add
        self._state_lock = threading.Lock()
        self._running = False

    def is_available(self):
        """
        Return whether a live or simulated benchmark can be started.
        """
        return self._ina219_script.is_file() or self._allow_mock

    def get_unavailable_reason(self):
        """
        Explain why the runner cannot execute a benchmark.
        """
        if self.is_available():
            return ""

        return (
            "The INA219 sampling script was not found at "
            f"'{self._ina219_script}', and simulated readings are disabled."
        )

    def is_running(self):
        """
        Return whether a benchmark thread currently owns the runner.
        """
        with self._state_lock:
            return self._running

    def start(self, request, status_callback=None):
        """
        Start one benchmark and return its background thread.

        Raises:
            BenchmarkUnavailableError: If no execution mode is available.
            BenchmarkAlreadyRunningError: If another benchmark is active.
        """
        if not self.is_available():
            raise BenchmarkUnavailableError(self.get_unavailable_reason())

        callback = status_callback or self._print_status

        with self._state_lock:
            if self._running:
                raise BenchmarkAlreadyRunningError(
                    "A power benchmark is already running."
                )

            self._running = True

        thread = threading.Thread(
            target=self._run_and_clear,
            args=(request, callback),
            daemon=True,
            name="pda-power-benchmark",
        )

        try:
            thread.start()
        except RuntimeError as error:
            with self._state_lock:
                self._running = False
            raise PowerBenchmarkRunnerError(
                f"Could not start the benchmark thread: {error}"
            ) from error

        return thread

    def _run_and_clear(self, request, status_callback):
        """
        Run the worker and always release the active-run state.
        """
        try:
            self._run_benchmark(request, status_callback)
        except Exception as error:
            self._post_status(
                status_callback,
                f"Status: Error — unexpected benchmark failure.\n{error}",
            )
        finally:
            with self._state_lock:
                self._running = False

    def _run_benchmark(self, request, status_callback):
        """
        Run governor setup, measurement, restoration, and result reporting.
        """
        csv_path = Path(request.output_path).expanduser()
        use_mock = not self._ina219_script.is_file()
        original_governor = None
        governor_changed = False
        governor_summary = f"Governor: {request.governor}"
        restore_warning = ""

        try:
            csv_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            (
                original_governor,
                governor_changed,
                governor_summary,
            ) = self._prepare_governor(
                request,
                status_callback,
                use_mock,
            )

            statistics = self._run_measurement(
                request,
                csv_path,
                status_callback,
                use_mock,
            )
        except (
            OSError,
            subprocess.SubprocessError,
            PowerBenchmarkRunnerError,
        ) as error:
            error_message = self._format_execution_error(error)
        else:
            error_message = ""
        finally:
            if governor_changed and original_governor:
                restore_warning = self._restore_governor(
                    original_governor,
                )

        if error_message:
            self._post_status(
                status_callback,
                f"Status: Error — {error_message}{restore_warning}",
            )
            return

        self._post_status(
            status_callback,
            self._format_result(
                request,
                csv_path,
                statistics,
                use_mock,
                governor_summary,
                restore_warning,
            ),
        )

    def _prepare_governor(
        self,
        request,
        status_callback,
        use_mock,
    ):
        """
        Save and apply the benchmark governor.

        Returns:
            tuple: Original governor, whether it was changed, and text
                describing the governor used for the benchmark.

        Governor failures are tolerated only for simulated development runs.
        Live measurements fail rather than silently recording data under an
        unknown governor.
        """
        try:
            original_governor = self._governor_controller.get_current_governor()
        except GovernorControllerError as error:
            if use_mock:
                governor_summary = (
                    f"Requested governor: {request.governor}\n"
                    "Governor status: Not applied "
                    "(simulated data only)\n"
                    f"Governor warning: {error}"
                )

                self._post_status(
                    status_callback,
                    "Status: Governor control is unavailable. "
                    "Continuing with simulated data only.\n"
                    f"{error}",
                )

                return None, False, governor_summary

            raise PowerBenchmarkRunnerError(
                "The active governor could not be read before the live "
                f"benchmark: {error}"
            ) from error

        if original_governor == request.governor:
            return (
                original_governor,
                False,
                f"Governor: {request.governor}",
            )

        self._post_status(
            status_callback,
            f"Status: Setting governor to {request.governor}…",
        )

        try:
            self._governor_controller.set_governor(
                request.governor,
            )
        except GovernorControllerError as error:
            restore_status = self._restore_governor(
                original_governor,
            )

            if use_mock:
                governor_summary = (
                    f"Requested governor: {request.governor}\n"
                    "Governor status: Not applied "
                    "(simulated data only)\n"
                    f"Governor warning: {error}"
                    f"{restore_status}"
                )

                self._post_status(
                    status_callback,
                    "Status: The requested governor could not be applied. "
                    "Continuing with simulated data only.\n"
                    f"{error}"
                    f"{restore_status}",
                )

                return (
                    original_governor,
                    False,
                    governor_summary,
                )

            raise PowerBenchmarkRunnerError(
                f"Could not apply governor '{request.governor}' before "
                f"the live benchmark: {error}"
                f"{restore_status}"
            ) from error

        return (
            original_governor,
            True,
            f"Governor: {request.governor}",
        )

    def _run_measurement(
        self,
        request,
        csv_path,
        status_callback,
        use_mock,
    ):
        """
        Run the INA219 script or generate simulated development data.
        """
        if use_mock:
            self._post_status(
                status_callback,
                "Status: Generating simulated "
                f"{request.workload} dataset representing "
                f"{request.duration_seconds} seconds…",
            )

            time.sleep(min(request.duration_seconds, 3))

            mock_statistics = create_mock_result(request)
            write_mock_csv(
                csv_path,
                mock_statistics,
            )

            return parse_benchmark_csv(csv_path)

        self._post_status(
            status_callback,
            f"Status: Measuring the prepared {request.workload} "
            "condition for "
            f"{request.duration_seconds} seconds…",
        )

        completed_process = subprocess.run(
            [
                sys.executable,
                str(self._ina219_script),
                "--seconds",
                str(request.duration_seconds),
                "--out",
                str(csv_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        if completed_process.stdout.strip():
            print(completed_process.stdout.strip())

        return parse_benchmark_csv(csv_path)

    def _restore_governor(self, original_governor):
        """
        Restore the governor active before the benchmark.
        """
        try:
            restored_governor = self._governor_controller.set_governor(
                original_governor
            )
        except GovernorControllerError as error:
            return (
                "\n\nWarning: The previous governor could not be "
                f"restored: {error}"
            )

        return f"\nRestored governor: {restored_governor}"

    def _post_status(self, status_callback, text):
        """
        Schedule one status callback on the GTK main loop.
        """
        self._status_dispatcher(status_callback, text)

    @staticmethod
    def _print_status(text):
        """
        Print status when no GTK label callback was supplied.
        """
        print(f"[power benchmark] {text}")

    @staticmethod
    def _format_execution_error(error):
        """
        Convert worker exceptions into user-facing benchmark text.
        """
        if isinstance(error, subprocess.CalledProcessError):
            details = (error.stderr or "").strip()

            if details:
                return f"INA219 script failed.\n{details}"

            return f"INA219 script failed with exit code {error.returncode}."

        return str(error)

    @staticmethod
    def _format_result(
        request,
        csv_path,
        statistics,
        use_mock,
        governor_summary,
        restore_warning,
    ):
        """
        Format one completed benchmark result for the status label.
        """
        data_source = "Simulated development data" if use_mock else "INA219"

        clip_note = (
            "\nWarning: Reading clipped at the 3.2 A sensor limit."
            if statistics["clipped"]
            else ""
        )

        return (
            "Status: Complete.\n"
            f"Data source: {data_source}\n"
            f"{governor_summary}\n"
            f"Workload: {request.workload}\n"
            f"Average: {statistics['average_watts']:.2f} W\n"
            f"Minimum: {statistics['min_watts']:.2f} W\n"
            f"Maximum: {statistics['max_watts']:.2f} W\n"
            f"Voltage: {statistics['average_voltage']:.2f} V\n"
            f"Samples: {statistics['sample_count']}\n"
            f"Saved to: {csv_path}"
            f"{clip_note}"
            f"{restore_warning}"
        )
