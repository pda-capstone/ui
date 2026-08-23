# power_backend.py
# Provides the UI-facing power service facade for the PDA GTK demo.
# Owner: Jiesui
# Last updated: August 2026

"""
Power service facade for the PDA GTK demo.

The GTK layer uses one PowerBackend instance. Internally, the backend delegates
power-mode settings to PowerProfileController and benchmark governor work to
GovernorController and PowerBenchmarkRunner.
"""

from dataclasses import dataclass
from pathlib import Path

from app.governor_controller import GovernorController
from app.power_benchmark_runner import (
    PowerBenchmarkRunner,
    PowerBenchmarkRunnerError,
)
from app.power_modes import get_power_mode_definition
from app.power_profile_controller import (
    PowerProfileApplyError as ControllerPowerProfileApplyError,
)
from app.power_profile_controller import PowerProfileController
from app.power_profile_controller import (
    PowerProfileUnavailableError as ControllerPowerProfileUnavailableError,
)


class PowerBackendError(RuntimeError):
    """
    Base exception for recoverable power backend failures.
    """


class UnsupportedPowerModeError(PowerBackendError):
    """
    Report that an application power mode is unknown.
    """


class PowerProfileUnavailableError(PowerBackendError):
    """
    Report that system power profile information cannot be used.
    """


class PowerProfileApplyError(PowerBackendError):
    """
    Report that a requested system power profile could not be applied.
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
    Provide one UI-facing service for power settings and benchmarks.
    """

    def __init__(
        self,
        power_profile_controller=None,
        governor_controller=None,
        benchmark_runner=None,
    ):
        """
        Initialize the power-profile controller and benchmark components.
        """
        if power_profile_controller is None:
            self._power_profile_controller = PowerProfileController()
        else:
            self._power_profile_controller = power_profile_controller

        if governor_controller is None:
            self._governor_controller = GovernorController()
        elif isinstance(governor_controller, GovernorController):
            self._governor_controller = governor_controller
        else:
            self._governor_controller = GovernorController(
                controller=governor_controller,
            )

        if benchmark_runner is None:
            self._benchmark_runner = PowerBenchmarkRunner(
                self._governor_controller,
            )
        else:
            self._benchmark_runner = benchmark_runner

    def is_available(self):
        """
        Return whether live or simulated benchmark execution is available.
        """
        return self._benchmark_runner.is_available()

    def get_unavailable_reason(self):
        """
        Explain why benchmark execution is unavailable.
        """
        return self._benchmark_runner.get_unavailable_reason()

    def is_benchmark_running(self):
        """
        Return whether a benchmark is currently active.
        """
        return self._benchmark_runner.is_running()

    def get_profile_for_power_mode(self, power_mode):
        """
        Return the system power profile mapped to an application power mode.

        Raises:
            UnsupportedPowerModeError: If the power mode is unknown.
        """
        try:
            definition = get_power_mode_definition(power_mode)
        except ValueError as error:
            raise UnsupportedPowerModeError(str(error)) from error

        return definition.profile

    def get_available_profiles(self):
        """
        Return the power profiles exposed by the operating system.

        Raises:
            PowerProfileUnavailableError: If profile data cannot be read.
        """
        try:
            return self._power_profile_controller.get_available_profiles()
        except ControllerPowerProfileUnavailableError as error:
            raise PowerProfileUnavailableError(str(error)) from error

    def get_active_profile(self):
        """
        Return the currently active system power profile.

        Raises:
            PowerProfileUnavailableError: If the profile cannot be read.
        """
        try:
            return self._power_profile_controller.get_active_profile()
        except ControllerPowerProfileUnavailableError as error:
            raise PowerProfileUnavailableError(str(error)) from error

    def _set_and_verify_profile(self, profile):
        """
        Delegate profile application and verification to the controller.

        Returns:
            str: The active profile after verification.

        Raises:
            PowerProfileUnavailableError: If profile data cannot be accessed.
            PowerProfileApplyError: If the profile cannot be applied.
        """
        try:
            return self._power_profile_controller.set_profile(profile)
        except ControllerPowerProfileUnavailableError as error:
            raise PowerProfileUnavailableError(str(error)) from error
        except ControllerPowerProfileApplyError as error:
            raise PowerProfileApplyError(str(error)) from error

    def apply_power_mode(self, power_mode):
        """
        Apply and verify the system profile mapped to a power mode.

        Returns:
            str: The active profile after the operation succeeds.

        Raises:
            UnsupportedPowerModeError: If the power mode is unknown.
            PowerProfileUnavailableError: If profile data cannot be accessed.
            PowerProfileApplyError: If the profile cannot be applied.
        """
        if self.is_benchmark_running():
            raise PowerBackendError(
                "A power mode cannot be changed while a benchmark is running."
            )

        requested_profile = self.get_profile_for_power_mode(power_mode)

        return self._set_and_verify_profile(requested_profile)

    def restore_profile(self, profile):
        """
        Restore and verify a previously active power profile.

        Returns:
            str: The restored active profile.
        """
        if self.is_benchmark_running():
            raise PowerBackendError(
                "The power profile cannot be restored while a benchmark "
                "is running."
            )

        return self._set_and_verify_profile(profile)

    def start_benchmark(
        self,
        request,
        status_callback=None,
    ):
        """
        Submit one benchmark request to the internal runner.

        Returns:
            threading.Thread: The started benchmark worker.

        Raises:
            PowerBackendError: If the benchmark cannot be started.
        """
        try:
            return self._benchmark_runner.start(
                request,
                status_callback,
            )
        except PowerBenchmarkRunnerError as error:
            raise PowerBackendError(str(error)) from error