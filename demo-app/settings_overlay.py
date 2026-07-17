# settings_overlay.py
# Builds the power mode settings overlay for the PDA GTK demo.
# Owner: Jiesui
# Last updated: July 2026

"""
Power mode settings overlay for the PDA GTK demo.

The overlay allows the user to select a persistent power mode and save
it to the PDA settings JSON file. Applying the selected governor to the
operating system remains the responsibility of the power controller.
"""

import json

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from settings_store import (
    DEFAULT_POWER_MODE,
    load_settings,
    save_settings,
)


POWER_MODE_OPTIONS = (
    {
        "id": "default",
        "label": "Default",
        "governor": "schedutil",
    },
    {
        "id": "low_power",
        "label": "Low Power",
        "governor": "powersave",
    },
    {
        "id": "performance",
        "label": "Performance",
        "governor": "performance",
    },
)


def create_left_aligned_label(text):
    """
    Create a reusable left-aligned label.
    """
    label = Gtk.Label(label=text)
    label.set_xalign(0)
    label.set_wrap(True)

    return label


def get_power_mode_option(power_mode):
    """
    Return the metadata for one power mode.
    """
    for option in POWER_MODE_OPTIONS:
        if option["id"] == power_mode:
            return option

    return POWER_MODE_OPTIONS[0]


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


def update_loaded_mode_status(status_label, power_mode):
    """
    Display the currently configured power mode.
    """
    option = get_power_mode_option(power_mode)

    status_label.set_text(
        f"Configured mode: {option['label']} "
        f"({option['governor']})"
    )


def on_open_settings_clicked(
    _button,
    settings_revealer,
    mode_buttons,
    status_label,
):
    """
    Load the saved settings and show the settings overlay.
    """
    try:
        settings = load_settings()
        power_mode = settings["power_mode"]
    except (
        OSError,
        json.JSONDecodeError,
        ValueError,
    ) as error:
        power_mode = DEFAULT_POWER_MODE
        status_label.set_text(
            f"Could not load settings: {error}"
        )
    else:
        update_loaded_mode_status(
            status_label,
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


def on_save_settings_clicked(
    _button,
    mode_buttons,
    status_label,
):
    """
    Save the selected power mode to the settings JSON file.
    """
    power_mode = get_selected_power_mode(mode_buttons)
    option = get_power_mode_option(power_mode)

    try:
        settings_path = save_settings(power_mode)
    except (OSError, ValueError) as error:
        status_label.set_text(
            f"Could not save settings: {error}"
        )
        return

    status_label.set_text(
        f"Saved configuration: {option['label']} "
        f"({option['governor']})\n"
        f"Config: {settings_path}\n"
        "The operating system governor was not changed."
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

    title_label = Gtk.Label(
        label="Power Mode Settings"
    )
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

    for option in POWER_MODE_OPTIONS:
        button_label = (
            f"{option['label']} "
            f"({option['governor']})"
        )

        mode_button = Gtk.CheckButton(
            label=button_label,
        )
        mode_button.set_halign(Gtk.Align.START)

        if first_button is None:
            first_button = mode_button
        else:
            mode_button.set_group(first_button)

        mode_buttons[option["id"]] = mode_button
        button_box.append(mode_button)

    mode_buttons[DEFAULT_POWER_MODE].set_active(True)

    return button_box, mode_buttons


def create_save_button(mode_buttons, status_label):
    """
    Create the Save Settings button.
    """
    save_button = Gtk.Button(
        label="Save Settings",
    )
    save_button.set_halign(Gtk.Align.START)

    save_button.connect(
        "clicked",
        on_save_settings_clicked,
        mode_buttons,
        status_label,
    )

    return save_button


def create_settings_content():
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
        "Select the power mode that the power controller should use. "
        "The selection is saved to the PDA settings JSON file."
    )

    mode_button_box, mode_buttons = (
        create_power_mode_buttons()
    )

    status_label = create_left_aligned_label(
        "Configured mode: Default (schedutil)"
    )
    status_label.set_selectable(True)

    save_button = create_save_button(
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


def create_settings_panel(settings_revealer):
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

    # Fill the complete overlay using the current GTK theme.
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
    ) = create_settings_content()

    panel_box.append(
        create_settings_header(settings_revealer)
    )
    panel_box.append(settings_content)

    background_box.append(panel_box)

    return background_box, mode_buttons, status_label


def create_settings_revealer():
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
    settings_revealer.set_transition_type(
        Gtk.RevealerTransitionType.CROSSFADE
    )
    settings_revealer.set_transition_duration(200)
    settings_revealer.set_reveal_child(False)
    settings_revealer.set_can_target(False)

    (
        settings_panel,
        mode_buttons,
        status_label,
    ) = create_settings_panel(settings_revealer)

    settings_revealer.set_child(settings_panel)
    settings_revealer.connect(
        "notify::child-revealed",
        on_settings_child_revealed,
    )

    return settings_revealer, mode_buttons, status_label


def create_settings_button(
    settings_revealer,
    mode_buttons,
    status_label,
):
    """
    Create the button that opens the settings overlay.
    """
    settings_icon = Gtk.Label()
    settings_icon.set_markup(
        '<span size="x-large">⚙</span>'
    )

    settings_button = Gtk.Button()
    settings_button.set_child(settings_icon)
    settings_button.set_tooltip_text(
        "Power Mode Settings"
    )

    settings_button.connect(
        "clicked",
        on_open_settings_clicked,
        settings_revealer,
        mode_buttons,
        status_label,
    )

    return settings_button


def create_settings_controls():
    """
    Create the settings revealer and its launch button.

    Returns:
        tuple: Settings revealer and settings launch button.
    """
    (
        settings_revealer,
        mode_buttons,
        status_label,
    ) = create_settings_revealer()

    settings_button = create_settings_button(
        settings_revealer,
        mode_buttons,
        status_label,
    )

    return settings_revealer, settings_button