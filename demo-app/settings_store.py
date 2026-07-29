# settings_store.py
# Reads and writes persistent settings for the PDA GTK demo.
# Owner: Jiesui
# Last updated: July 2026

"""
Persistent settings storage for the PDA GTK demo.

Settings are stored as JSON in the user's XDG configuration directory.
The power controller can use load_settings() to read the selected
power mode when it starts.
"""

import json
import os
from pathlib import Path


APPLICATION_CONFIG_DIRECTORY = "pda-demo"
SETTINGS_FILENAME = "settings.json"
SETTINGS_SCHEMA_VERSION = 1

DEFAULT_POWER_MODE = "default"

VALID_POWER_MODES = (
    "default",
    "low_power",
    "performance",
)


def get_config_directory():
    """
    Return the PDA demo configuration directory.
    """
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")

    if xdg_config_home:
        return Path(xdg_config_home) / APPLICATION_CONFIG_DIRECTORY

    return Path.home() / ".config" / APPLICATION_CONFIG_DIRECTORY


def get_settings_path():
    """
    Return the path to the persistent settings JSON file.
    """
    return get_config_directory() / SETTINGS_FILENAME


def create_default_settings():
    """
    Return a new dictionary containing the default settings.
    """
    return {
        "version": SETTINGS_SCHEMA_VERSION,
        "power_mode": DEFAULT_POWER_MODE,
    }


def validate_power_mode(power_mode):
    """
    Validate a power mode value.

    Raises:
        ValueError: If the supplied power mode is unsupported.
    """
    if power_mode not in VALID_POWER_MODES:
        raise ValueError(
            f"Unsupported power mode: {power_mode}"
        )


def validate_settings(settings):
    """
    Validate settings loaded from the JSON configuration file.

    Raises:
        ValueError: If the configuration structure is invalid.
    """
    if not isinstance(settings, dict):
        raise ValueError(
            "The settings file must contain a JSON object."
        )

    power_mode = settings.get("power_mode")

    if power_mode is None:
        raise ValueError(
            "The settings file does not contain power_mode."
        )

    validate_power_mode(power_mode)


def load_settings():
    """
    Load and validate the persistent settings.

    Returns:
        dict: The saved settings, or defaults if no file exists.

    Raises:
        OSError: If the settings file cannot be read.
        json.JSONDecodeError: If the JSON is malformed.
        ValueError: If the settings contain unsupported values.
    """
    settings_path = get_settings_path()

    if not settings_path.exists():
        return create_default_settings()

    with settings_path.open(
        "r",
        encoding="utf-8",
    ) as settings_file:
        settings = json.load(settings_file)

    validate_settings(settings)

    return settings


def save_settings(power_mode):
    """
    Save the selected power mode atomically.

    Args:
        power_mode: Stable application-level power mode name.

    Returns:
        Path: The location of the saved settings file.

    Raises:
        OSError: If the configuration cannot be written.
        ValueError: If the selected power mode is invalid.
    """
    validate_power_mode(power_mode)

    config_directory = get_config_directory()
    settings_path = get_settings_path()
    temporary_path = settings_path.with_suffix(".tmp")

    config_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    settings = {
        "version": SETTINGS_SCHEMA_VERSION,
        "power_mode": power_mode,
    }

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as settings_file:
        json.dump(
            settings,
            settings_file,
            indent=4,
        )
        settings_file.write("\n")

    temporary_path.replace(settings_path)

    return settings_path