# fps_display.py
# Builds and updates the PDA GTK demo FPS display.
# Owner: Jiesui
# Last updated: July 2026

"""
FPS display helpers for the PDA GTK demo.

This module owns the FPS label widget and the lightweight frame-rate
calculation used during UI responsiveness checks.
"""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


FPS_UPDATE_INTERVAL_SECONDS = 0.5


def create_fps_label():
    """
    Create the persistent lower-left FPS display.
    """
    fps_label = Gtk.Label(label="FPS: --.-")
    fps_label.set_xalign(0)
    fps_label.set_halign(Gtk.Align.START)
    fps_label.set_valign(Gtk.Align.END)
    fps_label.set_margin_start(8)
    fps_label.set_margin_bottom(8)
    fps_label.set_can_target(False)

    return fps_label


def create_fps_state(fps_label, start_time_seconds):
    """
    Store FPS calculation state separately from the click test panel.
    """
    return {
        "fps_label": fps_label,
        "window_start_seconds": start_time_seconds,
        "frame_count": 0
    }


def update_fps_label(fps_state, current_time_seconds):
    """
    Update the FPS label from GTK frame-clock ticks.
    """
    fps_state["frame_count"] += 1
    elapsed_seconds = (
        current_time_seconds
        - fps_state["window_start_seconds"]
    )

    if elapsed_seconds < FPS_UPDATE_INTERVAL_SECONDS:
        return

    fps_value = fps_state["frame_count"] / elapsed_seconds

    fps_state["fps_label"].set_text(f"FPS: {fps_value:4.1f}")
    fps_state["window_start_seconds"] = current_time_seconds
    fps_state["frame_count"] = 0