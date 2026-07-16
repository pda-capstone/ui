# diagnostics_overlay.py
# Builds the diagnostics overlay scaffold for the PDA GTK demo.
# Owner: Jiesui
# Last updated: July 2026

"""
Diagnostics overlay UI for the PDA GTK demo.

This module creates the fixed diagnostics button, full-screen overlay,
background, title row, and close behavior. Diagnostic tools are
implemented in separate panel modules so that this file remains focused
on overlay layout and visibility.
"""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from power_benchmark_panel import create_power_benchmark_panel


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

    Drawing the background directly avoids relying on theme-specific
    CSS behavior for the full-screen overlay.
    """
    context.set_source_rgb(0.96, 0.96, 0.95)
    context.rectangle(0, 0, width, height)
    context.fill()


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


def create_diagnostics_content():
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
    content_box.append(create_power_benchmark_panel())

    scrolled_window = Gtk.ScrolledWindow()
    scrolled_window.set_policy(
        Gtk.PolicyType.NEVER,
        Gtk.PolicyType.AUTOMATIC,
    )
    scrolled_window.set_hexpand(True)
    scrolled_window.set_vexpand(True)
    scrolled_window.set_child(content_box)

    return scrolled_window


def create_diagnostics_panel(diagnostics_revealer):
    """
    Build the full-screen diagnostics overlay panel.
    """
    panel_overlay = Gtk.Overlay()
    panel_overlay.set_hexpand(True)
    panel_overlay.set_vexpand(True)

    background = Gtk.DrawingArea()
    background.set_hexpand(True)
    background.set_vexpand(True)
    background.set_draw_func(draw_diagnostics_background)

    panel_overlay.set_child(background)

    panel_box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=16,
    )
    panel_box.set_hexpand(True)
    panel_box.set_vexpand(True)
    panel_box.set_margin_top(24)
    panel_box.set_margin_bottom(24)
    panel_box.set_margin_start(24)
    panel_box.set_margin_end(24)

    panel_box.append(
        create_diagnostics_header(diagnostics_revealer)
    )
    panel_box.append(create_diagnostics_content())

    panel_overlay.add_overlay(panel_box)

    return panel_overlay


def create_diagnostics_revealer():
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
        create_diagnostics_panel(diagnostics_revealer)
    )
    diagnostics_revealer.connect(
        "notify::child-revealed",
        on_revealer_child_revealed,
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
        diagnostics_revealer,
    )

    return diagnostics_button


def create_diagnostics_overlay(main_content):
    """
    Wrap the main demo content with a diagnostics overlay.
    """
    root_overlay = Gtk.Overlay()
    root_overlay.set_child(main_content)

    diagnostics_revealer = create_diagnostics_revealer()
    diagnostics_button = create_diagnostics_button(
        diagnostics_revealer
    )

    root_overlay.add_overlay(diagnostics_button)
    root_overlay.add_overlay(diagnostics_revealer)

    return root_overlay