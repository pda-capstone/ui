# click_test_panel.py
# Builds the PDA GTK touch/click test panel and click counter behavior.
# Owner: Jiesui
# Last updated: July 2026

"""
Touch / click test panel UI for the PDA GTK demo.

This module owns the test label, test button, click counter state, and
coordinates the click effect and FPS helper modules.
"""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from click_effects import (
    add_click_effect,
    create_effect_area,
    create_effect_state,
    get_current_time_seconds,
    has_active_effects,
    microseconds_to_seconds,
    prune_finished_effects
)
from fps_display import (
    create_fps_label,
    create_fps_state,
    update_fps_label
)


def create_panel_state(fps_label):
    """
    Store state shared by the click test panel callback functions.
    """
    current_time_seconds = get_current_time_seconds()

    return {
        "click_state": {
            "count": 0
        },
        "effect_state": create_effect_state(),
        "fps_state": create_fps_state(
            fps_label,
            current_time_seconds
        )
    }


def on_frame_tick(widget, frame_clock, panel_state):
    """
    Keep FPS current and redraw the effect area while animations are active.
    """
    current_time_seconds = microseconds_to_seconds(
        frame_clock.get_frame_time()
    )
    effect_state = panel_state["effect_state"]

    update_fps_label(
        panel_state["fps_state"],
        current_time_seconds
    )
    prune_finished_effects(
        effect_state,
        current_time_seconds
    )

    if has_active_effects(effect_state):
        widget.queue_draw()

    return True


def on_button_clicked(_button, status_label, panel_state, effect_area):
    """
    Increase the click counter, update the label, and start click feedback.
    """
    click_state = panel_state["click_state"]

    click_state["count"] += 1
    status_label.set_text(
        f"Click count: {click_state['count']}"
    )

    add_click_effect(
        effect_area,
        panel_state["effect_state"]
    )


def create_button_overlay(button, effect_area):
    """
    Place the click effect DrawingArea over the test button.
    """
    button_overlay = Gtk.Overlay()
    button_overlay.set_hexpand(True)
    button_overlay.set_child(button)
    button_overlay.add_overlay(effect_area)

    return button_overlay


def create_click_test_panel():
    """
    Build the touch/click test UI as a reusable GTK container.
    """
    root_overlay = Gtk.Overlay()
    root_overlay.set_hexpand(True)
    root_overlay.set_vexpand(True)

    panel = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=12
    )
    panel.set_hexpand(True)
    panel.set_vexpand(True)

    # The label gives immediate feedback during touchscreen input checks.
    status_label = Gtk.Label(
        label="Click count: 0"
    )

    fps_label = create_fps_label()
    panel_state = create_panel_state(fps_label)
    effect_area = create_effect_area(
        panel_state["effect_state"]
    )

    # The large target makes touch testing practical on the small PDA screen.
    button = Gtk.Button(
        label="Test Touch / Click"
    )
    button.set_vexpand(False)
    button.set_hexpand(True)
    button.set_size_request(-1, 160)

    button.connect(
        "clicked",
        on_button_clicked,
        status_label,
        panel_state,
        effect_area
    )

    panel.append(status_label)
    panel.append(
        create_button_overlay(button, effect_area)
    )

    root_overlay.set_child(panel)
    root_overlay.add_overlay(fps_label)

    # The tick callback must be attached to the DrawingArea because that is
    # the widget whose draw function renders the click effects.
    effect_area.add_tick_callback(
        on_frame_tick,
        panel_state
    )

    return root_overlay