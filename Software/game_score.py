import os
import platform
import random
import subprocess
import sys
import traceback

try:
    import RPi.GPIO as GPIO
    ON_PI = True
except (ImportError, RuntimeError):
    ON_PI = False

    class _DummyGPIO:
        BCM = IN = PUD_UP = BOTH = None

        def setmode(self, *_):
            pass

        def setup(self, *_):
            pass

        def input(self, *_):
            return 1

        def add_event_detect(self, *_ , **__):
            pass

        def cleanup(self):
            pass

    GPIO = _DummyGPIO()

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QMovie
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

import controller

BEAM_PIN = 17           # BCM numbering; beam‑break pulls the pin *LOW*
GAME_TIME = 60          # seconds
QUICK_QUIT_MS = 10      # poll period for ⃝ / back button
GIF_DURATION_MS = 2500  # how long each celebratory GIF shows

class Scoreboard(QWidget):

    beam_tripped = pyqtSignal()

    def __init__(self, gif_folder: str):
        super().__init__()
        self.setWindowTitle("Scoreboard")
        self.gif_folder = gif_folder

        self.score = 0
        self.time_left = GAME_TIME
        self._movie: QMovie | None = None
        self.robot_process: subprocess.Popen[str] | None = None

        self.timer_label = QLabel(f"Time Left: {GAME_TIME}")
        self.timer_label.setStyleSheet("font-size: 28px;")
        self.score_label = QLabel("Score: 0")
        self.score_label.setStyleSheet("font-size: 36px; font-weight: bold;")
        self.gif_label = QLabel()
        self.gif_label.setVisible(False)
        self.continue_button = QPushButton("Continue")
        self.continue_button.setVisible(False)
        self.continue_button.clicked.connect(self.cleanup_and_exit)

        lay = QVBoxLayout()
        for w in (self.timer_label, self.score_label, self.gif_label, self.continue_button):
            lay.addWidget(w, alignment=Qt.AlignCenter)
        self.setLayout(lay)

        quit_timer = QTimer(self)
        quit_timer.timeout.connect(
            lambda: self.cleanup_and_exit()
            if controller.poll()["state"]["back"]
            else None,
        )
        quit_timer.start(QUICK_QUIT_MS)

        pycmd = "python3" if platform.system() != "Windows" else "python"
        try:
            self.robot_process = subprocess.Popen([pycmd, "game_logic.py", "--headless"])
        except Exception as exc:  # noqa: BLE001
            print("❌ Failed to launch robot:", exc)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer)
        self.timer.start(1000)

        if ON_PI:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(BEAM_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

            def _beam_callback(channel: int):
                self.beam_tripped.emit()

            GPIO.add_event_detect(
                BEAM_PIN,
                GPIO.BOTH,
                callback=_beam_callback,
                bouncetime=120,
            )
        else:
            print("⚠️  GPIO stub active — scoring only via <space> key")

        self.beam_tripped.connect(self.register_goal)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.register_goal()
        elif event.key() == Qt.Key_Escape:
            self.cleanup_and_exit()

    def register_goal(self):

        if self.time_left <= 0:
            return
        self.score += 1
        self.score_label.setText(f"Score: {self.score}")
        self._show_random_gif()

    def _show_random_gif(self):
        gifs = [f for f in os.listdir(self.gif_folder) if f.lower().endswith(".gif")]
        if not gifs:
            return
        chosen = os.path.join(self.gif_folder, random.choice(gifs))
        self._movie = QMovie(chosen)
        self.gif_label.setMovie(self._movie)
        self.gif_label.setVisible(True)
        self._movie.start()
        QTimer.singleShot(GIF_DURATION_MS, self._hide_gif)

    def _hide_gif(self):
        if self._movie:
            self._movie.stop()
        self.gif_label.setVisible(False)

    def _update_timer(self):
        self.time_left -= 1
        if self.time_left <= 10:
            self.timer_label.setStyleSheet("font-size: 28px; color: red;")
        if self.time_left > 0:
            self.timer_label.setText(f"Time Left: {self.time_left}")
        else:
            self.timer_label.setText("Time's up!")
            self.timer.stop()
            self.continue_button.setVisible(True)

    def cleanup_and_exit(self):
        try:
            if ON_PI:
                GPIO.cleanup()
        except Exception:
            traceback.print_exc()
        if self.robot_process:
            self.robot_process.terminate()
        print(self.score, flush=True)
        QApplication.instance().quit()
        sys.exit(0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    if os.path.exists("theme.qss"):
        with open("theme.qss", "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    gif_path = r"E:\30_april\goal gifs" # remember

    scoreboard = Scoreboard(gif_folder=gif_path)
    scoreboard.showFullScreen()

    sys.exit(app.exec_())
