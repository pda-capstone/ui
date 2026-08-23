# governor_controller.py
# Provides validated CPUfreq governor access for the PDA GTK demo.
# Owner: Jiesui
# Last updated: August 2026

"""
CPUfreq governor controller for the PDA GTK demo.

This module owns loading the optional power-team governor implementation,
reading available and active governors, applying a governor, and verifying
that the requested value became active.
"""

import importlib


class GovernorControllerError(RuntimeError):
    """
    Base exception for recoverable governor controller failures.
    """


class GovernorUnavailableError(GovernorControllerError):
    """
    Report that CPUfreq governor information cannot be used.
    """


class GovernorApplyError(GovernorControllerError):
    """
    Report that a requested governor was not applied successfully.
    """


class GovernorController:
    """
    Provide validated access to the optional CPUfreq governor implementation.
    """

    def __init__(self, controller=None, module_name="app.governors"):
        """
        Initialize with an optional low-level governor implementation.

        When no implementation is supplied, the configured module is loaded
        lazily when governor access is first requested. This keeps the GTK
        application usable on systems where CPUfreq support is unavailable.
        """
        self._controller = controller
        self._module_name = module_name
        self._import_error = None

    def _get_controller(self):
        """
        Return the low-level governor implementation, loading it if needed.

        Raises:
            GovernorUnavailableError: If the optional implementation cannot
                be imported.
        """
        if self._controller is not None:
            return self._controller

        if self._import_error is not None:
            raise GovernorUnavailableError(
                "The CPU governor implementation is not available: "
                f"{self._import_error}"
            ) from self._import_error

        try:
            self._controller = importlib.import_module(self._module_name)
        except Exception as error:
            self._import_error = error
            raise GovernorUnavailableError(
                f"The CPU governor implementation could not be loaded: {error}"
            ) from error

        return self._controller

    def get_available_governors(self):
        """
        Return the CPUfreq governors exposed by the operating system.

        Raises:
            GovernorUnavailableError: If governor data cannot be read.
        """
        controller = self._get_controller()

        try:
            available_governors = tuple(controller.available_governors())
        except (AttributeError, OSError, RuntimeError) as error:
            raise GovernorUnavailableError(
                f"Could not read the available CPU governors: {error}"
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
        controller = self._get_controller()

        try:
            current_governor = controller.get_current_governor()
        except (AttributeError, OSError, RuntimeError) as error:
            raise GovernorUnavailableError(
                f"Could not read the active CPU governor: {error}"
            ) from error

        if not current_governor:
            raise GovernorUnavailableError(
                "The operating system reported an empty CPU governor."
            )

        return current_governor

    def set_governor(self, governor):
        """
        Apply one governor and verify the active value.

        Returns:
            str: The active governor after verification.

        Raises:
            GovernorUnavailableError: If CPUfreq data cannot be accessed.
            GovernorApplyError: If the governor cannot be applied or verified.
        """
        available_governors = self.get_available_governors()

        if governor not in available_governors:
            raise GovernorUnavailableError(
                f"Governor '{governor}' is not supported. "
                "Available governors: "
                f"{', '.join(available_governors)}"
            )

        controller = self._get_controller()

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
