# settings_overlay.py
# Builds the power mode settings overlay for the PDA GTK demo.
# Owner: Jiesui
# Last updated: August 2026

"""
Power mode settings overlay for the PDA GTK demo.

The overlay saves the selected power mode to the PDA settings JSON
file and then tries to apply the corresponding system power profile.

Power-mode requests are sent through PowerBackend so the GTK layer does
not communicate with tuned-ppd directly.
"""

import json

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from app.power_backend import PowerBackendError
from app.power_modes import (
    DEFAULT_POWER_MODE,
    POWER_MODE_DEFINITIONS,
    get_power_mode_definition,
)
from app.settings_store import (
    load_settings,
    save_settings,
)


def create_left_aligned_label(text):
    """
    Create a reusable left-aligned label.
    """
    label = Gtk.Label(label=text)
    label.set_xalign(0)
    label.set_wrap(True)

    return label


def set_selected_power_mode(mode_buttons, power_mode):
    """
    Select the radio button matching the supplied power mode.
    """
    selected_button = mode_buttons.get(power_mode)

    if selected_button is None:
        selected_button = mode_buttons[DEFAULT_POWER_MODE]

    selected_button.set_active(True)


def get_selected_power_mode(mode_buttons):
    """
    Return the currently selected power mode identifier.
    """
    for power_mode, mode_button in mode_buttons.items():
        if mode_button.get_active():
            return power_mode

    return DEFAULT_POWER_MODE


def get_power_mode_display_text(power_mode):
    """
    Return the shared display label and profile for one power mode.
    """
    definition = get_power_mode_definition(power_mode)

    return f"{definition.label} ({definition.profile})"


def update_loaded_mode_status(
    status_label,
    power_backend,
    power_mode,
):
    """
    Display the configured mode and currently active power profile.
    """
    display_text = get_power_mode_display_text(power_mode)

    try:
        active_profile = power_backend.get_active_profile()
    except PowerBackendError as error:
        status_label.set_text(
            f"Configured mode: {display_text}\n"
            f"Active profile unavailable: {error}"
        )
        return

    status_label.set_text(
        f"Configured mode: {display_text}\n"
        f"Active profile: {active_profile}"
    )


def load_saved_power_mode():
    """
    Load and return the configured power mode.
    """
    settings = load_settings()

    return settings["power_mode"]


def apply_saved_power_mode(
    power_backend,
    mode_buttons,
    status_label,
):
    """
    Apply the saved power mode during UI initialization.

    Failures are displayed in the settings panel and do not prevent the
    rest of the UI from starting.
    """
    try:
        power_mode = load_saved_power_mode()
    except (
        OSError,
        json.JSONDecodeError,
        ValueError,
    ) as error:
        set_selected_power_mode(
            mode_buttons,
            DEFAULT_POWER_MODE,
        )
        status_label.set_text(f"Could not load saved power mode: {error}")
        return

    set_selected_power_mode(mode_buttons, power_mode)
    display_text = get_power_mode_display_text(power_mode)

    try:
        active_profile = power_backend.apply_power_mode(power_mode)
    except PowerBackendError as error:
        status_label.set_text(
            f"Configured mode: {display_text}\n"
            "Could not apply the saved mode during startup:\n"
            f"{error}"
        )
        return

    status_label.set_text(
        f"Applied saved mode: {display_text}\n"
        f"Active profile: {active_profile}"
    )


def on_open_settings_clicked(
    _button,
    power_backend,
    settings_revealer,
    mode_buttons,
    status_label,
):
    """
    Load the saved settings and show the settings overlay.
    """
    try:
        power_mode = load_saved_power_mode()
    except (
        OSError,
        json.JSONDecodeError,
        ValueError,
    ) as error:
        power_mode = DEFAULT_POWER_MODE
        status_label.set_text(f"Could not load settings: {error}")
    else:
        update_loaded_mode_status(
            status_label,
            power_backend,
            power_mode,
        )

    set_selected_power_mode(
        mode_buttons,
        power_mode,
    )

    settings_revealer.set_can_target(True)
    settings_revealer.set_reveal_child(True)


def on_close_settings_clicked(_button, settings_revealer):
    """
    Start hiding the settings overlay.
    """
    settings_revealer.set_reveal_child(False)


def on_settings_child_revealed(
    settings_revealer,
    _property_specification,
):
    """
    Disable input targeting after the close animation finishes.
    """
    if not settings_revealer.get_child_revealed():
        settings_revealer.set_can_target(False)


def restore_previous_profile(
    power_backend,
    previous_profile,
):
    """
    Try to restore the power profile active before the operation.
    """
    try:
        restored_profile = power_backend.restore_profile(previous_profile)
    except PowerBackendError as error:
        return (
            "The previous active profile could not be restored: "
            f"{error}"
        )

    return (
        "The previous active profile was restored "
        f"({restored_profile})."
    )


def on_save_settings_clicked(
    _button,
    power_backend,
    mode_buttons,
    status_label,
):
    """
    Save the selected power mode, then try to apply its system profile.

    Saving remains independent of system power-profile availability so the
    settings UI can still be tested on development systems such as macOS.
    """
    if power_backend.is_benchmark_running():
        status_label.set_text(
            "A power benchmark is currently running.\n"
            "Wait for it to finish before changing the power mode."
        )
        return

    power_mode = get_selected_power_mode(mode_buttons)
    display_text = get_power_mode_display_text(power_mode)

    try:
        settings_path = save_settings(power_mode)
    except (OSError, ValueError) as error:
        status_label.set_text(
            "Could not save the selected power mode.\n"
            "No power profile changes were made.\n\n"
            f"{error}"
        )
        return

    try:
        previous_profile = power_backend.get_active_profile()
    except PowerBackendError as error:
        status_label.set_text(
            f"Saved mode: {display_text}\n"
            f"Config: {settings_path}\n\n"
            "The mode could not be applied on this system because "
            "the active profile is unavailable:\n"
            f"{error}"
        )
        return

    try:
        active_profile = power_backend.apply_power_mode(power_mode)
    except PowerBackendError as error:
        rollback_status = restore_previous_profile(
            power_backend,
            previous_profile,
        )
        status_label.set_text(
            f"Saved mode: {display_text}\n"
            f"Config: {settings_path}\n\n"
            "Could not apply the selected power mode:\n"
            f"{error}\n\n"
            f"{rollback_status}"
        )
        return

    status_label.set_text(
        f"Saved and applied: {display_text}\n"
        f"Active profile: {active_profile}\n"
        f"Config: {settings_path}"
    )

def create_settings_header(settings_revealer):
    """
    Create the settings title row and close button.
    """
    header = Gtk.Box(
        orientation=Gtk.Orientation.HORIZONTAL,
        spacing=8,
    )
    header.set_hexpand(True)

    title_label = Gtk.Label(label="Power Mode Settings")
    title_label.set_xalign(0)
    title_label.set_hexpand(True)
    title_label.add_css_class("title-2")

    close_button = Gtk.Button(label="Close")
    close_button.connect(
        "clicked",
        on_close_settings_clicked,
        settings_revealer,
    )

    header.append(title_label)
    header.append(close_button)

    return header


def create_power_mode_buttons():
    """
    Create a grouped set of power mode radio buttons.
    """
    button_box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=14,
    )
    button_box.set_hexpand(True)

    mode_buttons = {}
    first_button = None

    for definition in POWER_MODE_DEFINITIONS:
        mode_button = Gtk.CheckButton(
            label=f"{definition.label} ({definition.profile})",
        )
        mode_button.set_halign(Gtk.Align.START)

        if first_button is None:
            first_button = mode_button
        else:
            mode_button.set_group(first_button)

        mode_buttons[definition.identifier] = mode_button
        button_box.append(mode_button)

    mode_buttons[DEFAULT_POWER_MODE].set_active(True)

    return button_box, mode_buttons


def create_save_button(
    power_backend,
    mode_buttons,
    status_label,
):
    """
    Create the Save and Apply button.
    """
    save_button = Gtk.Button(
        label="Save and Apply",
    )
    save_button.set_halign(Gtk.Align.START)

    save_button.connect(
        "clicked",
        on_save_settings_clicked,
        power_backend,
        mode_buttons,
        status_label,
    )

    return save_button


def create_settings_content(power_backend):
    """
    Create the scrollable settings content.

    Returns:
        tuple: Scrolled content, mode button mapping, and status label.
    """
    content_box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=16,
    )
    content_box.set_hexpand(True)

    description_label = create_left_aligned_label(
        "Select a power mode to save in the PDA settings JSON file. "
        "On supported Linux systems, the corresponding system power "
        "profile is also applied."
    )

    mode_button_box, mode_buttons = create_power_mode_buttons()

    default_display_text = get_power_mode_display_text(DEFAULT_POWER_MODE)
    status_label = create_left_aligned_label(
        f"Configured mode: {default_display_text}"
    )
    status_label.set_selectable(True)

    save_button = create_save_button(
        power_backend,
        mode_buttons,
        status_label,
    )

    content_box.append(description_label)
    content_box.append(Gtk.Separator())
    content_box.append(mode_button_box)
    content_box.append(save_button)
    content_box.append(Gtk.Separator())
    content_box.append(status_label)

    scrolled_window = Gtk.ScrolledWindow()
    scrolled_window.set_policy(
        Gtk.PolicyType.NEVER,
        Gtk.PolicyType.AUTOMATIC,
    )
    scrolled_window.set_hexpand(True)
    scrolled_window.set_vexpand(True)
    scrolled_window.set_child(content_box)

    return scrolled_window, mode_buttons, status_label


def create_settings_panel(
    settings_revealer,
    power_backend,
):
    """
    Build the full-screen power mode settings panel.

    Returns:
        tuple: Settings panel, mode button mapping, and status label.
    """
    background_box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
    )
    background_box.set_halign(Gtk.Align.FILL)
    background_box.set_valign(Gtk.Align.FILL)
    background_box.set_hexpand(True)
    background_box.set_vexpand(True)
    background_box.add_css_class("background")

    panel_box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=16,
    )
    panel_box.set_halign(Gtk.Align.FILL)
    panel_box.set_valign(Gtk.Align.FILL)
    panel_box.set_hexpand(True)
    panel_box.set_vexpand(True)
    panel_box.set_margin_top(24)
    panel_box.set_margin_bottom(24)
    panel_box.set_margin_start(24)
    panel_box.set_margin_end(24)

    (
        settings_content,
        mode_buttons,
        status_label,
    ) = create_settings_content(power_backend)

    panel_box.append(create_settings_header(settings_revealer))
    panel_box.append(settings_content)

    background_box.append(panel_box)

    return background_box, mode_buttons, status_label


def create_settings_revealer(power_backend):
    """
    Create the hidden full-screen settings revealer.

    Returns:
        tuple: Revealer, mode button mapping, and status label.
    """
    settings_revealer = Gtk.Revealer()
    settings_revealer.set_halign(Gtk.Align.FILL)
    settings_revealer.set_valign(Gtk.Align.FILL)
    settings_revealer.set_hexpand(True)
    settings_revealer.set_vexpand(True)
    settings_revealer.set_transition_type(Gtk.RevealerTransitionType.CROSSFADE)
    settings_revealer.set_transition_duration(200)
    settings_revealer.set_reveal_child(False)
    settings_revealer.set_can_target(False)

    (
        settings_panel,
        mode_buttons,
        status_label,
    ) = create_settings_panel(
        settings_revealer,
        power_backend,
    )

    settings_revealer.set_child(settings_panel)
    settings_revealer.connect(
        "notify::child-revealed",
        on_settings_child_revealed,
    )

    return settings_revealer, mode_buttons, status_label


def create_settings_button(
    power_backend,
    settings_revealer,
    mode_buttons,
    status_label,
):
    """
    Create the button that opens the settings overlay.
    """
    settings_icon = Gtk.Label()
    settings_icon.set_markup('<span size="x-large">⚙</span>')

    settings_button = Gtk.Button()
    settings_button.set_child(settings_icon)
    settings_button.set_tooltip_text("Power Mode Settings")

    settings_button.connect(
        "clicked",
        on_open_settings_clicked,
        power_backend,
        settings_revealer,
        mode_buttons,
        status_label,
    )

    return settings_button


def create_settings_controls(power_backend):
    """
    Create the settings revealer and its launch button.

    The saved power mode is applied once while the controls are created.

    Returns:
        tuple: Settings revealer and settings launch button.
    """
    (
        settings_revealer,
        mode_buttons,
        status_label,
    ) = create_settings_revealer(power_backend)

    apply_saved_power_mode(
        power_backend,
        mode_buttons,
        status_label,
    )

    settings_button = create_settings_button(
        power_backend,
        settings_revealer,
        mode_buttons,
        status_label,
    )

    return settings_revealer, settings_button
