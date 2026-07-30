# click_effects.py
# Draws lightweight click ripple and dot animations for PDA GTK demo.
# Owner: Jiesui
# Last updated: July 2026

"""
Click effect drawing helpers for the PDA GTK demo.

This module owns the DrawingArea, ripple animation records, dot animation
records, and Cairo drawing logic used by the click test panel.
"""

import math

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk


RIPPLE_DURATION_SECONDS = 0.6
DOT_DURATION_SECONDS = 0.65
DOT_COUNT = 10
DOT_TRAVEL_DISTANCE = 46
DOT_RADIUS = 3.5


def microseconds_to_seconds(time_us):
    """
    Convert GTK / GLib microsecond timestamps to seconds.
    """
    return time_us / 1_000_000


def get_current_time_seconds():
    """
    Return the current monotonic time in seconds.
    """
    return microseconds_to_seconds(
        GLib.get_monotonic_time()
    )


def create_effect_state():
    """
    Store active click animation records.
    """
    return {
        "ripples": [],
        "dots": []
    }


def create_effect_area(effect_state):
    """
    Create a transparent overlay used only for drawing click effects.
    """
    effect_area = Gtk.DrawingArea()
    effect_area.set_hexpand(True)
    effect_area.set_vexpand(True)
    effect_area.set_halign(Gtk.Align.FILL)
    effect_area.set_valign(Gtk.Align.FILL)
    effect_area.set_can_target(False)
    effect_area.set_draw_func(
        draw_click_effects,
        effect_state
    )

    return effect_area


def add_click_effect(effect_area, effect_state):
    """
    Add one simple ripple and a small ring of dots after a button press.
    """
    current_time_seconds = get_current_time_seconds()
    center_x = effect_area.get_allocated_width() / 2
    center_y = effect_area.get_allocated_height() / 2

    effect_state["ripples"].append(
        {
            "start_time_seconds": current_time_seconds,
            "center_x": center_x,
            "center_y": center_y
        }
    )

    for index in range(DOT_COUNT):
        angle = (math.tau / DOT_COUNT) * index

        effect_state["dots"].append(
            {
                "start_time_seconds": current_time_seconds,
                "center_x": center_x,
                "center_y": center_y,
                "angle": angle
            }
        )

    effect_area.queue_draw()


def has_active_effects(effect_state):
    """
    Check whether any click animations are still visible.
    """
    return bool(
        effect_state["ripples"]
        or effect_state["dots"]
    )


def prune_finished_effects(effect_state, current_time_seconds):
    """
    Remove completed animation records so the demo stays lightweight.
    """
    effect_state["ripples"] = [
        ripple for ripple in effect_state["ripples"]
        if (
            current_time_seconds - ripple["start_time_seconds"]
            < RIPPLE_DURATION_SECONDS
        )
    ]

    effect_state["dots"] = [
        dot for dot in effect_state["dots"]
        if (
            current_time_seconds - dot["start_time_seconds"]
            < DOT_DURATION_SECONDS
        )
    ]


def draw_click_effects(_drawing_area, context, _width, _height, effect_state):
    """
    Draw all active ripple and dot effects.
    """
    current_time_seconds = get_current_time_seconds()

    for ripple in effect_state["ripples"]:
        draw_ripple(context, ripple, current_time_seconds)

    for dot in effect_state["dots"]:
        draw_dot(context, dot, current_time_seconds)


def draw_ripple(context, ripple, current_time_seconds):
    """
    Draw one expanding circle around the button center.
    """
    age_seconds = current_time_seconds - ripple["start_time_seconds"]
    progress = min(age_seconds / RIPPLE_DURATION_SECONDS, 1.0)
    radius = 18 + (76 * progress)
    opacity = 0.45 * (1.0 - progress)

    context.save()
    context.set_source_rgba(0.2, 0.55, 1.0, opacity)
    context.set_line_width(2.0)
    context.arc(
        ripple["center_x"],
        ripple["center_y"],
        radius,
        0,
        math.tau
    )
    context.stroke()
    context.restore()


def draw_dot(context, dot, current_time_seconds):
    """
    Draw one small outward-moving dot.
    """
    age_seconds = current_time_seconds - dot["start_time_seconds"]
    progress = min(age_seconds / DOT_DURATION_SECONDS, 1.0)
    distance = DOT_TRAVEL_DISTANCE * progress
    opacity = 0.55 * (1.0 - progress)

    dot_x = dot["center_x"] + math.cos(dot["angle"]) * distance
    dot_y = dot["center_y"] + math.sin(dot["angle"]) * distance

    context.save()
    context.set_source_rgba(0.2, 0.55, 1.0, opacity)
    context.arc(dot_x, dot_y, DOT_RADIUS, 0, math.tau)
    context.fill()
    context.restore()