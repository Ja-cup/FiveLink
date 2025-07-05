import numpy as np
import pygame
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
import sys
import controller
from PyQt5.QtCore import QTimer
from motors import FiveBar, Rail, Gripper, torque_off

DEADZONE = 0.10 # reduce drift
headless = "--headless" in sys.argv

if not headless:
    app = QtWidgets.QApplication([])

#  Pygame / joystick
pygame.init()
joystick = None
if pygame.joystick.get_count() > 0:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print("Joystick:", joystick.get_name())
else:
    print("No joystick detected!")

#  5‑link geometry
L1, L2 = 1.56, 3.25
base1 = np.array([-0.45, 2.0])
base2 = np.array([0.45, 2.0])
end_effector = np.array([0.0, -2])

# Rail / gripper visual parameters
X_RAIL     = -3.0
X_GRIPPER  =  3.0
Y_MIN, Y_MAX = -3.0, 2.0   # slider range in plot coords



#  IK solver


def inverse_kinematics(x, y):
    try:
        if any([x<-2.5, x>2.5, y< -2.5, x>1 and y < -1.5]): # boundary for case and hoop
            return None, None, None, None
        d1 = np.linalg.norm([x - base1[0], y - base1[1]])
        d2 = np.linalg.norm([x - base2[0], y - base2[1]])
        if d1 > (L1 + L2) or d2 > (L1 + L2): # is arm long enough
            return None, None, None, None
        theta1 = -np.arccos((L1**2 + d1**2 - L2**2) / (2 * L1 * d1)) + np.arctan2(
            y - base1[1], x - base1[0]
        )
        elbow1 = base1 + L1 * np.array([np.cos(theta1), np.sin(theta1)])
        theta2 = np.arccos((L1**2 + d2**2 - L2**2) / (2 * L1 * d2)) + np.arctan2(
            y - base2[1], x - base2[0]
        )
        elbow2 = base2 + L1 * np.array([np.cos(theta2), np.sin(theta2)])
        #print (theta1, theta2, elbow1, elbow2) # for making constraints
        if any([np.isnan(theta1), np.isnan(theta2), theta1 < -4.2, theta1 > -1.6, theta2 > 1.19, theta2 < -1.55]): # boundary for angles
            return None, None, None, None
        return elbow1, elbow2, theta1, theta2
    except ValueError:
        return None, None, None, None


def is_within_workspace(x, y):
    e1, e2, th1, th2= inverse_kinematics(x, y)
    return e1 is not None and e2 is not None


if not headless:
    win = pg.GraphicsLayoutWidget(show=True)
    win.setWindowTitle("5‑Bar Parallel Robot Kinematics")

    plot = win.addPlot(row=0, col=1)
    plot.setXRange(-3.5, 3.5)
    plot.setYRange(-3.5, 2.5)
    plot.setAspectLocked(True)
    plot.showGrid(x=True, y=True)

    square = QtWidgets.QGraphicsRectItem(-2.5, -3, 5, 5)
    square.setPen(pg.mkPen("r", width=2))
    plot.getViewBox().addItem(square)

    base_points = plot.plot([base1[0], base2[0]], [base1[1], base2[1]], pen=None, symbol='o', symbolBrush='g')
    link_lines  = plot.plot([], [], pen=pg.mkPen('r', width=2))

    plot.plot([X_RAIL, X_RAIL], [Y_MIN, Y_MAX], pen=pg.mkPen('w', width=1, style=QtCore.Qt.PenStyle.DashLine))
    plot.plot([X_GRIPPER, X_GRIPPER], [Y_MIN, Y_MAX], pen=pg.mkPen('w', width=1, style=QtCore.Qt.PenStyle.DashLine))
    rail_marker    = plot.plot([X_RAIL],    [Y_MIN], pen=None, symbol='s', symbolSize=8, symbolBrush='y')
    gripper_marker = plot.plot([X_GRIPPER], [Y_MIN], pen=None, symbol='s', symbolSize=8, symbolBrush='c')



def update_plot():
    # inverse kinematics

    e1, e2 ,th1, th2 = inverse_kinematics(*end_effector)
    if e1 is None:
        return

    # send to dynamixel

    servo_right = 2 * (-th2)  # base-2 link drives RIGHT servo
    servo_left = 2 * (-th1 + np.pi)  # base-1 link drives LEFT  servo

    FiveBar.set_pose(servo_right, servo_left)  # ID-1 = right, ID-2 = left

    if headless:
        return


    # draw links
    link_lines.setData(
        [base1[0], e1[0], end_effector[0], e2[0], base2[0]],
        [base1[1], e1[1], end_effector[1], e2[1], base2[1]]
    )





def set_slider(marker, x_fixed, norm):
    """norm ∈ [0,1] → marker at x_fixed, y between Y_MIN and Y_MAX."""
    y = Y_MIN + norm * (Y_MAX - Y_MIN)
    marker.setData([x_fixed], [y])


_last_grip   = None

def update_controller():
    global _last_grip
    pad = controller.poll()
    ax  = pad["axes"]
    

    if pad["state"].get("back"):

        #try: Rail.home()
        #except Exception:pass
        QtWidgets.QApplication.instance().quit()
        return


    dx, dy = ax["rx"], ax["ry"]
    if abs(dx) > DEADZONE or abs(dy) > DEADZONE:
        step = 0.05
        nx = end_effector[0] + step * dx
        ny = end_effector[1] - step * dy
        if is_within_workspace(nx, ny):
            end_effector[:] = (nx, ny)
            update_plot()


    rail_axis = -ax["ly"]
    if abs(rail_axis) < DEADZONE:
        rail_axis = 0.0

    Rail.nudge(rail_axis)


    if not headless:
        rail_norm = Rail.get_norm()
        set_slider(rail_marker, X_RAIL, rail_norm)


    lt_raw = ax["lt"]
    lt_norm = (lt_raw + 1.0) * 0.5


    if lt_norm < DEADZONE:
        lt_norm = 0.0




    #send only when the value actually changes
    global _last_grip  # declare the guard var
    GRIP_STEP = 0.010

    if _last_grip is None or float(abs(lt_norm - _last_grip)) > GRIP_STEP:  # <─ this line stops the spam
        Gripper.set_ratio(lt_norm)
        _last_grip = lt_norm  # remember what we sent
        if not headless:
            set_slider(gripper_marker, X_GRIPPER, lt_norm)





# keyboard fallback

def keyPressEvent(ev):
    step = 0.05
    if ev.key() == QtCore.Qt.Key_Escape:
        QtWidgets.QApplication.instance().quit(); return
    m = {QtCore.Qt.Key_Up:(0, step), QtCore.Qt.Key_Down:(0,-step),
         QtCore.Qt.Key_Left:(-step,0), QtCore.Qt.Key_Right:(step,0)}
    if ev.key() in m:
        nx = end_effector[0] + m[ev.key()][0]
        ny = end_effector[1] + m[ev.key()][1]
        if is_within_workspace(nx, ny):
            end_effector[:] = (nx, ny)
            update_plot()



if __name__ == '__main__':
    if not headless:
        win.keyPressEvent = keyPressEvent
        update_plot()
        t = QtCore.QTimer(); t.timeout.connect(update_controller); t.start(50)
        QtWidgets.QApplication.instance().exec()
        torque_off()
    else:
        try:
            while True:
                update_controller(); pygame.time.wait(50)
        except KeyboardInterrupt:
            pygame.quit()
