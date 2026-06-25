"""
PDA module state helpers.

This file stores temporary demo data and helper functions for generating
module-related status text. Later, this can be replaced or extended with
real data from the hot-swap daemon through D-Bus.
"""

# Demo data used by the UI until real daemon / D-Bus data is connected.
# The module count shown in the status bar is calculated from this list.

DAEMON_STATUS = "Running (Testing)"

MODULES = [
    {
        "name": "Expansion module A",
        "role": "Demo module",
        "state": "connected"
    },
    {
        "name": "Expansion module B",
        "role": "Demo module",
        "state": "connected"
    }
]


def get_connected_module_count():
    """
    Count connected modules from the current module state list.
    """
    return sum(
        1 for module in MODULES
        if module.get("state") == "connected"
    )


def get_status_bar_text(expanded=False):
    """
    Build the top status bar text from current module state.
    """
    connected_count = get_connected_module_count()
    total_count = len(MODULES)
    arrow = "▲" if expanded else "▼"

    if total_count == 0:
        module_text = "No modules detected"
    else:
        module_text = f"{connected_count}/{total_count} modules active"

    return f"{module_text} {arrow}"


def get_module_detail_lines():
    """
    Build text lines for the expanded module status panel.
    """
    lines = [
        f"Hot-swap daemon: {DAEMON_STATUS}"
    ]

    if MODULES:
        for index, module in enumerate(MODULES, start=1):
            module_name = module.get("name", f"Module {index}")
            module_role = module.get("role", "Unknown role")
            module_state = module.get("state", "unknown")

            lines.append(
                f"{module_name}: {module_state} · {module_role}"
            )
    else:
        lines.append("Modules: none detected")

    lines.append("Last update: demo placeholder")

    return lines