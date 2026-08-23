# power_profile_controller.py
# Provides tuned-ppd power profile access for the PDA GTK demo.
# Owner: Jiesui
# Last updated: August 2026

"""
Power profile controller for the PDA GTK demo.

This module communicates with the tuned-ppd compatibility service over
the system D-Bus. It reads available profiles, reads the active profile,
applies a requested profile, and verifies the result.
"""

import gi

gi.require_version("Gio", "2.0")

from gi.repository import Gio, GLib


BUS_NAME = "org.freedesktop.UPower.PowerProfiles"
OBJECT_PATH = "/org/freedesktop/UPower/PowerProfiles"
INTERFACE_NAME = "org.freedesktop.UPower.PowerProfiles"
PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"


class PowerProfileControllerError(RuntimeError):
    """
    Base exception for recoverable power profile controller failures.
    """


class PowerProfileUnavailableError(PowerProfileControllerError):
    """
    Report that the system power profile service cannot be used.
    """


class PowerProfileApplyError(PowerProfileControllerError):
    """
    Report that a requested power profile could not be applied.
    """


class PowerProfileController:
    """
    Provide validated access to the system power profile service.
    """

    def __init__(self, proxy=None):
        """
        Initialize with an optional D-Bus proxy.

        The proxy is created lazily so the GTK application can still start
        on development systems where tuned-ppd is unavailable.
        """
        self._proxy = proxy

    def _get_proxy(self):
        """
        Return the tuned-ppd D-Bus proxy, creating it if necessary.

        Raises:
            PowerProfileUnavailableError: If the D-Bus service cannot
                be reached.
        """
        if self._proxy is not None:
            return self._proxy

        try:
            self._proxy = Gio.DBusProxy.new_for_bus_sync(
                Gio.BusType.SYSTEM,
                Gio.DBusProxyFlags.NONE,
                None,
                BUS_NAME,
                OBJECT_PATH,
                INTERFACE_NAME,
                None,
            )
        except GLib.Error as error:
            raise PowerProfileUnavailableError(
                f"Could not connect to the power profile service: {error}"
            ) from error

        return self._proxy

    def get_available_profiles(self):
        """
        Return the power profiles exposed by tuned-ppd.

        Returns:
            tuple[str, ...]: Available profile identifiers.

        Raises:
            PowerProfileUnavailableError: If profile data cannot be read.
        """
        proxy = self._get_proxy()

        try:
            profiles_variant = proxy.get_cached_property("Profiles")
        except GLib.Error as error:
            raise PowerProfileUnavailableError(
                f"Could not read available power profiles: {error}"
            ) from error

        if profiles_variant is None:
            raise PowerProfileUnavailableError(
                "The power profile service did not expose Profiles."
            )

        profiles = profiles_variant.unpack()

        available_profiles = tuple(
            profile["Profile"]
            for profile in profiles
            if "Profile" in profile
        )

        if not available_profiles:
            raise PowerProfileUnavailableError(
                "The power profile service did not report any profiles."
            )

        return available_profiles

    def get_active_profile(self):
        """
        Return the currently active power profile.

        Raises:
            PowerProfileUnavailableError: If the active profile cannot
                be read.
        """
        proxy = self._get_proxy()

        try:
            active_variant = proxy.get_cached_property("ActiveProfile")
        except GLib.Error as error:
            raise PowerProfileUnavailableError(
                f"Could not read the active power profile: {error}"
            ) from error

        if active_variant is None:
            raise PowerProfileUnavailableError(
                "The power profile service did not expose ActiveProfile."
            )

        active_profile = active_variant.unpack()

        if not active_profile:
            raise PowerProfileUnavailableError(
                "The power profile service reported an empty active profile."
            )

        return active_profile

    def set_profile(self, profile):
        """
        Apply one power profile and verify the result.

        Returns:
            str: The active profile after verification.

        Raises:
            PowerProfileUnavailableError: If profile information cannot
                be accessed.
            PowerProfileApplyError: If the profile cannot be applied or
                verified.
        """
        available_profiles = self.get_available_profiles()

        if profile not in available_profiles:
            raise PowerProfileUnavailableError(
                f"Power profile '{profile}' is not supported. "
                "Available profiles: "
                f"{', '.join(available_profiles)}"
            )

        proxy = self._get_proxy()
        connection = proxy.get_connection()

        parameters = GLib.Variant(
            "(ssv)",
            (
                INTERFACE_NAME,
                "ActiveProfile",
                GLib.Variant("s", profile),
            ),
        )

        try:
            connection.call_sync(
                BUS_NAME,
                OBJECT_PATH,
                PROPERTIES_INTERFACE,
                "Set",
                parameters,
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None,
            )
        except GLib.Error as error:
            raise PowerProfileApplyError(
                f"Could not apply power profile '{profile}': {error}"
            ) from error

        # Refresh the proxy properties before verifying the result.
        try:
            proxy = Gio.DBusProxy.new_for_bus_sync(
                Gio.BusType.SYSTEM,
                Gio.DBusProxyFlags.NONE,
                None,
                BUS_NAME,
                OBJECT_PATH,
                INTERFACE_NAME,
                None,
            )
        except GLib.Error as error:
            raise PowerProfileApplyError(
                f"Power profile '{profile}' was requested, but the "
                f"result could not be verified: {error}"
            ) from error

        self._proxy = proxy

        try:
            active_profile = self.get_active_profile()
        except PowerProfileUnavailableError as error:
            raise PowerProfileApplyError(
                f"Power profile '{profile}' was requested, but the "
                "active profile could not be verified."
            ) from error

        if active_profile != profile:
            raise PowerProfileApplyError(
                f"Requested power profile '{profile}', but the system "
                f"reports '{active_profile}'."
            )

        return active_profile