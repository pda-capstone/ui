#!/usr/bin/env python3
# fake_hotswapd_ctl.py
# This functions as the 'control panel' to simulate attach,detach,change power, and check status
# Owner: Griffin
# Last updated: July 2026
import os
import sys
import socket

CONTROL_SOCKET = os.environ.get(
    "FAKE_HOTSWAPD_CONTROL_SOCKET", "/tmp/fake_hotswapd-control.sock"
)


def print_usage():
    print("Usage: fake_hotswapd_ctl.py <command> [args]")
    print("Commands: attach, detach, power <mA>, status, help, quit")


def run_command(argv):
    if len(argv) < 2:
        print_usage()
        return 1

    command = " ".join(argv[1:]).strip()
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(CONTROL_SOCKET)
            client.sendall(command.encode("utf-8"))
            response = client.recv(4096)
            sys.stdout.write(response.decode("utf-8"))
    except FileNotFoundError:
        print(f"Control socket not found: {CONTROL_SOCKET}", file=sys.stderr)
        return 1
    except ConnectionRefusedError:
        print(
            f"Failed to connect to fake daemon control socket: {CONTROL_SOCKET}",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(
            f"Error communicating with fake daemon control socket: {exc}",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(run_command(sys.argv))
