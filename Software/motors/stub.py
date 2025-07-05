
RAIL_MIN  = 0
RAIL_MAX  = 36_000
RAIL_STEP = 100


class _Dummy:
    def __init__(self, name):
        self.n = name
        self._target = 0

    def set_pose(self, *a):  print(f"[sim] {self.n}.set_pose{a}")
    def set_speed(self, v):  print(f"[sim] {self.n}.set_speed({v:.2f})")
    def set_ratio(self, v):  print(f"[sim] {self.n}.set_ratio({v:.8f})")

    def torque_off(self):    print(f"[sim] {self.n}.torque_off()")
    def nudge(self, axis_val: float):
        if axis_val == 0.0:
            return
        self._target = max(
            RAIL_MIN,
            min(RAIL_MAX, self._target + axis_val * RAIL_STEP)
        )
        print(f"[sim] {self.n}.nudge({axis_val:+.3f}) → {self._target}")

    def get_norm(self) -> float:
        return self._target / RAIL_MAX





FiveBar = _Dummy("fivebar")
Rail    = _Dummy("rail")
Gripper = _Dummy("gripper")
