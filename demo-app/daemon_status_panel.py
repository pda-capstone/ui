# daemon_status_panel.py
# Builds the PDA GTK daemon/module status panel and expand behavior.
# Owner: Jiesui
# Last updated: June 2026

"""
Daemon / module status panel UI for the PDA GTK demo.

This module owns the GTK widgets and click behavior for the expandable
status panel. The actual demo state and text formatting come from
module_state.py.
"""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from module_state import (
    get_status_bar_text,
    get_module_detail_lines
)


def create_left_aligned_label(text):
    """
    Create a reusable left-aligned label for status detail rows.
    """
    label = Gtk.Label(label=text)
    label.set_xalign(0)
    return label


def on_status_bar_clicked(button, revealer):
    """
    Toggle the expandable status panel.

    The status bar text is generated from the current system/module state,
    instead of using a fixed module count.
    """
    expanded = not revealer.get_reveal_child()
    revealer.set_reveal_child(expanded)

    button.set_label(get_status_bar_text(expanded))


def create_daemon_status_panel():
    """
    Build the daemon/module status UI as a reusable GTK container.
    """
    panel = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=6
    )
    panel.set_hexpand(True)

    # A button makes the status bar easy to trigger with touch input.
    status_bar = Gtk.Button(
        label=get_status_bar_text(expanded=False)
    )
    status_bar.set_hexpand(True)

    # The details stay in a separate box so D-Bus-backed rows can be added
    # later without changing the expand/collapse behavior.
    status_details = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=6
    )

    for line in get_module_detail_lines():
        status_details.append(
            create_left_aligned_label(line)
        )

    # Revealer gives the status panel an explicit expand/collapse transition.
    status_revealer = Gtk.Revealer()
    status_revealer.set_transition_type(
        Gtk.RevealerTransitionType.SLIDE_DOWN
    )
    status_revealer.set_transition_duration(200)
    status_revealer.set_reveal_child(False)
    status_revealer.set_child(status_details)

    status_bar.connect(
        "clicked",
        on_status_bar_clicked,
        status_revealer
    )

    panel.append(status_bar)
    panel.append(status_revealer)

    return panel