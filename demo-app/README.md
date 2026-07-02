# UI - Wayland Touch Stack

Touch-capable graphical interface for a portrait-orientation capacitive display.

## Goals

- Wayland compositor with correct touch input handling
- Smooth frame rate on portrait display
- Reference demo app showing basic touch interaction
- Modular demo structure that separates status display, input testing, and application startup logic

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

The demo is currently organized into separate files:

```text
demo.py
module_state.py
daemon_status_panel.py
click_test_panel.py
```

### File Structure

- `demo.py` is the main application entry point. It creates the GTK application window and combines the UI panels.
- `module_state.py` stores temporary daemon/module demo state and helper functions for generating status text.
- `daemon_status_panel.py` creates the expandable daemon/module status panel.
- `click_test_panel.py` creates the touch/click test panel and maintains the click counter state.

The module state data is currently static placeholder data. Later, this can be replaced or extended with real data from the hot-swap daemon through D-Bus.

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
