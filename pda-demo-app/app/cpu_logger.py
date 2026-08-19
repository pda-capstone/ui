# cpu_logger.py
# Collects CPU runtime metrics and records them to CSV.
# Owner: Nelson / Jiesui
# Last updated: August 2026

"""
Standalone CPU monitoring and CSV logging for the PDA GTK demo.

This module reads CPU runtime information without changing system
configuration. Logging runs on a background thread so GTK remains
responsive.
"""

import csv
import threading
import time
from pathlib import Path

import psutil


DEFAULT_SAMPLE_INTERVAL_SECONDS = 1.0

GOVERNOR_PATH = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
TEMPERATURE_PATH = Path("/sys/class/thermal/thermal_zone0/temp")


class CpuLoggerError(Exception):
    """Raised when CPU logging cannot be started."""


class CpuLogger:
    """Read CPU runtime metrics and optionally record them to CSV."""

    def __init__(self):
        self._thread = None
        self._stop_event = threading.Event()

    def is_running(self):
        """Return True while a logging session is active."""
        return self._thread is not None and self._thread.is_alive()

    def read_governor(self):
        """Return the active CPU governor when available."""
        try:
            return GOVERNOR_PATH.read_text(encoding="utf-8").strip()
        except OSError:
            return None

    def read_frequency_mhz(self):
        """Return the current CPU frequency in MHz when available."""
        try:
            frequency = psutil.cpu_freq()
        except OSError, NotImplementedError:
            return None

        if frequency is None:
            return None

        return frequency.current

    def read_usage_percent(self):
        """Return current total CPU utilization."""
        try:
            return psutil.cpu_percent(interval=None)
        except OSError, NotImplementedError:
            return None

    def read_temperature_c(self):
        """Return CPU temperature in Celsius when available."""
        try:
            raw_temperature = TEMPERATURE_PATH.read_text(
                encoding="utf-8"
            ).strip()
            return int(raw_temperature) / 1000
        except OSError, ValueError:
            return None

    def read_metrics(self):
        """Return one snapshot of the current CPU state."""
        return {
            "timestamp": time.time(),
            "governor": self.read_governor(),
            "frequency_mhz": self.read_frequency_mhz(),
            "usage_percent": self.read_usage_percent(),
            "temperature_c": self.read_temperature_c(),
        }

    def start(
        self,
        duration_seconds,
        output_path,
        sample_callback=None,
        finished_callback=None,
        error_callback=None,
    ):
        """Start a CPU logging session on a background thread."""
        if self.is_running():
            raise CpuLoggerError("CPU logging is already running.")

        if duration_seconds <= 0:
            raise CpuLoggerError("Duration must be greater than zero.")

        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._run,
            args=(
                duration_seconds,
                Path(output_path),
                sample_callback,
                finished_callback,
                error_callback,
            ),
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        """Request that the active logging session stop."""
        self._stop_event.set()

    def _run(
        self,
        duration_seconds,
        output_path,
        sample_callback,
        finished_callback,
        error_callback,
    ):
        """Write CPU samples until duration expires or stop is requested."""
        try:
            output_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with output_path.open(
                "w",
                newline="",
                encoding="utf-8",
            ) as output_file:
                writer = csv.writer(output_file)

                writer.writerow(
                    [
                        "timestamp",
                        "governor",
                        "cpu_frequency_mhz",
                        "cpu_usage_percent",
                        "temperature_c",
                    ]
                )

                # Prime psutil so later non-blocking CPU usage readings
                # describe the interval between samples.
                psutil.cpu_percent(interval=None)

                start_time = time.monotonic()

                while (
                    time.monotonic() - start_time < duration_seconds
                    and not self._stop_event.is_set()
                ):
                    metrics = self.read_metrics()

                    writer.writerow(
                        [
                            metrics["timestamp"],
                            metrics["governor"] or "",
                            self._format_csv_value(metrics["frequency_mhz"]),
                            self._format_csv_value(metrics["usage_percent"]),
                            self._format_csv_value(metrics["temperature_c"]),
                        ]
                    )
                    output_file.flush()

                    if sample_callback is not None:
                        sample_callback(metrics)

                    self._stop_event.wait(DEFAULT_SAMPLE_INTERVAL_SECONDS)

            if finished_callback is not None:
                finished_callback(self._stop_event.is_set())

        except OSError as error:
            if error_callback is not None:
                error_callback(str(error))

    def _format_csv_value(self, value):
        """Format optional numeric values for CSV output."""
        if value is None:
            return ""

        return f"{value:.2f}"
