# UI - Wayland Touch Stack

Touch-capable graphical interface for a portrait-orientation capacitive display.

## Goals

- Wayland compositor with correct touch input handling
- Smooth frame rate on portrait display
- Reference demo app showing basic touch interaction
- Expandable placeholder status display for future hot-swap daemon integration
- Diagnostics and power configuration UI that remains usable before the power scripts are connected
- Modular demo structure that separates UI panels, animation logic, settings storage, and future backend integration

## Tech Stack

- Wayland compositor: Phosh/Phoc
- UI framework: GTK4
- Language: Python with PyGObject
- Input stack: libinput
- Communication: D-Bus
- Persistent configuration: JSON in the user's XDG configuration directory

## GTK Demo

The GTK demo is a reference application used to verify that:

- a GTK4 application can run under the target Phosh/Phoc-based Wayland environment
- touch/click input reaches the application
- the layout can adapt to the available display size
- the demo can display temporary daemon/module status information
- the test button can count touch/click input events
- the test button can show simple visual click feedback
- the UI can display a lightweight FPS readout for responsiveness checks
- full-screen overlay panels can open, close, scroll, and receive input correctly
- power benchmark settings can be entered and validated before the real power scripts are connected
- a selected power mode can be saved and restored from a JSON configuration file

The demo is currently organized into separate files:

```text
demo.py
module_state.py
daemon_status_panel.py
click_test_panel.py
click_effects.py
fps_display.py
diagnostics_overlay.py
power_benchmark_panel.py
settings_overlay.py
settings_store.py
power_backend.py
```

### File Structure

- `demo.py` is the main application entry point. It creates the GTK application window and combines the UI panels.
- `module_state.py` stores temporary daemon/module demo state and helper functions for generating status text.
- `daemon_status_panel.py` creates the expandable daemon/module status panel.
- `click_test_panel.py` creates the touch/click test panel, maintains click counter state, and coordinates click effects with the FPS display.
- `click_effects.py` owns the lightweight ripple and dot animation logic used after button clicks.
- `fps_display.py` owns the FPS label and frame-rate calculation helpers.
- `diagnostics_overlay.py` adds the full-screen diagnostics and settings overlays and places their launch controls over the main demo content.
- `power_benchmark_panel.py` builds the benchmark configuration form, validates governor, workload, duration, and CSV filename values, and submits a `BenchmarkRequest` when a power backend is available.
- `settings_overlay.py` builds the power mode settings panel and restores or saves the selected application-level power mode.
- `settings_store.py` validates and atomically stores persistent settings as JSON in the user's XDG configuration directory.
- `power_backend.py` defines the optional interface between the GTK UI and future power scripts or a system service. Its default implementation reports that power integration is unavailable.

The module state data is currently static placeholder data. Later, this can be replaced or extended with real data from the hot-swap daemon through D-Bus.

## Click Effect and FPS Display

Clicking the test button increments the click counter and starts a simple visual feedback animation.

The click effect includes:

- one expanding ripple ring
- a small ring of lightweight dots
- no heavy particle system

The FPS label is shown in the lower-left corner of the click test area. It is calculated from GTK frame-clock ticks and is intended as a lightweight responsiveness indicator, not a formal benchmark.

## Diagnostics and Power Benchmark Panel

The `Diagnostics` button opens a full-screen overlay containing the power benchmark configuration panel.

The panel currently supports:

- CPU governor selection
- workload selection
- benchmark duration from 1 to 3600 seconds
- CSV output filename validation
- conversion of the form values into a `BenchmarkRequest`

The available prototype workloads are:

- `idle` — idle system or display-off testing
- `display` — active system with the display on
- `peripheral` — testing with an attached or active peripheral

The default `PowerBackend` is intentionally unavailable. In this mode, the panel validates and displays the selected configuration but does not run a benchmark or create a CSV file.

A future backend can connect `BenchmarkRequest` values to the power team's scripts, a subprocess runner, or a system service without moving power-specific execution logic into the GTK panel. A real backend must launch work asynchronously and return without blocking the GTK main thread.

## Power Mode Settings

The settings button opens a full-screen power mode panel with these application-level modes:

- `default` — `schedutil`
- `low_power` — `powersave`
- `performance` — `performance`

Selecting `Save Settings` stores the chosen mode in:

```text
$XDG_CONFIG_HOME/pda-demo/settings.json
```

If `XDG_CONFIG_HOME` is not set, the default location is:

```text
~/.config/pda-demo/settings.json
```

Example configuration:

```json
{
  "version": 1,
  "power_mode": "default"
}
```

The settings file records the user's selected mode, but the current demo does not change the operating system governor. Applying the mode remains the responsibility of a future power backend or power controller.

## Dependencies on postmarketOS

```bash
doas apk add python3 py3-gobject3 gtk4.0 py3-cairo git
```

### macOS Development

```bash
brew install pygobject3 gtk4
```

## Run

Place the Python files in the same directory, then run:

```bash
python3 demo.py
```

## Manual Test Checklist

After launching the demo:

1. Confirm the window opens and shows `Pocket Distro Alpha`.
2. Click the daemon/module status bar and confirm the detail panel expands and collapses.
3. Click the `Test Touch / Click` button.
4. Confirm the click counter increases.
5. Confirm a simple ripple and dot effect appears after each click.
6. Confirm the lower-left FPS label updates while the app is running.
7. Click `Diagnostics` and confirm the full-screen diagnostics overlay opens.
8. Change the governor, workload, duration, or CSV filename and confirm invalid values produce a visible error.
9. With the default unavailable backend, confirm a valid benchmark configuration is displayed without starting a benchmark.
10. Close the diagnostics overlay and confirm the main page receives input again.
11. Open the power mode settings panel.
12. Select a power mode, save it, close the panel, and reopen it.
13. Confirm the saved power mode is restored from the JSON configuration file.
14. Confirm the settings status explains that the operating system governor was not changed.

## Performance Notes

The FPS display reports the GTK frame-clock tick rate observed by the demo app. It is useful for quick visual checks during VM and hardware testing, but it does not measure full end-to-end display latency.

Known limitations:

- VM results may not match physical touchscreen hardware.
- Mouse clicks in a VM are only a temporary substitute for real touch input.
- The daemon status panel still uses placeholder data.
- The default power backend does not run power scripts.
- Saving a power mode does not currently apply a CPU governor.
- A validated benchmark configuration does not create a CSV file until a real backend is connected.
- Final validation should be repeated on the target display, compositor setup, and power measurement hardware.
