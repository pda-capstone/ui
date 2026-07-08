# UI - Wayland Touch Stack

Touch-capable graphical interface for a portrait-orientation capacitive display.

## Goals

- Wayland compositor with correct touch input handling
- Smooth frame rate on portrait display
- Reference demo app showing basic touch interaction
- Modular demo structure that separates status display, input testing, click effects, FPS display, and application startup logic

## Tech Stack

- Wayland compositor: Phosh/Phoc
- UI framework: GTK4
- Language: Python with PyGObject
- Input stack: libinput
- Communication: D-Bus

## GTK Demo

The GTK demo is a reference application used to verify that:

- a GTK4 application can run under the target Phosh/Phoc-based Wayland environment
- touch/click input reaches the application
- the layout can adapt to the available display size
- the demo can display temporary daemon/module status information
- the test button can count touch/click input events
- the test button can show simple visual click feedback
- the UI can display a lightweight FPS readout for responsiveness checks

The demo is currently organized into separate files:

```text
demo.py
module_state.py
daemon_status_panel.py
click_test_panel.py
click_effects.py
fps_display.py
```

### File Structure

- `demo.py` is the main application entry point. It creates the GTK application window and combines the UI panels.
- `module_state.py` stores temporary daemon/module demo state and helper functions for generating status text.
- `daemon_status_panel.py` creates the expandable daemon/module status panel.
- `click_test_panel.py` creates the touch/click test panel, maintains click counter state, and coordinates click effects with the FPS display.
- `click_effects.py` owns the lightweight ripple and dot animation logic used after button clicks.
- `fps_display.py` owns the FPS label and frame-rate calculation helpers.

The module state data is currently static placeholder data. Later, this can be replaced or extended with real data from the hot-swap daemon through D-Bus.

## Click Effect and FPS Display

Clicking the test button increments the click counter and starts a simple visual feedback animation.

The click effect includes:

- one expanding ripple ring
- a small ring of lightweight dots
- no heavy particle system

The FPS label is shown in the lower-left corner of the click test area. It is calculated from GTK frame-clock ticks and is intended as a lightweight responsiveness indicator, not a formal benchmark.

## Dependencies on postmarketOS

```bash
doas apk add python3 py3-gobject3 gtk4.0 git
```

### macOS development

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

## Performance Notes

The FPS display reports the GTK frame-clock tick rate observed by the demo app. It is useful for quick visual checks during VM and hardware testing, but it does not measure full end-to-end display latency.

Known limitations:

- VM results may not match physical touchscreen hardware.
- Mouse clicks in a VM are only a temporary substitute for real touch input.
- Final validation should be repeated on the target display and compositor setup.
