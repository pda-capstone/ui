# diagnostics_overlay.py
# Builds the diagnostics overlay scaffold for the PDA GTK demo.
# Owner: Jiesui
# Last updated: July 2026

"""
Diagnostics overlay UI for the PDA GTK demo.

This module creates the diagnostics overlay and integrates the
bottom-right Diagnostics and Power Mode Settings controls.
"""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from power_benchmark_panel import create_power_benchmark_panel
from settings_overlay import create_settings_controls
from power_backend import PowerBackend


def create_left_aligned_label(text):
    """
    Create a reusable left-aligned label for overlay text.
    """
    label = Gtk.Label(label=text)
    label.set_xalign(0)
    label.set_wrap(True)

    return label


def on_open_button_clicked(_button, diagnostics_revealer):
    """
    Show the diagnostics overlay panel.
    """
    diagnostics_revealer.set_can_target(True)
    diagnostics_revealer.set_reveal_child(True)


def on_close_button_clicked(_button, diagnostics_revealer):
    """
    Start hiding the diagnostics overlay panel.
    """
    diagnostics_revealer.set_reveal_child(False)


def on_revealer_child_revealed(
    diagnostics_revealer,
    _property_specification,
):
    """
    Disable input targeting after the close animation finishes.
    """
    if not diagnostics_revealer.get_child_revealed():
        diagnostics_revealer.set_can_target(False)


def create_diagnostics_header(diagnostics_revealer):
    """
    Create the overlay title row and close button.
    """
    header = Gtk.Box(
        orientation=Gtk.Orientation.HORIZONTAL,
        spacing=8,
    )
    header.set_hexpand(True)

    title_label = Gtk.Label(label="Diagnostics")
    title_label.set_xalign(0)
    title_label.set_hexpand(True)
    title_label.add_css_class("title-2")

    close_button = Gtk.Button(label="Close")
    close_button.connect(
        "clicked",
        on_close_button_clicked,
        diagnostics_revealer,
    )

    header.append(title_label)
    header.append(close_button)

    return header


def create_diagnostics_content(power_backend):
    """
    Create the scrollable diagnostics tool content.
    """
    content_box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=16,
    )
    content_box.set_hexpand(True)

    intro_label = create_left_aligned_label(
        "Configure development and measurement tools for the PDA demo. "
        "Benchmark execution will be connected after the power script "
        "interface and permissions are finalized."
    )

    content_box.append(intro_label)
    content_box.append(Gtk.Separator())
    content_box.append(create_power_benchmark_panel(power_backend))

    scrolled_window = Gtk.ScrolledWindow()
    scrolled_window.set_policy(
        Gtk.PolicyType.NEVER,
        Gtk.PolicyType.AUTOMATIC,
    )
    scrolled_window.set_hexpand(True)
    scrolled_window.set_vexpand(True)
    scrolled_window.set_child(content_box)

    return scrolled_window


def create_diagnostics_panel(diagnostics_revealer, power_backend):
    """
    Build the full-screen diagnostics overlay panel.
    """
    background_box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
    )
    background_box.set_halign(Gtk.Align.FILL)
    background_box.set_valign(Gtk.Align.FILL)
    background_box.set_hexpand(True)
    background_box.set_vexpand(True)

    # Fill the entire overlay with the active GTK theme background.
    # Margins belong to the inner content box, not this background box.
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

    panel_box.append(
        create_diagnostics_header(diagnostics_revealer)
    )
    panel_box.append(create_diagnostics_content(power_backend))

    background_box.append(panel_box)

    return background_box


def create_diagnostics_revealer(power_backend):
    """
    Create the hidden diagnostics overlay revealer.
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
        create_diagnostics_panel(diagnostics_revealer, power_backend)
    )
    diagnostics_revealer.connect(
        "notify::child-revealed",
        on_revealer_child_revealed,
    )

    return diagnostics_revealer


def create_diagnostics_button(diagnostics_revealer):
    """
    Create the Diagnostics button.
    """
    diagnostics_button = Gtk.Button(label="Diagnostics")

    diagnostics_button.connect(
        "clicked",
        on_open_button_clicked,
        diagnostics_revealer,
    )

    return diagnostics_button


def create_bottom_action_row(
    diagnostics_revealer,
    settings_button,
):
    """
    Create the bottom-right diagnostics and settings controls.
    """
    button_row = Gtk.Box(
        orientation=Gtk.Orientation.HORIZONTAL,
        spacing=8,
    )
    button_row.set_halign(Gtk.Align.END)
    button_row.set_valign(Gtk.Align.END)
    button_row.set_margin_end(12)
    button_row.set_margin_bottom(12)

    diagnostics_button = create_diagnostics_button(
        diagnostics_revealer
    )

    button_row.append(diagnostics_button)
    button_row.append(settings_button)

    return button_row


def create_diagnostics_overlay(main_content, power_backend=None):
    """
    Wrap the main content with diagnostics and settings overlays.
    """
    root_overlay = Gtk.Overlay()
    root_overlay.set_hexpand(True)
    root_overlay.set_vexpand(True)
    root_overlay.set_child(main_content)

    if power_backend is None:
        power_backend = PowerBackend()

    diagnostics_revealer = create_diagnostics_revealer(
        power_backend
    )

    (
        settings_revealer,
        settings_button,
    ) = create_settings_controls()

    bottom_action_row = create_bottom_action_row(
        diagnostics_revealer,
        settings_button,
    )

    root_overlay.add_overlay(bottom_action_row)
    root_overlay.add_overlay(diagnostics_revealer)
    root_overlay.add_overlay(settings_revealer)

    return root_overlay