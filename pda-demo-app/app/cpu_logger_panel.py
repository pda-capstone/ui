# cpu_logger_panel.py
# Builds the standalone CPU logging controls for PDA diagnostics.
# Owner: Jiesui
# Last updated: August 2026

"""
CPU logging panel for the PDA GTK diagnostics overlay.

This panel starts and stops read-only CPU monitoring without changing
power profiles, governors, or benchmark configuration.
"""

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from app.cpu_logger import CpuLogger, CpuLoggerError


DEFAULT_DURATION_SECONDS = 30
MINIMUM_DURATION_SECONDS = 1
MAXIMUM_DURATION_SECONDS = 3600
DEFAULT_OUTPUT_FILENAME = "cpu_log.csv"


def create_left_aligned_label(text):
    """
    Create a reusable left-aligned label.
    """
    label = Gtk.Label(label=text)
    label.set_xalign(0)
    label.set_wrap(True)

    return label


def create_form_label(text):
    """
    Create a label used on the left side of a form row.
    """
    label = Gtk.Label(label=text)
    label.set_xalign(0)
    label.set_halign(Gtk.Align.START)
    label.set_valign(Gtk.Align.CENTER)

    return label


def create_duration_input():
    """
    Create the CPU logging duration input.
    """
    duration_input = Gtk.SpinButton.new_with_range(
        MINIMUM_DURATION_SECONDS,
        MAXIMUM_DURATION_SECONDS,
        1,
    )
    duration_input.set_value(DEFAULT_DURATION_SECONDS)
    duration_input.set_numeric(True)
    duration_input.set_hexpand(True)

    return duration_input


def create_output_entry():
    """
    Create the CPU logging CSV output filename entry.
    """
    output_entry = Gtk.Entry()
    output_entry.set_text(DEFAULT_OUTPUT_FILENAME)
    output_entry.set_hexpand(True)
    output_entry.set_placeholder_text("cpu_log.csv")

    return output_entry


def create_logging_form(
    duration_input,
    output_entry,
):
    """
    Create the CPU logging configuration form.
    """
    form_grid = Gtk.Grid()
    form_grid.set_column_spacing(12)
    form_grid.set_row_spacing(12)
    form_grid.set_hexpand(True)

    duration_label = create_form_label("Duration:")
    output_label = create_form_label("Output file:")
    duration_unit_label = create_form_label("seconds")

    form_grid.attach(duration_label, 0, 0, 1, 1)
    form_grid.attach(duration_input, 1, 0, 1, 1)
    form_grid.attach(duration_unit_label, 2, 0, 1, 1)

    form_grid.attach(output_label, 0, 1, 1, 1)
    form_grid.attach(output_entry, 1, 1, 2, 1)

    return form_grid


def format_metric(value, suffix=""):
    """
    Format a numeric metric or show Unavailable.
    """
    if value is None:
        return "Unavailable"

    return f"{value:.2f}{suffix}"


def update_metrics_labels(metrics, labels):
    """
    Update visible CPU metrics on the GTK main thread.
    """
    governor = metrics["governor"] or "Unavailable"

    labels["governor"].set_text(f"Governor: {governor}")
    labels["frequency"].set_text(
        f"CPU Frequency: {format_metric(metrics['frequency_mhz'], ' MHz')}"
    )
    labels["usage"].set_text(
        f"CPU Usage: {format_metric(metrics['usage_percent'], '%')}"
    )
    labels["temperature"].set_text(
        f"Temperature: {format_metric(metrics['temperature_c'], ' °C')}"
    )

    return False


def on_sample_received(metrics, labels):
    """
    Forward a worker-thread sample to GTK.
    """
    GLib.idle_add(
        update_metrics_labels,
        metrics,
        labels,
    )


def on_logging_finished(
    stopped_early,
    status_label,
    start_button,
    stop_button,
):
    """
    Restore controls after the logger finishes.
    """

    def update_ui():
        if stopped_early:
            status_label.set_text("Status: Logging stopped.")
        else:
            status_label.set_text("Status: Logging complete.")

        start_button.set_sensitive(True)
        stop_button.set_sensitive(False)

        return False

    GLib.idle_add(update_ui)


def on_logging_error(
    error_message,
    status_label,
    start_button,
    stop_button,
):
    """
    Display a logger error and restore controls.
    """

    def update_ui():
        status_label.set_text(f"Status: Logging failed: {error_message}")

        start_button.set_sensitive(True)
        stop_button.set_sensitive(False)

        return False

    GLib.idle_add(update_ui)


def on_start_clicked(
    _button,
    cpu_logger,
    duration_input,
    output_entry,
    status_label,
    start_button,
    stop_button,
    labels,
):
    """
    Start a standalone CPU logging session.
    """
    duration_seconds = duration_input.get_value_as_int()
    output_text = output_entry.get_text().strip()

    if not output_text:
        status_label.set_text("Status: Enter an output filename.")
        return

    if not output_text.lower().endswith(".csv"):
        output_text = f"{output_text}.csv"
        output_entry.set_text(output_text)

    output_path = Path(output_text)

    try:
        cpu_logger.start(
            duration_seconds=duration_seconds,
            output_path=output_path,
            sample_callback=lambda metrics: on_sample_received(
                metrics,
                labels,
            ),
            finished_callback=lambda stopped: on_logging_finished(
                stopped,
                status_label,
                start_button,
                stop_button,
            ),
            error_callback=lambda message: on_logging_error(
                message,
                status_label,
                start_button,
                stop_button,
            ),
        )
    except CpuLoggerError as error:
        status_label.set_text(f"Status: {error}")
        return

    status_label.set_text(f"Status: Logging to {output_path}")

    start_button.set_sensitive(False)
    stop_button.set_sensitive(True)


def on_stop_clicked(
    _button,
    cpu_logger,
    status_label,
    stop_button,
):
    """
    Request that CPU logging stop.
    """
    cpu_logger.stop()

    status_label.set_text("Status: Stopping...")
    stop_button.set_sensitive(False)


def create_logging_buttons(
    cpu_logger,
    duration_input,
    output_entry,
    status_label,
    metrics_labels,
):
    """
    Create the CPU logging Start and Stop buttons.
    """
    button_row = Gtk.Box(
        orientation=Gtk.Orientation.HORIZONTAL,
        spacing=8,
    )

    start_button = Gtk.Button(label="Start Logging")
    start_button.set_hexpand(True)

    stop_button = Gtk.Button(label="Stop")
    stop_button.set_sensitive(False)

    start_button.connect(
        "clicked",
        on_start_clicked,
        cpu_logger,
        duration_input,
        output_entry,
        status_label,
        start_button,
        stop_button,
        metrics_labels,
    )

    stop_button.connect(
        "clicked",
        on_stop_clicked,
        cpu_logger,
        status_label,
        stop_button,
    )

    button_row.append(start_button)
    button_row.append(stop_button)

    return button_row


def create_cpu_logger_panel():
    """
    Build the standalone CPU logger diagnostics panel.
    """
    cpu_logger = CpuLogger()

    panel_box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=16,
    )
    panel_box.set_hexpand(True)

    title_label = create_left_aligned_label("CPU Logging")
    title_label.add_css_class("title-3")

    description_label = create_left_aligned_label(
        "Record the current CPU governor, frequency, utilization, "
        "and temperature without changing system power settings."
    )

    duration_input = create_duration_input()
    output_entry = create_output_entry()

    logging_form = create_logging_form(
        duration_input,
        output_entry,
    )

    status_label = create_left_aligned_label("Status: Ready")
    status_label.set_selectable(True)

    metrics_labels = {
        "governor": create_left_aligned_label("Governor: --"),
        "frequency": create_left_aligned_label("CPU Frequency: --"),
        "usage": create_left_aligned_label("CPU Usage: --"),
        "temperature": create_left_aligned_label("Temperature: --"),
    }

    button_row = create_logging_buttons(
        cpu_logger,
        duration_input,
        output_entry,
        status_label,
        metrics_labels,
    )

    panel_box.append(title_label)
    panel_box.append(description_label)
    panel_box.append(logging_form)
    panel_box.append(button_row)
    panel_box.append(status_label)

    for label in metrics_labels.values():
        panel_box.append(label)

    return panel_box
