# UI - Wayland Touch Stack

Touch-capable GTK4 reference interface for Pocket Distro Alpha. The demo is
designed for a portrait-oriented display and is used to validate Wayland input,
GTK responsiveness, daemon-status presentation, CPU governor settings, and
power benchmark integration.

## Goals

- Run a GTK4 application under the PDA Wayland environment.
- Verify touch and click input with visible feedback.
- Provide a lightweight FPS indicator for responsiveness checks.
- Display expandable placeholder module status before D-Bus integration is
  complete.
- Save and apply application-level CPU power modes when CPUfreq support is
  available.
- Run INA219 power measurements asynchronously without blocking the GTK main
  loop.
- Provide clearly labeled simulated benchmark data on development systems.

## Tech Stack

- Wayland environment: Phosh/Phoc
- UI framework: GTK4
- Language: Python with PyGObject
- Input stack: libinput
- Planned daemon communication: D-Bus
- Persistent configuration: JSON in the user's XDG configuration directory
- Power control: Linux CPUfreq governors through an optional `governors` module
- Power measurement: INA219 sampling script or simulated development data

## Current Demo Features

The reference application currently includes:

- an expandable daemon/module status panel using placeholder state
- a large touch/click test button with a click counter
- ripple and dot click-feedback animations
- a lightweight FPS label based on GTK frame-clock ticks
- a full-screen diagnostics overlay
- a power benchmark configuration and execution panel
- a full-screen power mode settings overlay
- persistent JSON settings
- one shared `PowerBackend` facade for settings and benchmark operations

## Project Structure

```text
app/
├── __init__.py
├── module_state.py
├── daemon_status_panel.py
├── click_test_panel.py
├── click_effects.py
├── fps_display.py
├── diagnostics_overlay.py
├── power_modes.py
├── governor_controller.py
├── power_benchmark_runner.py
├── power_benchmark_panel.py
├── power_backend.py
├── settings_store.py
└── settings_overlay.py
```

### Main Modules

- `app/__init__.py` creates the GTK application window and connects the UI
  components.
- `module_state.py` stores temporary daemon/module state and formats status
  text.
- `daemon_status_panel.py` creates the expandable module status panel.
- `click_test_panel.py` manages the click counter and coordinates click effects
  with the FPS display.
- `click_effects.py` contains the lightweight ripple and dot animation logic.
- `fps_display.py` calculates and displays the GTK frame-clock tick rate.
- `diagnostics_overlay.py` creates the diagnostics and settings overlays.
- `power_modes.py` defines the shared application power modes and governor
  mappings.
- `governor_controller.py` loads the optional governor implementation lazily,
  validates available governors, applies a governor, and verifies the result.
- `power_benchmark_runner.py` runs one benchmark at a time on a background
  thread, writes CSV output, and restores the previous governor.
- `power_benchmark_panel.py` validates benchmark form values and submits a
  `BenchmarkRequest` through `PowerBackend`.
- `power_backend.py` provides the single UI-facing service used by both power
  settings and benchmarks.
- `settings_store.py` validates and atomically saves persistent JSON settings.
- `settings_overlay.py` restores, saves, and attempts to apply the selected
  power mode.

The module status data is still static. It can later be replaced with data from
the hot-swap daemon through D-Bus without changing the main panel layout.

## Power Architecture

The GTK layer uses one `PowerBackend` instance. Internally, it delegates:

- CPUfreq operations to `GovernorController`
- benchmark lifecycle and background work to `PowerBenchmarkRunner`

This keeps GTK widgets independent from Linux CPUfreq and subprocess details.
It also ensures that power settings and benchmarks share the same governor
controller and benchmark-running state.

While a benchmark is active, the settings panel prevents the user from changing
the power mode. The benchmark runner records the original governor and attempts
to restore it after the measurement finishes or fails.

## Power Mode Settings

The settings button opens a full-screen power mode panel with these shared
application-level modes:

| Mode ID       | Display name | Governor      |
| ------------- | ------------ | ------------- |
| `default`     | Default      | `schedutil`   |
| `low_power`   | Low Power    | `powersave`   |
| `performance` | Performance  | `performance` |

Selecting **Save and Apply** first saves the selected mode and then attempts to
apply the mapped governor.

Settings are stored in:

```text
$XDG_CONFIG_HOME/pda-demo/settings.json
```

When `XDG_CONFIG_HOME` is not set, the default location is:

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

The saved mode is loaded and applied when the settings controls are created.
If CPUfreq support or the required permissions are unavailable, the application
continues to run and reports the error in the settings panel. Saving the JSON
configuration remains available on development systems such as macOS.

### Governor Integration Requirements

The optional low-level Python module is named `governors` by default. It must
provide these functions:

```python
available_governors()
get_current_governor()
set_governor(governor)
```

Governor changes normally require Linux CPUfreq support and sufficient system
permissions. The UI does not attempt to bypass operating-system permission
requirements.

## Diagnostics and Power Benchmark

The **Diagnostics** button opens the benchmark panel. The panel supports:

- governor selection from the shared power mode definitions
- workload label selection
- duration from 1 to 3600 seconds
- CSV filename validation
- asynchronous benchmark execution
- visible progress, result, and error messages

The available workload labels are:

- `idle` - idle system or display-off condition
- `display` - active system with the display on
- `peripheral` - attached or active peripheral condition

The current UI records the selected workload as benchmark metadata. It does not
automatically turn the display on or off, create system load, or activate a
peripheral. Prepare the selected workload condition manually before starting a
live measurement.

### Live INA219 Mode

The runner searches for the sampling script in the expected sibling-repository
layout:

```text
power/hardware/ina219/ina219_sample.py
```

The path can be overridden with:

```bash
export PDA_INA219_SCRIPT=/absolute/path/to/ina219_sample.py
```

The script is launched with:

```text
--seconds <duration> --out <csv-path>
```

The produced CSV must contain these columns:

```text
voltage_V,current_mA,power_mW
```

For live measurements, governor setup must succeed. The runner will not silently
record INA219 data under an unknown governor.

### Simulated Development Mode

When the INA219 script is not available, the default runner creates clearly
labeled simulated development data. This allows the UI, background thread,
status callbacks, CSV generation, and governor error paths to be tested without
the target hardware.

Simulated values are not valid power measurements and must not be used in the
baseline or optimized power reports.

### CSV Output Location

The benchmark panel currently accepts a filename only. The CSV file is saved
relative to the directory from which the application was launched.

For example, starting the app from `pda-demo-app/` with the default filename
creates:

```text
pda-demo-app/benchmark_idle.csv
```

## Dependencies

### postmarketOS / Alpine Linux

```bash
doas apk add python3 py3-gobject3 gtk4.0 py3-cairo git
```

The final packaged application should also include the project package, the
optional governor implementation, and the power sampling script when live power
features are required.

### macOS Development

```bash
brew install pygobject3 gtk4 uv
```

PyGObject installed by Homebrew is a system Python package. When using a virtual
environment, ensure that the environment can access system site packages.

One development setup is:

```bash
uv venv --system-site-packages
uv pip install -e .
uv run --no-sync pda-demo-app
```

## Run

From the `pda-demo-app` directory, development environments with `uv` can run:

```bash
uv run pda-demo-app
```

After the project package is installed, use its console entry point:

```bash
pda-demo-app
```

The console entry point is configured as:

```toml
pda-demo-app = "app:main"
```

in `pyproject.toml`.

The command name is `pda-demo-app`, while `app:main` refers to the Python
package and function used internally as the application entry point.

## Manual Test Checklist

### Main UI

1. Launch the application and confirm the window shows `Pocket Distro Alpha`.
2. Expand and collapse the daemon/module status panel.
3. Click **Test Touch / Click** and confirm the counter increases.
4. Confirm the ripple and dot feedback appears.
5. Confirm the lower-left FPS label updates.

### Diagnostics and Benchmark

1. Open **Diagnostics** and confirm the overlay receives input.
2. Test invalid duration or filename values and confirm an error is displayed.
3. Start a short benchmark.
4. Confirm the GTK window remains responsive while the worker runs.
5. Confirm the status identifies INA219 or simulated development data.
6. Confirm a CSV file is created in the launch directory.
7. Start another benchmark while one is active and confirm it is rejected.
8. Confirm the previous governor is restored when governor control is
   available.

### Power Mode Settings

1. Open the power mode settings overlay.
2. Select a mode and press **Save and Apply**.
3. Close and reopen the panel and confirm the saved selection is restored.
4. Restart the application and confirm it attempts to apply the saved mode.
5. Confirm governor or permission failures are shown without crashing the app.
6. While a benchmark is running, confirm power mode changes are blocked.

## Performance Notes

The FPS label reports the GTK frame-clock tick rate observed by the demo. It is
useful for quick responsiveness checks, but it is not a formal frame-rate,
latency, or end-to-end touch benchmark.

## Known Limitations

- The daemon/module panel still uses placeholder data and is not yet connected
  to the hot-swap daemon through D-Bus.
- VM mouse input is only a substitute for physical touchscreen testing.
- Portrait display rotation and touch-coordinate alignment require final target
  hardware validation.
- Workload conditions are prepared manually; the benchmark runner only records
  the selected workload label.
- Simulated benchmark output is development-only and is not measurement data.
- Live INA219 execution depends on the external sampling script, hardware
  connection, and permissions.
- CPU governor control depends on Linux CPUfreq support, the external
  `governors` implementation, and permissions.
- Benchmark CSV files are currently saved relative to the process working
  directory.
- Final validation must be repeated on the CM5, target display, compositor,
  touchscreen, and power measurement hardware.
