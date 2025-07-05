import sys
sys.path.append('/home/aribanani/Documents/LSS_Library_Python/src')
import lss
import lss_const as lssc
PORT = "/dev/ttyUSB1"
BAUD = lssc.LSS_DefaultBaud
lss.initBus(PORT, BAUD)

_rail    = lss.LSS(0)
_gripper = lss.LSS(1)

if not hasattr(_rail, "position"):
    _rail.position = lambda: int(_rail.getPosition() or 0)
    _gripper.position = lambda: int(_gripper.getPosition() or 0)
if not hasattr(_rail, "goto"):
    _rail.goto     = _rail.move
    _gripper.goto  = _gripper.move




RAIL_MIN    = 0
RAIL_MAX    = 36_000         # 3 600°  = 10 laps
RAIL_STEP   = 100            # 10° per tick (in 0.1° units)
rail_target = 0


def _clamp(x, lo, hi): return max(lo, min(x, hi))

class Rail:
    @staticmethod
    def nudge(axis_val: float):

        global rail_target
        if axis_val == 0.0:
            return
        rail_target = _clamp(
            rail_target + axis_val * RAIL_STEP, RAIL_MIN, RAIL_MAX
        )
        _rail.move(int(rail_target))

    @staticmethod
    def get_norm() -> float:                 # 0.0 ,,, 1.0
        return rail_target / RAIL_MAX

    @staticmethod
    def home():
        global rail_target
        rail_target = RAIL_MIN
        _rail.move(rail_target)

    @staticmethod
    def torque_off():
        global rail_target
        rail_target = RAIL_MIN
        _rail.move(rail_target)
        #_rail.hold()



GRIP_OPEN  =     0        # 0°  (trigger released)
GRIP_CLOSE = 5000        # 1000° ≈ 2.78 laps  (trigger fully pressed)

class Gripper:
    @staticmethod
    def set_ratio(t):    # t = 0 ,,, 1  (after dead-zone)
        target = GRIP_OPEN + t * (GRIP_CLOSE - GRIP_OPEN)
        _gripper.move(int(target))

    @staticmethod
    def torque_off():
        _gripper.move(int(GRIP_OPEN ))
        #_gripper.hold()

