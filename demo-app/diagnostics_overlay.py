# diagnostics_overlay.py
# Builds the diagnostics overlay scaffold for the PDA GTK demo.
# Owner: Jiesui
# Last updated: July 2026

"""
Diagnostics overlay UI for the PDA GTK demo.

This module adds a fixed diagnostics button and an overlay panel with
placeholder script categories. The Start and Stop buttons currently
update mock status text only. Real script execution can be connected
later after script paths and command behavior are finalized.
"""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


SCRIPT_CATEGORIES = [
    {
        "name": "CPU Monitor",
        "path": "scripts/cpu_monitor_placeholder.py",
        "description": "Placeholder for CPU load and frequency checks."
    },
    {
        "name": "Power Monitor",
        "path": "scripts/power_monitor_placeholder.py",
        "description": "Placeholder for power logging or governor checks."
    }
]


def create_left_aligned_label(text):
    """
    Create a reusable left-aligned label for overlay text.
    """
    label = Gtk.Label(label=text)
    label.set_xalign(0)
    label.set_wrap(True)

    return label


def draw_diagnostics_background(_area, context, width, height):
    """
    Draw an opaque diagnostics background.

    Drawing the background directly is more reliable than depending on
    GTK theme CSS for this overlay scaffold.
    """
    context.set_source_rgb(0.96, 0.96, 0.95)
    context.rectangle(0, 0, width, height)
    context.fill()


def update_script_status(status_label, category_name, action_name):
    """
    Update placeholder status text for a script category.

    The real script runner is intentionally not connected yet because
    script paths, permissions, and output behavior are still undecided.
    """
    status_label.set_text(
        f"Status: {action_name} clicked for {category_name}. "
        "Script runner is not connected yet."
    )


def on_open_button_clicked(_button, diagnostics_revealer):
    """
    Show the diagnostics overlay panel.
    """
    diagnostics_revealer.set_can_target(True)
    diagnostics_revealer.set_reveal_child(True)


def on_close_button_clicked(_button, diagnostics_revealer):
    """
    Hide the diagnostics overlay panel.
    """
    diagnostics_revealer.set_reveal_child(False)
    diagnostics_revealer.set_can_target(False)


def create_action_button_row(category_name, status_label):
    """
    Create placeholder Start and Stop buttons for one script category.
    """
    button_row = Gtk.Box(
        orientation=Gtk.Orientation.HORIZONTAL,
        spacing=8
    )
    button_row.set_halign(Gtk.Align.START)

    start_button = Gtk.Button(label="Start")
    stop_button = Gtk.Button(label="Stop")

    start_button.connect(
        "clicked",
        lambda _button: update_script_status(
            status_label,
            category_name,
            "Start"
        )
    )
    stop_button.connect(
        "clicked",
        lambda _button: update_script_status(
            status_label,
            category_name,
            "Stop"
        )
    )

    button_row.append(start_button)
    button_row.append(stop_button)

    return button_row


def create_script_category_expander(category):
    """
    Create one expandable placeholder script category.
    """
    category_name = category["name"]

    content_box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=8
    )
    content_box.set_margin_top(8)
    content_box.set_margin_bottom(8)
    content_box.set_margin_start(8)
    content_box.set_margin_end(8)

    path_label = create_left_aligned_label(
        f"Script path: {category['path']}"
    )
    description_label = create_left_aligned_label(
        category["description"]
    )
    status_label = create_left_aligned_label(
        "Status: Not running"
    )

    content_box.append(path_label)
    content_box.append(description_label)
    content_box.append(
        create_action_button_row(category_name, status_label)
    )
    content_box.append(status_label)

    expander = Gtk.Expander(label=category_name)
    expander.set_child(content_box)

    return expander


def create_diagnostics_header(diagnostics_revealer):
    """
    Create the overlay title row and close button.
    """
    header = Gtk.Box(
        orientation=Gtk.Orientation.HORIZONTAL,
        spacing=8
    )
    header.set_hexpand(True)

    title = Gtk.Label(label="Diagnostics")
    title.set_xalign(0)
    title.set_hexpand(True)
    title.add_css_class("title-3")

    close_button = Gtk.Button(label="Close")
    close_button.connect(
        "clicked",
        on_close_button_clicked,
        diagnostics_revealer
    )

    header.append(title)
    header.append(close_button)

    return header


def create_category_list():
    """
    Create the scrollable list of placeholder script categories.
    """
    category_list = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=8
    )

    for category in SCRIPT_CATEGORIES:
        category_list.append(
            create_script_category_expander(category)
        )

    scrolled_window = Gtk.ScrolledWindow()
    scrolled_window.set_policy(
        Gtk.PolicyType.NEVER,
        Gtk.PolicyType.AUTOMATIC
    )
    scrolled_window.set_vexpand(True)
    scrolled_window.set_child(category_list)

    return scrolled_window


def create_diagnostics_panel(diagnostics_revealer):
    """
    Build the full-screen diagnostics overlay panel.
    """
    panel_overlay = Gtk.Overlay()
    panel_overlay.set_hexpand(True)
    panel_overlay.set_vexpand(True)

    background = Gtk.DrawingArea()
    background.set_draw_func(draw_diagnostics_background)

    panel_overlay.set_child(background)

    panel_box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=12
    )
    panel_box.set_margin_top(24)
    panel_box.set_margin_bottom(24)
    panel_box.set_margin_start(24)
    panel_box.set_margin_end(24)

    intro_label = create_left_aligned_label(
        "Placeholder script launcher. Real script execution and output "
        "display will be added after the script interface is finalized."
    )

    panel_box.append(
        create_diagnostics_header(diagnostics_revealer)
    )
    panel_box.append(intro_label)
    panel_box.append(create_category_list())

    panel_overlay.add_overlay(panel_box)

    return panel_overlay


def create_diagnostics_revealer():
    """
    Create the hidden overlay panel revealer.
    """
    diagnostics_revealer = Gtk.Revealer()
    diagnostics_revealer.set_halign(Gtk.Align.FILL)
    diagnostics_revealer.set_valign(Gtk.Align.FILL)
    diagnostics_revealer.set_hexpand(True)
    diagnostics_revealer.set_vexpand(True)
    diagnostics_revealer.set_transition_type(
        Gtk.RevealerTransitionType.CROSSFADE
    )
    diagnostics_revealer.set_transition_duration(200)
    diagnostics_revealer.set_reveal_child(False)
    diagnostics_revealer.set_can_target(False)
    diagnostics_revealer.set_child(
        create_diagnostics_panel(diagnostics_revealer)
    )

    return diagnostics_revealer


def create_diagnostics_button(diagnostics_revealer):
    """
    Create the fixed bottom-right diagnostics button.
    """
    diagnostics_button = Gtk.Button(label="Diagnostics")
    diagnostics_button.set_halign(Gtk.Align.END)
    diagnostics_button.set_valign(Gtk.Align.END)
    diagnostics_button.set_margin_end(12)
    diagnostics_button.set_margin_bottom(12)

    diagnostics_button.connect(
        "clicked",
        on_open_button_clicked,
        diagnostics_revealer
    )

    return diagnostics_button


def create_diagnostics_overlay(main_content):
    """
    Wrap the main demo content with a diagnostics overlay.
    """
    root_overlay = Gtk.Overlay()
    root_overlay.set_child(main_content)

    diagnostics_revealer = create_diagnostics_revealer()

    root_overlay.add_overlay(
        create_diagnostics_button(diagnostics_revealer)
    )
    root_overlay.add_overlay(diagnostics_revealer)

    return root_overlay