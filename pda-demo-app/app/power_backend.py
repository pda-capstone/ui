# power_backend.py
# Defines the optional power integration interface for the PDA GTK demo.
# Owner: Jiesui
# Last updated: August 2026

"""
Optional power backend interface for the PDA GTK demo.

Power-mode requests are translated into CPUfreq governors and delegated
to GovernorController. Benchmark execution remains unavailable until the
benchmark runner interface is connected.
"""

from dataclasses import dataclass
from pathlib import Path

from app.governor_controller import (
    GovernorApplyError as ControllerGovernorApplyError,
)
from app.governor_controller import GovernorController
from app.governor_controller import (
    GovernorUnavailableError as ControllerGovernorUnavailableError,
)
from app.power_modes import get_power_mode_definition


class PowerBackendError(RuntimeError):
    """
    Base exception for recoverable power backend failures.
    """


class UnsupportedPowerModeError(PowerBackendError):
    """
    Report that an application power mode is unknown.
    """


class GovernorUnavailableError(PowerBackendError):
    """
    Report that CPUfreq governor information cannot be used.
    """


class GovernorApplyError(PowerBackendError):
    """
    Report that a requested governor was not applied successfully.
    """


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
    Coordinate power-mode requests and future benchmark execution.
    """

    def __init__(self, governor_controller=None):
        """
        Initialize with an optional governor controller.

        A GovernorController instance can be supplied directly. For backward
        compatibility, a low-level governor implementation can also be
        supplied and will be wrapped by GovernorController.
        """
        if governor_controller is None:
            self._governor_controller = GovernorController()
        elif isinstance(governor_controller, GovernorController):
            self._governor_controller = governor_controller
        else:
            self._governor_controller = GovernorController(
                controller=governor_controller,
            )

    def is_available(self):
        """
        Return whether benchmark execution is connected.

        Power-mode control is available independently through
        apply_power_mode().
        """
        return False

    def get_unavailable_reason(self):
        """
        Explain why benchmark actions cannot currently run.
        """
        return "Power benchmark integration is not available in this build."

    def get_governor_for_power_mode(self, power_mode):
        """
        Return the CPUfreq governor mapped to an application power mode.

        Raises:
            UnsupportedPowerModeError: If the power mode is unknown.
        """
        try:
            definition = get_power_mode_definition(power_mode)
        except ValueError as error:
            raise UnsupportedPowerModeError(str(error)) from error

        return definition.governor

    def get_available_governors(self):
        """
        Return the CPUfreq governors exposed by the operating system.

        Raises:
            GovernorUnavailableError: If governor data cannot be read.
        """
        try:
            return self._governor_controller.get_available_governors()
        except ControllerGovernorUnavailableError as error:
            raise GovernorUnavailableError(str(error)) from error

    def get_current_governor(self):
        """
        Return the governor currently reported for CPU 0.

        Raises:
            GovernorUnavailableError: If the governor cannot be read.
        """
        try:
            return self._governor_controller.get_current_governor()
        except ControllerGovernorUnavailableError as error:
            raise GovernorUnavailableError(str(error)) from error

    def _set_and_verify_governor(self, governor):
        """
        Delegate governor application and verification to GovernorController.

        Returns:
            str: The active governor after verification.

        Raises:
            GovernorUnavailableError: If CPUfreq data cannot be accessed.
            GovernorApplyError: If the governor cannot be applied or verified.
        """
        try:
            return self._governor_controller.set_governor(governor)
        except ControllerGovernorUnavailableError as error:
            raise GovernorUnavailableError(str(error)) from error
        except ControllerGovernorApplyError as error:
            raise GovernorApplyError(str(error)) from error

    def apply_power_mode(self, power_mode):
        """
        Apply and verify the governor mapped to a power mode.

        Returns:
            str: The active governor after the operation succeeds.

        Raises:
            UnsupportedPowerModeError: If the power mode is unknown.
            GovernorUnavailableError: If CPUfreq data cannot be accessed.
            GovernorApplyError: If the governor cannot be applied or verified.
        """
        requested_governor = self.get_governor_for_power_mode(power_mode)

        return self._set_and_verify_governor(requested_governor)

    def restore_governor(self, governor):
        """
        Restore and verify a previously active governor.

        Returns:
            str: The restored active governor.
        """
        return self._set_and_verify_governor(governor)

    def start_benchmark(self, _request):
        """
        Report that benchmark execution is not connected yet.
        """
        raise PowerBackendError(self.get_unavailable_reason())