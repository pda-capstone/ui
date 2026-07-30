# power_backend.py
# Defines the optional power integration interface for the PDA GTK demo.
# Owner: Jiesui
# Last updated: July 2026

"""
Optional power backend interface for the PDA GTK demo.

Power-mode requests are translated into CPUfreq governors and delegated
through the power team's governor controller. Benchmark execution remains
unavailable until the benchmark runner interface is connected.
"""

import importlib
from dataclasses import dataclass
from pathlib import Path

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
        Initialize the backend with an optional governor controller.

        The power team's governors module is loaded only when governor
        control is first requested. This keeps the UI usable when the
        optional power implementation is not installed.
        """
        self._governor_controller = governor_controller
        self._governor_import_error = None

    def _get_governor_controller(self):
        """
        Return the configured governor controller, loading it if needed.

        Raises:
            GovernorUnavailableError: If the optional controller cannot
                be imported.
        """
        if self._governor_controller is not None:
            return self._governor_controller

        if self._governor_import_error is not None:
            raise GovernorUnavailableError(
                "The CPU governor controller is not available: "
                f"{self._governor_import_error}"
            ) from self._governor_import_error

        try:
            self._governor_controller = importlib.import_module(
                "governors"
            )
        except Exception as error:
            self._governor_import_error = error
            raise GovernorUnavailableError(
                "The CPU governor controller could not be loaded: "
                f"{error}"
            ) from error

        return self._governor_controller

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
        return (
            "Power benchmark integration is not available in this build."
        )

    def get_governor_for_power_mode(self, power_mode):
        """
        Return the CPUfreq governor mapped to an application power mode.

        Raises:
            UnsupportedPowerModeError: If the power mode is unknown.
        """
        try:
            definition = get_power_mode_definition(power_mode)
        except ValueError as error:
            raise UnsupportedPowerModeError(
                str(error)
            ) from error

        return definition.governor

    def get_available_governors(self):
        """
        Return the CPUfreq governors exposed by the operating system.

        Raises:
            GovernorUnavailableError: If governor data cannot be read.
        """
        controller = self._get_governor_controller()

        try:
            available_governors = tuple(
                controller.available_governors()
            )
        except (AttributeError, OSError, RuntimeError) as error:
            raise GovernorUnavailableError(
                "Could not read the available CPU governors: "
                f"{error}"
            ) from error

        if not available_governors:
            raise GovernorUnavailableError(
                "The operating system did not report any CPU governors."
            )

        return available_governors

    def get_current_governor(self):
        """
        Return the governor currently reported for CPU 0.

        Raises:
            GovernorUnavailableError: If the governor cannot be read.
        """
        controller = self._get_governor_controller()

        try:
            current_governor = controller.get_current_governor()
        except (AttributeError, OSError, RuntimeError) as error:
            raise GovernorUnavailableError(
                "Could not read the active CPU governor: "
                f"{error}"
            ) from error

        if not current_governor:
            raise GovernorUnavailableError(
                "The operating system reported an empty CPU governor."
            )

        return current_governor

    def _set_and_verify_governor(self, governor):
        """
        Set one governor and verify the active value.

        Returns:
            str: The active governor after verification.

        Raises:
            GovernorUnavailableError: If CPUfreq data cannot be accessed.
            GovernorApplyError: If the governor cannot be applied or
                verified.
        """
        available_governors = self.get_available_governors()

        if governor not in available_governors:
            raise GovernorUnavailableError(
                f"Governor '{governor}' is not supported. "
                "Available governors: "
                f"{', '.join(available_governors)}"
            )

        controller = self._get_governor_controller()

        try:
            controller.set_governor(governor)
        except (AttributeError, OSError, RuntimeError) as error:
            raise GovernorApplyError(
                f"Could not apply governor '{governor}': {error}"
            ) from error

        try:
            active_governor = self.get_current_governor()
        except GovernorUnavailableError as error:
            raise GovernorApplyError(
                f"Governor '{governor}' was requested, but the active "
                "governor could not be verified."
            ) from error

        if active_governor != governor:
            raise GovernorApplyError(
                f"Requested governor '{governor}', but the operating "
                f"system reports '{active_governor}'."
            )

        return active_governor

    def apply_power_mode(self, power_mode):
        """
        Apply and verify the governor mapped to a power mode.

        Returns:
            str: The active governor after the operation succeeds.

        Raises:
            UnsupportedPowerModeError: If the power mode is unknown.
            GovernorUnavailableError: If CPUfreq data cannot be accessed.
            GovernorApplyError: If the governor cannot be applied or
                verified.
        """
        requested_governor = self.get_governor_for_power_mode(
            power_mode
        )

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
