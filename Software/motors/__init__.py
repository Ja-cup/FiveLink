
import importlib, sys
from .stub import FiveBar, Rail, Gripper   # defaults

# Dynamixel
try:
    importlib.import_module("dynamixel_sdk")
    from .dxl import FiveBar
    print("[motors] Dynamixel live")
except Exception as e:
    print("[motors] no Dynamixel → stub:", e, file=sys.stderr)


# HS-1
try:
    from .hs1 import Rail, Gripper
    print("[motors] HS-1 live")
except Exception as e:
    from .stub import Rail, Gripper
    print("[motors] no HS-1 → stub:", e, file=sys.stderr)


def torque_off():
    FiveBar.torque_off()
    Rail.torque_off()
    Gripper.torque_off()
