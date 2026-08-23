# governors.py
# Last updated: August 2026
# Author: Nelson Nguyen


from pathlib import Path

CPU_PATH = Path("/sys/devices/system/cpu")


# Grabs the current governor , default should be schedutil
def get_current_governor():
    path = CPU_PATH / "cpu0/cpufreq/scaling_governor"

    with path.open("r") as file:
        return file.read().strip()


# Sets the governor for the CPU
def set_governor(governor):
    for cpu in CPU_PATH.glob("cpu[0-9]*"):
        path = cpu / "cpufreq/scaling_governor"

        if path.exists():
            path.write_text(governor)


# Lists the avilable governors
def available_governors():
    path = CPU_PATH / "cpu0/cpufreq/scaling_available_governors"
    return path.read_text().split()


def restore_governor(governor):
    for cpu in CPU_PATH.glob("cpu[0-9]*"):
        path = cpu / "cpufreq/scaling_governor"

        if path.exists():
            path.write_text(governor)
