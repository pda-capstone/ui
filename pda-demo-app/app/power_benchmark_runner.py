# power_benchmark_runner.py
# Concrete PowerBackend that connects the UI to the INA219 sensor script.
# Falls back to simulated readings on non-Pi hardware (Mac development).
# Owner: Camellia Tran
# Last updated: July 2026


import csv
import subprocess
import threading
import time
from pathlib import Path

from gi.repository import GLib

from power_backend import BenchmarkRequest, PowerBackend


# Path to the sponsor-provided INA219 sensor script.
# Adjust if your checkout layout differs.
INA219_SCRIPT = (
    Path(__file__).parent.parent.parent
    / "power"
    / "hardware"
    / "ina219"
    / "ina219_sample.py"
)

CPU_FREQ_PATH = Path("/sys/devices/system/cpu")


# ── Governor helpers ──────────────────────────────────────────────────────────


def _read_governor() -> str:
    """Return the current governor for cpu0, or empty string if unavailable."""
    gov_path = CPU_FREQ_PATH / "cpu0" / "cpufreq" / "scaling_governor"
    try:
        return gov_path.read_text().strip()
    except OSError:
        return ""


def _write_governor(governor: str) -> None:
    """
    Write governor to every CPU core.
    Tries a direct write first; falls back to sudo on permission error.
    Does not raise on failure — logs a warning and continues.
    """
    for cpu_dir in sorted(CPU_FREQ_PATH.glob("cpu[0-9]*")):
        gov_path = cpu_dir / "cpufreq" / "scaling_governor"
        if not gov_path.exists():
            continue
        try:
            gov_path.write_text(governor)
        except PermissionError:
            try:
                subprocess.run(
                    ["sudo", "tee", str(gov_path)],
                    input=governor.encode(),
                    capture_output=True,
                    check=True,
                )
            except subprocess.CalledProcessError as exc:
                print(f"[runner] Warning: could not set {gov_path}: {exc}")
        except OSError as exc:
            print(f"[runner] Warning: {gov_path}: {exc}")


# ── CSV reader ────────────────────────────────────────────────────────────────


def _parse_csv(csv_path: Path) -> dict:
    """
    Parse the CSV the INA219 script produces and return summary stats.
    Raises RuntimeError if the file is missing or contains no valid rows.
    """
    watts_list = []
    voltage_list = []
    clipped = False

    try:
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    power_mw = float(row.get("power_mW", 0))
                    voltage_v = float(row.get("voltage_V", 0))
                    current_ma = float(row.get("current_mA", 0))
                    watts_list.append(power_mw / 1000)
                    voltage_list.append(voltage_v)
                    if current_ma >= 3200:
                        clipped = True
                except ValueError, KeyError:
                    continue
    except OSError as exc:
        raise RuntimeError(f"Could not read {csv_path}: {exc}") from exc

    if not watts_list:
        raise RuntimeError(
            f"No valid readings in {csv_path}. "
            "Check that the INA219 sensor is connected and wired correctly."
        )

    return {
        "average_watts": sum(watts_list) / len(watts_list),
        "min_watts": min(watts_list),
        "max_watts": max(watts_list),
        "average_voltage": sum(voltage_list) / len(voltage_list),
        "sample_count": len(watts_list),
        "clipped": clipped,
    }


# ── Mock results ──────────────────────────────────────────────────────────────


def _mock_result(request: BenchmarkRequest) -> dict:
    """
    Return plausible simulated readings for development on non-Pi hardware.
    """
    import random

    base = {"schedutil": 2.3, "ondemand": 2.5, "powersave": 1.8}.get(
        request.governor, 2.3
    )
    factor = {"idle": 0.80, "display": 1.10, "peripheral": 1.35}.get(
        request.workload, 1.0
    )
    avg = base * factor

    return {
        "average_watts": round(avg + random.uniform(-0.05, 0.05), 2),
        "min_watts": round(avg * 0.88, 2),
        "max_watts": round(avg * 1.12, 2),
        "average_voltage": 4.97,
        "sample_count": request.duration_seconds * 4,
        "clipped": False,
    }


def _write_mock_csv(csv_path: Path, stats: dict, duration: int) -> None:
    """Write simulated readings to a CSV so the output file actually exists."""
    import random

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["voltage_V", "current_mA", "power_mW"])
        for _ in range(stats["sample_count"]):
            v = stats["average_voltage"]
            w = stats["average_watts"] + random.uniform(-0.05, 0.05)
            ma = (w / v) * 1000
            writer.writerow([f"{v:.4f}", f"{ma:.2f}", f"{w * 1000:.2f}"])


# ── Background worker ─────────────────────────────────────────────────────────


def _benchmark_thread(request: BenchmarkRequest, status_cb) -> None:
    """
    Run one benchmark on a background thread.

    Steps:
      1. Save and switch governor.
      2. Run INA219 script (or mock).
      3. Restore governor.
      4. Parse CSV and call status_cb with results.

    status_cb(text) is called via GLib.idle_add — safe to set a GTK label.
    """

    def update(text: str) -> None:
        GLib.idle_add(status_cb, text)

    original_governor = _read_governor()
    csv_path = Path(request.output_path)

    try:
        # 1. Switch governor ────────────────────────────────────────────────
        if original_governor:
            update(f"Status: Setting governor to {request.governor}…")
            _write_governor(request.governor)

        # 2. Run measurement ────────────────────────────────────────────────
        update(
            f"Status: Running {request.workload} workload "
            f"for {request.duration_seconds} s…"
        )

        if INA219_SCRIPT.exists():
            subprocess.run(
                [
                    "python3",
                    str(INA219_SCRIPT),
                    "--seconds",
                    str(request.duration_seconds),
                    "--out",
                    str(csv_path),
                ],
                check=True,
            )
            stats = _parse_csv(csv_path)
        else:
            # No sensor hardware — simulate and still produce a real CSV
            print(f"[runner] INA219 script not found — using mock data.")
            time.sleep(min(request.duration_seconds, 3))
            stats = _mock_result(request)
            _write_mock_csv(csv_path, stats, request.duration_seconds)

        # 3. Report results ─────────────────────────────────────────────────
        clip_note = (
            "\n⚠ Reading clipped at 3.2 A sensor limit."
            if stats["clipped"]
            else ""
        )
        update(
            f"Status: Complete.\n"
            f"Governor:  {request.governor}\n"
            f"Workload:  {request.workload}\n"
            f"Average:   {stats['average_watts']:.2f} W\n"
            f"Min:       {stats['min_watts']:.2f} W\n"
            f"Max:       {stats['max_watts']:.2f} W\n"
            f"Voltage:   {stats['average_voltage']:.2f} V\n"
            f"Samples:   {stats['sample_count']}\n"
            f"Saved to:  {csv_path}"
            f"{clip_note}"
        )

    except subprocess.CalledProcessError as exc:
        update(f"Status: Error — INA219 script failed.\n{exc}")

    except RuntimeError as exc:
        update(f"Status: Error — {exc}")

    finally:
        # 4. Restore governor ───────────────────────────────────────────────
        if original_governor and original_governor != request.governor:
            _write_governor(original_governor)


# ── Public backend ────────────────────────────────────────────────────────────


class LivePowerBackend(PowerBackend):
    """
    Real power backend. Subclasses PowerBackend so it plugs straight
    into demo.py without changing any other file.
    """

    def __init__(self) -> None:
        self._status_cb = lambda text: print(f"[runner] {text}")
        self._running = False

    def is_available(self) -> bool:
        return True

    def get_unavailable_reason(self) -> str:
        return ""

    def apply_power_mode(self, power_mode: str) -> None:
        """Switch the CPU governor."""
        _write_governor(power_mode)

    def start_benchmark(self, request: BenchmarkRequest) -> None:
        """
        Start the benchmark on a background thread and return immediately.
        The panel label updates automatically when the thread finishes.
        """
        if self._running:
            self._status_cb(
                "Status: A benchmark is already running. Please wait."
            )
            return
        self._running = True

        thread = threading.Thread(
            target=_benchmark_thread,
            args=(request, self._status_cb),
            daemon=True,
        )
        thread.start()

    def connect_status_label(self, label) -> None:
        """
        Wire the runner's status updates to a GTK label.
        Call this after the window is built:

            backend.connect_status_label(your_status_label)

        This is optional — without it, updates print to the terminal.
        """
        self._status_cb = label.set_text

    def _run_and_clear(self, request):  # ADD THIS METHOD
        try:
            _benchmark_thread(request, self._status_cb)
        finally:
            self._running = False
