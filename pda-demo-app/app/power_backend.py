# power_backend.py
# Defines the optional power integration interface for the PDA GTK demo.
# Owner: Jiesui
# Last updated: July 2026

"""
Optional power backend interface for the PDA GTK demo.

The UI remains usable when no power implementation is installed.
A future backend can connect these requests to the power scripts or
to a system service without changing the UI panels.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BenchmarkRequest:
    """
    Store one validated benchmark request.
    """

    governor: str
    workload: str
    duration_seconds: int
    output_path: Path


class PowerBackend:
    """
    Default unavailable power backend.
    """

    def is_available(self):
        """
        Return whether a real power implementation is connected.
        """
        return False

    def get_unavailable_reason(self):
        """
        Explain why power actions cannot currently run.
        """
        return (
            "Power benchmark integration is not available in this build."
        )

    def apply_power_mode(self, _power_mode):
        """
        Report that active power-mode control is unavailable.
        """
        raise RuntimeError(self.get_unavailable_reason())

    def start_benchmark(self, _request):
        """
        Start a benchmark without blocking the GTK main thread.

        Implementations must return immediately after scheduling or
        launching the benchmark.
        """
        raise RuntimeError(self.get_unavailable_reason())