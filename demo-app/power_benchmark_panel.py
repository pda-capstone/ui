# power_benchmark_panel.py
# Builds the power benchmark configuration panel for the PDA GTK demo.
# Owner: Jiesui
# Last updated: July 2026

"""
Power benchmark panel for the PDA GTK demo.

The panel allows the user to select a CPU governor and workload,
configure the benchmark duration, and choose a CSV output filename.

The real benchmark runner is not connected yet. Until the power
measurement script interface is finalized, the Start Benchmark button
validates the selected settings and displays a placeholder status.
"""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


GOVERNOR_OPTIONS = (
    "schedutil",
    "ondemand",
    "powersave",
)

WORKLOAD_OPTIONS = (
    "Idle / Display Off",
    "Active / Display On",
    "Peripheral Active",
)

DEFAULT_DURATION_SECONDS = 60
MINIMUM_DURATION_SECONDS = 1
MAXIMUM_DURATION_SECONDS = 3600
DEFAULT_OUTPUT_FILENAME = "benchmark_idle.csv"


def create_left_aligned_label(text):
    """
    Create a reusable left-aligned label.
    """
    label = Gtk.Label(label=text)
    label.set_xalign(0)
    label.set_wrap(True)

    return label


def create_dropdown(options):
    """
    Create a drop-down containing the supplied text options.
    """
    option_model = Gtk.StringList.new(list(options))
    dropdown = Gtk.DropDown.new(option_model, None)
    dropdown.set_hexpand(True)
    dropdown.set_halign(Gtk.Align.FILL)

    return dropdown


def get_selected_dropdown_text(dropdown):
    """
    Return the currently selected text from a GTK drop-down.
    """
    selected_item = dropdown.get_selected_item()

    if selected_item is None:
        return ""

    return selected_item.get_string()


def normalize_output_filename(output_filename):
    """
    Normalize the output filename and ensure that it uses CSV format.
    """
    normalized_filename = output_filename.strip()

    if normalized_filename and not normalized_filename.lower().endswith(
        ".csv"
    ):
        normalized_filename = f"{normalized_filename}.csv"

    return normalized_filename


def validate_benchmark_settings(duration_seconds, output_filename):
    """
    Validate the user-provided benchmark settings.

    Raises:
        ValueError: If a setting cannot be used for a benchmark.
    """
    if duration_seconds < MINIMUM_DURATION_SECONDS:
        raise ValueError(
            "Duration must be at least "
            f"{MINIMUM_DURATION_SECONDS} second."
        )

    if duration_seconds > MAXIMUM_DURATION_SECONDS:
        raise ValueError(
            "Duration cannot exceed "
            f"{MAXIMUM_DURATION_SECONDS} seconds."
        )

    if not output_filename:
        raise ValueError("A CSV output filename is required.")

    if "/" in output_filename or "\\" in output_filename:
        raise ValueError(
            "Enter a filename only. Output folders are not supported yet."
        )


def on_start_benchmark_clicked(
    _button,
    governor_dropdown,
    workload_dropdown,
    duration_input,
    output_entry,
    status_label,
):
    """
    Validate the benchmark configuration and update placeholder status.
    """
    governor_name = get_selected_dropdown_text(governor_dropdown)
    workload_name = get_selected_dropdown_text(workload_dropdown)
    duration_seconds = duration_input.get_value_as_int()
    output_filename = normalize_output_filename(
        output_entry.get_text()
    )

    try:
        validate_benchmark_settings(
            duration_seconds,
            output_filename,
        )
    except ValueError as error:
        status_label.set_text(f"Status: Error — {error}")
        return

    output_entry.set_text(output_filename)

    status_label.set_text(
        "Status: Benchmark configuration is ready.\n"
        f"Governor: {governor_name}\n"
        f"Workload: {workload_name}\n"
        f"Duration: {duration_seconds} seconds\n"
        f"Output: {output_filename}\n"
        "The benchmark runner is not connected yet."
    )


def create_duration_input():
    """
    Create the benchmark duration input.
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
    Create the CSV output filename entry.
    """
    output_entry = Gtk.Entry()
    output_entry.set_text(DEFAULT_OUTPUT_FILENAME)
    output_entry.set_hexpand(True)
    output_entry.set_placeholder_text("benchmark_results.csv")

    return output_entry


def create_form_label(text):
    """
    Create a label used on the left side of a form row.
    """
    label = Gtk.Label(label=text)
    label.set_xalign(0)
    label.set_halign(Gtk.Align.START)
    label.set_valign(Gtk.Align.CENTER)

    return label


def create_benchmark_form(
    governor_dropdown,
    workload_dropdown,
    duration_input,
    output_entry,
):
    """
    Create the benchmark configuration form.
    """
    form_grid = Gtk.Grid()
    form_grid.set_column_spacing(12)
    form_grid.set_row_spacing(12)
    form_grid.set_hexpand(True)

    governor_label = create_form_label("Governor:")
    workload_label = create_form_label("Workload:")
    duration_label = create_form_label("Duration:")
    output_label = create_form_label("Save As:")

    duration_unit_label = create_form_label("seconds")

    form_grid.attach(governor_label, 0, 0, 1, 1)
    form_grid.attach(governor_dropdown, 1, 0, 2, 1)

    form_grid.attach(workload_label, 0, 1, 1, 1)
    form_grid.attach(workload_dropdown, 1, 1, 2, 1)

    form_grid.attach(duration_label, 0, 2, 1, 1)
    form_grid.attach(duration_input, 1, 2, 1, 1)
    form_grid.attach(duration_unit_label, 2, 2, 1, 1)

    form_grid.attach(output_label, 0, 3, 1, 1)
    form_grid.attach(output_entry, 1, 3, 2, 1)

    return form_grid


def create_start_button(
    governor_dropdown,
    workload_dropdown,
    duration_input,
    output_entry,
    status_label,
):
    """
    Create the button used to start a benchmark.
    """
    start_button = Gtk.Button(label="Start Benchmark")
    start_button.set_halign(Gtk.Align.CENTER)
    start_button.set_margin_top(8)

    start_button.connect(
        "clicked",
        on_start_benchmark_clicked,
        governor_dropdown,
        workload_dropdown,
        duration_input,
        output_entry,
        status_label,
    )

    return start_button


def create_power_benchmark_panel():
    """
    Create the complete power benchmark configuration panel.
    """
    panel_box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=16,
    )
    panel_box.set_hexpand(True)

    title_label = create_left_aligned_label("Power Benchmark")
    title_label.add_css_class("title-3")

    description_label = create_left_aligned_label(
        "Configure a repeatable power measurement test. Raw benchmark "
        "samples will eventually be written to the selected CSV file."
    )

    governor_dropdown = create_dropdown(GOVERNOR_OPTIONS)
    workload_dropdown = create_dropdown(WORKLOAD_OPTIONS)
    duration_input = create_duration_input()
    output_entry = create_output_entry()

    status_label = create_left_aligned_label("Status: Ready")
    status_label.set_selectable(True)

    benchmark_form = create_benchmark_form(
        governor_dropdown,
        workload_dropdown,
        duration_input,
        output_entry,
    )

    start_button = create_start_button(
        governor_dropdown,
        workload_dropdown,
        duration_input,
        output_entry,
        status_label,
    )

    panel_box.append(title_label)
    panel_box.append(description_label)
    panel_box.append(benchmark_form)
    panel_box.append(start_button)
    panel_box.append(Gtk.Separator())
    panel_box.append(status_label)

    return panel_box