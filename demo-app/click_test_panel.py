"""
Touch / click test panel UI for the PDA GTK demo.

This module owns the test label, test button, and click counter state.
"""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


def on_button_clicked(button, status_label, click_state):
    """
    Increase the click counter and update the status label.
    """
    click_state["count"] += 1
    status_label.set_text(
        f"Click count: {click_state['count']}"
    )


def create_click_test_panel():
    """
    Build the touch/click test UI as a reusable GTK container.
    """
    panel = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=12
    )
    panel.set_hexpand(True)

    # Status label used to show whether user input has been received.
    status_label = Gtk.Label(
        label="Click count: 0"
    )

    # Mutable state used by the clicked callback.
    click_state = {
        "count": 0
    }

    # Large test button for touch/click interaction.
    button = Gtk.Button(
        label="Test Touch / Click"
    )
    button.set_vexpand(False)
    button.set_hexpand(True)
    button.set_size_request(-1, 160)

    # Connect the button's clicked signal to the callback function.
    button.connect(
        "clicked",
        on_button_clicked,
        status_label,
        click_state
    )

    panel.append(status_label)
    panel.append(button)

    return panel