# power_modes.py
# Defines shared power mode metadata for the PDA GTK demo.
# Owner: Jiesui
# Last updated: August 2026

"""
Shared application-level power mode definitions.

Settings use the system power-profile mapping, while the existing benchmark
path continues to use CPUfreq governor mappings during the transition to
tuned-ppd.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PowerModeDefinition:
    """
    Describe one application-level power mode.
    """

    identifier: str
    label: str
    profile: str
    governor: str


DEFAULT_POWER_MODE = "default"

POWER_MODE_DEFINITIONS = (
    PowerModeDefinition(
        identifier="default",
        label="Default",
        profile="balanced",
        governor="schedutil",
    ),
    PowerModeDefinition(
        identifier="low_power",
        label="Low Power",
        profile="power-saver",
        governor="powersave",
    ),
    PowerModeDefinition(
        identifier="performance",
        label="Performance",
        profile="performance",
        governor="performance",
    ),
)

POWER_MODE_DEFINITIONS_BY_ID = {
    definition.identifier: definition for definition in POWER_MODE_DEFINITIONS
}

if len(POWER_MODE_DEFINITIONS_BY_ID) != len(POWER_MODE_DEFINITIONS):
    raise RuntimeError("Power mode identifiers must be unique.")

if DEFAULT_POWER_MODE not in POWER_MODE_DEFINITIONS_BY_ID:
    raise RuntimeError("The default power mode must be defined.")

VALID_POWER_MODES = tuple(POWER_MODE_DEFINITIONS_BY_ID)


def get_power_mode_definition(power_mode):
    """
    Return the shared definition for one power mode.

    Raises:
        ValueError: If the supplied power mode is unsupported.
    """
    try:
        return POWER_MODE_DEFINITIONS_BY_ID[power_mode]
    except KeyError as error:
        raise ValueError(f"Unsupported power mode: {power_mode}") from error