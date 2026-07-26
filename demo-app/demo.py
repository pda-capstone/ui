#!/usr/bin/env python3
# demo.py
# Creates the main GTK demo application window for PDA UI testing.
# Owner: Jiesui
# Last updated: July 2026

"""
PDA GTK Demo

A minimal GTK4 reference application for testing the Wayland UI stack.
This demo is intended to verify that a GTK application can run under
Phosh/Phoc and respond to basic touch/click input.
"""

import gi

# Require GTK 4 before importing Gtk from gi.repository.
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio

from daemon_status_panel import create_daemon_status_panel
from click_test_panel import create_click_test_panel
from diagnostics_overlay import create_diagnostics_overlay


def activate(app):
    """
    Create and present the main application window.

    In GTK applications, the activate signal is emitted when the
    application is launched and ready to create its main window.
    """
    window = Gtk.ApplicationWindow(application=app)
    window.set_title("PDA GTK Demo")

    # This preview size keeps VM testing consistent without assuming the
    # final compositor-managed device resolution.
    window.set_default_size(720, 720)

    # Final fullscreen behavior should be configured by the compositor so
    # the same app can run in both windowed VM tests and device deployment.

    # GTK's vertical box keeps the demo readable as the compositor resizes
    # the window or the app moves between VM and target-device environments.
    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=12
    )
    box.set_margin_top(18)
    box.set_margin_bottom(18)
    box.set_margin_start(20)
    box.set_margin_end(20)
    box.set_vexpand(True)
    box.set_hexpand(True)

    # The title identifies the reference UI during compositor testing.
    title = Gtk.Label(label="Pocket Distro Alpha")
    title.add_css_class("title-2")

    # Keep the status panel above the input test so system state is visible
    # before running touch/click verification.
    box.append(title)
    box.append(create_daemon_status_panel())
    box.append(create_click_test_panel())

    # Set the layout container as the window content and show the window.
    window.set_child(create_diagnostics_overlay(box))
    window.present()


def main():
    """
    Application entry point.
    """
    app = Gtk.Application(
        # Reverse-domain application IDs identify GTK apps in session tools.
        application_id="edu.pda.gtkdemo",
        flags=Gio.ApplicationFlags.DEFAULT_FLAGS
    )

    app.connect("activate", activate)

    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())