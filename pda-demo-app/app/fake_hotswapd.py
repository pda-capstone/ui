#!/usr/bin/env python3
# fake_hotswapd.py
# This is a standalone script that can be run to simulate the HotSwap daemon.
# Owner: Griffin
# Last updated: July 2026

import os
import sys
import socket
import threading
import time
import gi

gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib

DBUS_BUS_NAME = 'org.postmarketos.HotSwap'
DBUS_OBJECT_PATH = '/org/postmarketos/HotSwap'
DBUS_INTERFACE = 'org.postmarketos.HotSwap'

# Fake test device properties. The daemon starts with no attached device.
FAKE_DEVICE = {
    'devpath': '/sys/devices/test/test_device0',
    'vendor_id': '1234',
    'product_id': '5678',
    'name': 'test_flashdrive',
    'category': 'storage',
    'state': 'connected',
    'power': 500,
    'speed': 480,
    'attached': False,
}

BUS_ADDRESS_ENV = 'DBUS_SYSTEM_BUS_ADDRESS'
BUS_ADDRESS_FILE = '/tmp/hotswap_bus_address'
CONTROL_SOCKET = os.environ.get('FAKE_HOTSWAPD_CONTROL_SOCKET', '/tmp/fake_hotswapd-control.sock')
control_running = True

introspection_xml = f'''
<node>
  <interface name="{DBUS_INTERFACE}">
    <method name="ListModules">
      <arg direction="out" type="a(ssssu)"/>
    </method>
    <method name="GetModuleInfo">
      <arg direction="in" type="s" name="devpath"/>
      <arg direction="out" type="a{{sv}}"/>
    </method>
    <method name="GetTotalPowerDraw">
      <arg direction="out" type="u"/>
    </method>
    <signal name="ModuleAttached">
      <arg type="s"/>
      <arg type="s"/>
      <arg type="s"/>
      <arg type="s"/>
      <arg type="s"/>
      <arg type="u"/>
      <arg type="u"/>
    </signal>
    <signal name="ModuleDetached">
      <arg type="s"/>
      <arg type="s"/>
      <arg type="b"/>
    </signal>
    <signal name="PowerChanged">
      <arg type="u"/>
      <arg type="u"/>
    </signal>
  </interface>
</node>
'''

loop = None
connection = None
name_owner_id = None
hotswap_obj = None


def write_bus_address(bus_address):
    try:
        with open(BUS_ADDRESS_FILE, 'w') as handle:
            handle.write(bus_address)
    except OSError:
        pass


def _stop_main_loop():
    global loop, control_running
    control_running = False
    if loop is not None:
        loop.quit()
    return False


def _control_command(command):
    command = command.strip()
    if not command:
        return 'ok\n'

    parts = command.split()
    cmd = parts[0].lower()

    if hotswap_obj is None:
        return 'daemon not ready\n'

    if cmd == 'attach':
        if FAKE_DEVICE['attached']:
            return 'already attached\n'
        FAKE_DEVICE['attached'] = True
        print('fake device attached')
        hotswap_obj.emit_module_attached()
        hotswap_obj.emit_power_changed()
        return 'attached\n'

    if cmd == 'detach':
        if not FAKE_DEVICE['attached']:
            return 'already detached\n'
        FAKE_DEVICE['attached'] = False
        print('fake device detached')
        hotswap_obj.emit_module_detached()
        hotswap_obj.emit_power_changed()
        return 'detached\n'

    if cmd == 'power' and len(parts) == 2:
        try:
            power = int(parts[1])
        except ValueError:
            return 'invalid power\n'
        FAKE_DEVICE['power'] = power
        if FAKE_DEVICE['attached']:
            print(f'fake device power changed to {power}')
            hotswap_obj.emit_power_changed()
        return f'power set to {power}\n'

    if cmd == 'status':
        state = 'attached' if FAKE_DEVICE['attached'] else 'detached'
        return f'{state}\n'

    if cmd == 'help':
        return 'commands: attach, detach, power <mA>, status, quit\n'

    if cmd == 'quit':
        GLib.idle_add(_stop_main_loop)
        return 'quitting\n'

    return 'unknown command\n'


def _serve_control_socket():
    if os.path.exists(CONTROL_SOCKET):
        try:
            os.unlink(CONTROL_SOCKET)
        except OSError:
            pass

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(CONTROL_SOCKET)
    server.listen(1)
    print(f'Fake HotSwap control socket listening on {CONTROL_SOCKET}')
    server.settimeout(1.0)

    while control_running:
        try:
            client, _ = server.accept()
        except socket.timeout:
            continue
        except OSError:
            break

        with client:
            data = client.recv(1024).decode('utf-8')
            if not data:
                continue
            command = data.strip()
            result = {'value': None}

            def handle():
                result['value'] = _control_command(command)
                return False

            GLib.idle_add(handle)
            while result['value'] is None:
                time.sleep(0.01)

            client.sendall(result['value'].encode('utf-8'))

    server.close()
    try:
        os.unlink(CONTROL_SOCKET)
    except OSError:
        pass


def _register_hotswap_object(conn):
    global hotswap_obj
    hotswap_obj = HotswapObject(conn)
    conn.register_object(
        DBUS_OBJECT_PATH,
        hotswap_obj.interface_info,
        hotswap_obj.handle_method_call,
        None,
        None,
    )
    print(f'Fake HotSwap daemon registered on {DBUS_BUS_NAME}')


def on_name_acquired(connection, name):
    print(f'Bus name acquired: {name}')


def on_name_lost(connection, name):
    print(f'Failed to acquire bus name: {name}')
    if loop is not None:
        loop.quit()


class HotswapObject:
    def __init__(self, connection):
        self.connection = connection
        self.node_info = Gio.DBusNodeInfo.new_for_xml(introspection_xml)
        self.interface_info = self.node_info.lookup_interface(DBUS_INTERFACE)

    def handle_method_call(self, connection, sender, object_path, interface_name,
                           method_name, parameters, invocation):
        if method_name == 'ListModules':
            self.handle_list_modules(invocation)
        elif method_name == 'GetModuleInfo':
            self.handle_get_module_info(invocation, parameters)
        elif method_name == 'GetTotalPowerDraw':
            self.handle_get_total_power_draw(invocation)
        else:
            invocation.return_dbus_error('org.freedesktop.DBus.Error.UnknownMethod',
                                         f'Unknown method: {method_name}')

    def handle_list_modules(self, invocation):
        if not FAKE_DEVICE['attached']:
            result = GLib.Variant('(a(ssssu))', ([],))
            invocation.return_value(result)
            return

        module = GLib.Variant('(ssssu)', (
            FAKE_DEVICE['devpath'],
            FAKE_DEVICE['name'],
            FAKE_DEVICE['category'],
            FAKE_DEVICE['state'],
            FAKE_DEVICE['power'],
        ))
        result = GLib.Variant('(a(ssssu))', ([module],))
        invocation.return_value(result)

    def handle_get_module_info(self, invocation, parameters):
        if parameters is None or parameters.get_n_children() < 1:
            invocation.return_dbus_error('org.freedesktop.DBus.Error.InvalidArgs',
                                         'Expected devpath string')
            return

        devpath = parameters.get_child_value(0).get_string()
        if devpath != FAKE_DEVICE['devpath'] or not FAKE_DEVICE['attached']:
            invocation.return_dbus_error('org.freedesktop.DBus.Error.InvalidArgs',
                                         'Device not found')
            return

        props = {
            'devpath': GLib.Variant('s', FAKE_DEVICE['devpath']),
            'syspath': GLib.Variant('s', '/sys/devices/test/test_device0'),
            'vendor_id': GLib.Variant('s', FAKE_DEVICE['vendor_id']),
            'product_id': GLib.Variant('s', FAKE_DEVICE['product_id']),
            'vendor_name': GLib.Variant('s', 'TestVendor'),
            'product_name': GLib.Variant('s', FAKE_DEVICE['name']),
            'serial': GLib.Variant('s', 'TEST123'),
            'category': GLib.Variant('s', FAKE_DEVICE['category']),
            'state': GLib.Variant('s', FAKE_DEVICE['state']),
            'max_power_ma': GLib.Variant('u', FAKE_DEVICE['power']),
            'speed_mbps': GLib.Variant('u', FAKE_DEVICE['speed']),
            'self_powered': GLib.Variant('b', False),
            'has_pd': GLib.Variant('b', False),
            'mount_count': GLib.Variant('u', 0),
        }
        result = GLib.Variant('(a{sv})', (props,))
        invocation.return_value(result)

    def handle_get_total_power_draw(self, invocation):
        total_draw = FAKE_DEVICE['power'] if FAKE_DEVICE['attached'] else 0
        result = GLib.Variant('(u)', (total_draw,))
        invocation.return_value(result)

    def emit_module_attached(self):
        self.connection.emit_signal(
            None,
            DBUS_OBJECT_PATH,
            DBUS_INTERFACE,
            'ModuleAttached',
            GLib.Variant('(sssssuu)', (
                FAKE_DEVICE['devpath'],
                FAKE_DEVICE['vendor_id'],
                FAKE_DEVICE['product_id'],
                FAKE_DEVICE['name'],
                FAKE_DEVICE['category'],
                FAKE_DEVICE['power'],
                FAKE_DEVICE['speed'],
            ))
        )

    def emit_module_detached(self):
        self.connection.emit_signal(
            None,
            DBUS_OBJECT_PATH,
            DBUS_INTERFACE,
            'ModuleDetached',
            GLib.Variant('(ssb)', (
                FAKE_DEVICE['devpath'],
                FAKE_DEVICE['name'],
                False,
            ))
        )

    def emit_power_changed(self):
        device_count = 1 if FAKE_DEVICE['attached'] else 0
        self.connection.emit_signal(
            None,
            DBUS_OBJECT_PATH,
            DBUS_INTERFACE,
            'PowerChanged',
            GLib.Variant('(uu)', (
                FAKE_DEVICE['power'],
                device_count,
            ))
        )


def main():
    global loop, connection, name_owner_id
    loop = GLib.MainLoop()
    bus_address = os.environ.get(BUS_ADDRESS_ENV)
    if not bus_address:
        print(f'{BUS_ADDRESS_ENV} must be set to a valid D-Bus address', file=sys.stderr)
        return 1

    connection = Gio.DBusConnection.new_for_address_sync(
        bus_address,
        Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,
        None,
    )
    if connection is None:
        print(f'Failed to connect to bus address: {bus_address}', file=sys.stderr)
        return 1

    write_bus_address(bus_address)
    _register_hotswap_object(connection)
    name_owner_id = Gio.bus_own_name_on_connection(
        connection,
        DBUS_BUS_NAME,
        Gio.BusNameOwnerFlags.NONE,
        on_name_acquired,
        on_name_lost,
    )
    if name_owner_id == 0:
        print('Failed to own bus name on connection', file=sys.stderr)
        return 1

    control_thread = threading.Thread(target=_serve_control_socket, daemon=True)
    control_thread.start()

    try:
        loop.run()
    except KeyboardInterrupt:
        pass

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
