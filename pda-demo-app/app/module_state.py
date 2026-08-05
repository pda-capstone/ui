# module_state.py
# Stores temporary demo module state and builds PDA status text.
# Owner: Jiesui
# Last updated: June 2026

import os
import time
import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

"""
PDA module state helpers.

This file stores demo data and helper functions for generating
module-related status text. It also connects to the hot-swap daemon
via D-Bus to keep accessory state updated live.
"""

DBUS_BUS_NAME = "org.postmarketos.HotSwap"
DBUS_OBJECT_PATH = "/org/postmarketos/HotSwap"
DBUS_INTERFACE = "org.postmarketos.HotSwap"

DAEMON_STATUS = "Connecting to hot-swap daemon..."
MODULES = []

_CONNECTED_TO_DAEMON = False
_LAST_UPDATE_TIME = time.time()
_STATE_CHANGE_CALLBACKS = []
_PROXY = None
_CONNECTION = None
_SUBSCRIPTIONS = []
_NAME_OWNER_SUBSCRIPTION = None


def _notify_state_change():
    global _LAST_UPDATE_TIME
    _LAST_UPDATE_TIME = time.time()
    for callback in list(_STATE_CHANGE_CALLBACKS):
        callback()


def register_state_change_callback(callback):
    """Register a UI callback to run when module state changes."""
    if callback not in _STATE_CHANGE_CALLBACKS:
        _STATE_CHANGE_CALLBACKS.append(callback)


def _set_daemon_status(connected):
    global DAEMON_STATUS, _CONNECTED_TO_DAEMON
    _CONNECTED_TO_DAEMON = bool(connected)
    DAEMON_STATUS = "Connected" if _CONNECTED_TO_DAEMON else "Unavailable"


def _variant_child_count(variant):
    if variant is None:
        return 0
    try:
        return variant.n_children()
    except TypeError:
        return int(variant.n_children)


def _find_bus_address_file():
    for path in ["/tmp/hotswap_bus_address", "/tmp/hotswap_dbus_address"]:
        try:
            with open(path, "r") as handle:
                address = handle.read().strip()
            if address:
                return address
        except OSError:
            continue
    return None


def get_connected_module_count():
    """Count connected modules from the current module state list."""
    return sum(
        1 for module in MODULES
        if module.get("state") == "connected"
    )


def get_status_bar_text(expanded=False):
    """Build the top status bar text from current module state."""
    connected_count = get_connected_module_count()
    total_count = len(MODULES)
    arrow = "▲" if expanded else "▼"

    if not _CONNECTED_TO_DAEMON:
        module_text = "Hot-swap daemon unavailable"
    elif total_count == 0:
        module_text = "No accessories connected"
    elif connected_count == 1:
        module_text = "1 accessory connected"
    else:
        module_text = f"{connected_count} accessories connected"

    return f"{module_text} {arrow}"


def _module_from_variant(variant):
    """Convert a D-Bus module tuple variant to a local module dict."""
    if variant is None or _variant_child_count(variant) < 5:
        return None

    devpath = variant.get_child_value(0).get_string()
    name = variant.get_child_value(1).get_string()
    category = variant.get_child_value(2).get_string()
    state = variant.get_child_value(3).get_string()
    power = variant.get_child_value(4).get_uint32()

    return {
        "devpath": devpath,
        "name": name,
        "role": category,
        "state": state,
        "power": power
    }


def _parse_list_modules_reply(reply):
    """Extract a list of module dicts from a ListModules reply variant."""
    if reply is None:
        return []

    type_string = reply.get_type_string()
    if type_string.startswith("(") and _variant_child_count(reply) == 1:
        reply = reply.get_child_value(0)

    result = []
    for i in range(_variant_child_count(reply)):
        item = reply.get_child_value(i)
        module = _module_from_variant(item)
        if module:
            result.append(module)

    return result


def _add_or_update_module(module):
    """Add or update a module record by devpath."""
    if module is None:
        return

    for index, existing in enumerate(MODULES):
        if existing.get("devpath") == module.get("devpath"):
            MODULES[index] = module
            return

    MODULES.append(module)


def _remove_module(devpath):
    """Remove a module from the current list by devpath."""
    global MODULES
    MODULES = [m for m in MODULES if m.get("devpath") != devpath]


def _on_daemon_signal(connection, sender_name, object_path, interface_name,
                      signal_name, parameters, user_data):
    if signal_name == "ModuleAttached":
        if parameters is not None and _variant_child_count(parameters) >= 7:
            module = {
                "devpath": parameters.get_child_value(0).get_string(),
                "name": parameters.get_child_value(3).get_string(),
                "role": parameters.get_child_value(4).get_string(),
                "state": "connected",
                "power": parameters.get_child_value(5).get_uint32()
            }
            _add_or_update_module(module)
            _set_daemon_status(True)
            _notify_state_change()
    elif signal_name == "ModuleDetached":
        if parameters is not None and _variant_child_count(parameters) >= 1:
            devpath = parameters.get_child_value(0).get_string()
            _remove_module(devpath)
            _set_daemon_status(True)
            _notify_state_change()
    elif signal_name == "PowerChanged":
        if parameters is not None and _variant_child_count(parameters) >= 2:
            _set_daemon_status(True)
            _notify_state_change()

    return True


def _connect_signal(interface_name, member):
    if _CONNECTION is None:
        return

    subscription_id = _CONNECTION.signal_subscribe(
        None,
        DBUS_INTERFACE,
        member,
        DBUS_OBJECT_PATH,
        None,
        Gio.DBusSignalFlags.NONE,
        _on_daemon_signal,
        None
    )
    _SUBSCRIPTIONS.append(subscription_id)


def _on_name_owner_changed(connection, sender_name, object_path, interface_name,
                           signal_name, parameters, user_data):
    if parameters is None or signal_name != "NameOwnerChanged" or _variant_child_count(parameters) != 3:
        return True

    name = parameters.get_child_value(0).get_string()
    if name != DBUS_BUS_NAME:
        return True

    old_owner = parameters.get_child_value(1).get_string()
    new_owner = parameters.get_child_value(2).get_string()

    if new_owner == "":
        MODULES.clear()
        _set_daemon_status(False)
        _notify_state_change()
    elif old_owner == "":
        refresh_module_list()

    return True


def _connect_name_owner_watch():
    global _NAME_OWNER_SUBSCRIPTION
    if _CONNECTION is None:
        return

    _NAME_OWNER_SUBSCRIPTION = _CONNECTION.signal_subscribe(
        None,
        "org.freedesktop.DBus",
        "NameOwnerChanged",
        "/org/freedesktop/DBus",
        None,
        Gio.DBusSignalFlags.NONE,
        _on_name_owner_changed,
        None
    )


def _clear_subscriptions():
    global _SUBSCRIPTIONS, _NAME_OWNER_SUBSCRIPTION
    if _CONNECTION is None:
        return

    for subscription_id in _SUBSCRIPTIONS:
        _CONNECTION.signal_unsubscribe(subscription_id)
    _SUBSCRIPTIONS = []

    if _NAME_OWNER_SUBSCRIPTION is not None:
        _CONNECTION.signal_unsubscribe(_NAME_OWNER_SUBSCRIPTION)
        _NAME_OWNER_SUBSCRIPTION = None


def _schedule_periodic_refresh():
    if _PROXY is None:
        return False
    refresh_module_list()
    return True


def refresh_module_list():
    """Query the daemon for the currently attached modules."""
    global MODULES
    if _PROXY is None:
        return

    try:
        reply = _PROXY.call_sync(
            "ListModules",
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None
        )
        new_modules = _parse_list_modules_reply(reply)
        if new_modules:
            MODULES = new_modules
        else:
            MODULES = []
        _set_daemon_status(True)
        _notify_state_change()
    except Exception as exc:
        print("hot-swap daemon ListModules call failed:", exc)
        _set_daemon_status(False)
        _notify_state_change()


def connect_to_daemon():
    """Connect to the hot-swap daemon over D-Bus and subscribe to signals."""
    global _PROXY, _CONNECTION
    try:
        bus_address = os.environ.get('DBUS_SYSTEM_BUS_ADDRESS') or _find_bus_address_file()
        if bus_address:
            connection = Gio.DBusConnection.new_for_address_sync(
                bus_address,
                Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,
                None,
            )
            _PROXY = Gio.DBusProxy.new_sync(
                connection,
                Gio.DBusProxyFlags.NONE,
                None,
                DBUS_BUS_NAME,
                DBUS_OBJECT_PATH,
                DBUS_INTERFACE,
                None,
            )
            _CONNECTION = connection
        else:
            _PROXY = Gio.DBusProxy.new_for_bus_sync(
                Gio.BusType.SYSTEM,
                Gio.DBusProxyFlags.NONE,
                None,
                DBUS_BUS_NAME,
                DBUS_OBJECT_PATH,
                DBUS_INTERFACE,
                None,
            )
            _CONNECTION = _PROXY.get_connection()
    except Exception as exc:
        print("hot-swap daemon D-Bus proxy failed:", exc)
        _set_daemon_status(False)
        _notify_state_change()
        return False

    _connect_signal(DBUS_INTERFACE, "ModuleAttached")
    _connect_signal(DBUS_INTERFACE, "ModuleDetached")
    _connect_signal(DBUS_INTERFACE, "PowerChanged")
    _connect_name_owner_watch()
    refresh_module_list()
    GLib.timeout_add_seconds(5, _schedule_periodic_refresh)
    return True


def get_module_detail_lines():
    """
    Build text lines for the expanded module status panel.
    """
    lines = [f"Hot-swap daemon: {DAEMON_STATUS}"]

    if MODULES:
        lines.append(f"Accessories connected: {get_connected_module_count()}")
        for module in MODULES:
            module_name = module.get("name") or "Unknown accessory"
            module_role = module.get("role") or "Unknown type"
            module_state = module.get("state", "unknown")
            power = module.get("power")
            power_text = f" · {power} mA" if isinstance(power, int) and power > 0 else ""
            lines.append(
                f"{module_name}: {module_state} · {module_role}{power_text}"
            )
    else:
        lines.append("Accessories: none detected")

    lines.append(
        f"Last update: {time.strftime('%H:%M:%S', time.localtime(_LAST_UPDATE_TIME))}"
    )

    return lines
