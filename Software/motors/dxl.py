import dynamixel_sdk as dxl, numpy as np

DEV  = "/dev/ttyUSB0"
BAUD = 57600
ID1, ID2 = 1, 2

ADDR_TORQUE_EN = 64
ADDR_GOAL_POS  = 116

ph = dxl.PortHandler(DEV)
ph.openPort();  ph.setBaudRate(BAUD)
pk = dxl.PacketHandler(2.0)

for i in (ID1, ID2):
    pk.write1ByteTxRx(ph, i, ADDR_TORQUE_EN, 1)

def _rad_to_raw(rad: float) -> int:
    return int((rad + np.pi) / (2*np.pi) * 4095) & 0x0FFF

class FiveBar:
    @staticmethod
    def set_pose(t1_rad, t2_rad):

        pk.write4ByteTxRx(ph, ID1, ADDR_GOAL_POS, _rad_to_raw(t1_rad))
        pk.write4ByteTxRx(ph, ID2, ADDR_GOAL_POS, _rad_to_raw(t2_rad))

    @staticmethod
    def torque_off():
        for i in (ID1, ID2):
            pk.write1ByteTxRx(ph, i, ADDR_TORQUE_EN, 0)
        ph.closePort()
