

import pygame
pygame.init()

HAT_IDX = 0

_BTN = {
    "sel"  : 0,   # ✕
    "back" : 1,   # ◯
    "ltrig": 6,   # L2 digital click
}

_AX  = {
    "lx": 0, "ly": 1,     # left stick
    "rx": 3, "ry": 4,     # right stick
    "lt": 2,              # L2 analogue trigger
}


try:
    JS = pygame.joystick.Joystick(0)
    JS.init()
except pygame.error:
    JS = None

_prev = dict.fromkeys(
    ["up","down","left","right", * _BTN], 0
)


def _dig_now():

    now = {}


    if JS and JS.get_numhats() > HAT_IDX:
        hx, hy = JS.get_hat(HAT_IDX)
        now.update({
            "up":    int(hy > 0),
            "down":  int(hy < 0),
            "left":  int(hx < 0),
            "right": int(hx > 0),
        })
    else:
        now.update({k:0 for k in ("up","down","left","right")})


    for k, idx in _BTN.items():
        now[k] = JS.get_button(idx) if JS else 0
    return now

def _axes_now():

    return {k: JS.get_axis(i) if JS else 0.0 for k,i in _AX.items()}

def poll():
    if JS:
        for _ in pygame.event.get():
            pass

    now   = _dig_now()
    event = {k: int(now[k] and not _prev[k]) for k in now}
    _prev.update(now)

    return {
        "event": event,
        "state": now,
        "axes" : _axes_now(),
    }


if __name__ == "__main__":
    import time, pprint
    print("Polling… Ctrl-C to quit")
    try:
        while True:
            pprint.pprint(poll())
            time.sleep(0.1)
    except KeyboardInterrupt:
        print()
