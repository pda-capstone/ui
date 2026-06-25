# UI - Wayland Touch Stack

Touch-capable graphical interface for a portrait-orientation capacitive display.

## Goals

- Wayland compositor with correct touch input handling
- Smooth frame rate on portrait display
- Reference demo app showing basic touch interaction

## Tech Stack

- Wayland compositor: Weston
- UI framework: GTK4
- Language: Python with PyGObject
- Input stack: libinput
- Communication: D-Bus

## GTK Demo

The initial GTK demo is a minimal reference application used to verify that:

- a GTK4 application can run under Weston
- touch/click input reaches the application
- the layout can adapt to the available display size

## Dependencies on postmarketOS

```bash
doas apk add python3 py3-gobject3 gtk4.0 git
```

### macOS development

```bash
brew install pygobject3 gtk4
```
