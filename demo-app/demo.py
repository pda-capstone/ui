#!/usr/bin/env python3

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


def activate(app):
    """
    Create and present the main application window.

    In GTK applications, the activate signal is emitted when the
    application is launched and ready to create its main window.
    """
    window = Gtk.ApplicationWindow(application=app)
    window.set_title("PDA GTK Demo")

    # Development preview size.
    # This is not a fixed display size. The Wayland compositor may resize
    # or fullscreen the application depending on the target environment.
    window.set_default_size(720, 720)

    # For final device or kiosk-style deployment, fullscreen behavior may be
    # controlled by compositor configuration. This line can also be
    # enabled during testing if fullscreen behavior needs to be verified.
    # window.fullscreen()

    # Main vertical layout container.
    # GTK will adapt the child widgets to the available window size.
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

    # Demo title shown at the top of the application.
    title = Gtk.Label(label="Pocket Distro Alpha")
    title.add_css_class("title-2")

    # Add widgets to the vertical layout in display order.
    box.append(title)
    box.append(create_daemon_status_panel())
    box.append(create_click_test_panel())

    # Set the layout container as the window content and show the window.
    window.set_child(box)
    window.present()


def main():
    """
    Application entry point.
    """
    app = Gtk.Application(
        # Reverse-domain application ID.
        # This helps identify the application in desktop/session systems.
        application_id="edu.pda.gtkdemo",
        flags=Gio.ApplicationFlags.DEFAULT_FLAGS
    )

    app.connect("activate", activate)

    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())