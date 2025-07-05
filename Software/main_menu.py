import sys, json, os, platform
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton,
                             QVBoxLayout, QDialog)
from PyQt5.QtCore  import Qt, QProcess, QTimer
from PyQt5.QtGui   import QPixmap, QKeyEvent
import controller

app = QApplication(sys.argv)
with open("theme.qss") as f:
    app.setStyleSheet(f.read())

SCORE_FILE = "scores.json"
def load_scores():
    return json.load(open(SCORE_FILE)) if os.path.exists(SCORE_FILE) else []
def save_score(initials, score):
    data = load_scores()
    data.append({"initials": initials, "score": score})
    data.sort(key=lambda x: x["score"], reverse=True)
    json.dump(data[:10], open(SCORE_FILE, "w"))

class InitialsDialog(QDialog):
    def __init__(self, score):
        super().__init__()
        self.letters = ["A", "A", "A"]; self.col = 0; self.score = score
        self.setWindowFlags(Qt.FramelessWindowHint); self.showFullScreen()

        msg = QLabel(f"Score {score}\n↑↓ change  ←→ move\n✕ submit  ◯ cancel")
        msg.setAlignment(Qt.AlignCenter); msg.setStyleSheet("font-size:32px;")

        self.lbl = QLabel(); self.lbl.setAlignment(Qt.AlignCenter)
        self.lbl.setStyleSheet("font-size:72px;")

        lay = QVBoxLayout(self); lay.addStretch()
        lay.addWidget(msg); lay.addWidget(self.lbl); lay.addStretch()

        self._focus()
        QTimer(self, interval=10, timeout=self._pad).start()

    def _pad(self):
        pad = controller.poll()
        st, ev = pad["state"], pad["event"]


        if ev["up"]:   self._step(-1)
        if ev["down"]: self._step(+1)

        if ev["left"]:  self.col = (self.col - 1) % 3; self._focus()
        if ev["right"]: self.col = (self.col + 1) % 3; self._focus()
        if ev["sel"]:   self._confirm()
        if ev["back"]:  self.reject()

    def _step(self, d):
        a = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        idx = (a.index(self.letters[self.col]) + d) % 26
        self.letters[self.col] = a[idx]; self._focus()

    def _focus(self):
        txt = "".join(self.letters)
        self.lbl.setText(txt[:self.col] + "<u>" + txt[self.col] + "</u>" + txt[self.col+1:])

    def _confirm(self):
        save_score("".join(self.letters), self.score)
        self.accept()

class ScoreWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.showFullScreen()

        lay = QVBoxLayout(self); lay.addStretch()
        lay.addWidget(self._lbl("=== TOP 10 ==="))
        for i, e in enumerate(load_scores(), 1):
            lay.addWidget(self._lbl(f"#{i}  {e['initials']} – {e['score']}"))
        lay.addStretch()

        QTimer(self, interval=10, timeout=self._poll_back).start()

    def _lbl(self, text):
        l = QLabel(text); l.setAlignment(Qt.AlignCenter); return l

    def _poll_back(self):
        if controller.poll()["state"]["back"]:
            self.close()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()

class Menu(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot Game Menu")
        self.setFixedSize(800, 480)
        self.py = "python3" if platform.system() != "Windows" else "python"
        self._busy = False; self._idx = 0

        lay = QVBoxLayout(self)

        logo = QLabel(); logo.setPixmap(QPixmap("FiveLinkLogo.png"))
        logo.setAlignment(Qt.AlignCenter); logo.setStyleSheet("margin-bottom:20px;")
        lay.addWidget(logo)

        self.b_score = QPushButton(); lay.addWidget(self.b_score)
        self.b_tut   = QPushButton("📘 Tutorial Sheet")
        self.b_play  = QPushButton("🕹️ Start Game Mode")
        self.b_test  = QPushButton("🛠️ Test Robot Freeroam")
        self.b_exit  = QPushButton("❌ Exit")
        for b in (self.b_tut, self.b_play, self.b_test, self.b_exit):
            lay.addWidget(b)

        # overlay for tutorial
        self.overlay = QLabel(self); self.overlay.hide()
        self.overlay.setAlignment(Qt.AlignCenter)
        self.overlay.setStyleSheet("background:black;")

        # connections
        self.b_score.clicked.connect(self._open_score)
        self.b_tut.clicked.connect(self._open_tut)
        self.b_play.clicked.connect(self._start_game)
        self.b_test.clicked.connect(self._run_test)
        self.b_exit.clicked.connect(self.close)

        # focus list
        self._btns = [self.b_score, self.b_tut, self.b_play, self.b_test, self.b_exit]
        for b in self._btns: b.setFocusPolicy(Qt.StrongFocus)
        self._btns[0].setFocus()

        self._refresh_score()
        QTimer(self, interval=10, timeout=self._pad).start()


    def _pad(self):


        if self._busy and not self.overlay.isVisible():
            return

        pad = controller.poll()
        ev, st = pad["event"], pad["state"]

        if ev["back"]:
            if self.overlay.isVisible():
                self._close_overlay()
            elif self._busy and hasattr(self, "sw") and self.sw.isVisible():
                self.sw.close()
            else:
                self._send_esc()
            return

        if self._busy:
            return

        if ev["up"]:
            self._idx = (self._idx - 1) % len(self._btns)
            self._btns[self._idx].setFocus()
        if ev["down"]:
            self._idx = (self._idx + 1) % len(self._btns)
            self._btns[self._idx].setFocus()
        if ev["sel"]:
            self._btns[self._idx].click()

    def _send_esc(self):
        QApplication.postEvent(
            self, QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        )


    def _set_busy(self, flag: bool):
        self._busy = flag
        for b in self._btns[1:] + [self.b_exit]:
            b.setEnabled(not flag)
        if flag:
            self._btns[self._idx].clearFocus()
        else:
            self._btns[self._idx].setFocus()


    def _refresh_score(self):
        top = load_scores()[:3]
        lines = ["🏆 Scoreboard"] + [f"#{i} {e['initials']} – {e['score']}" for i, e in enumerate(top, 1)]
        self.b_score.setText("\n".join(lines))


    def _open_score(self):
        self._set_busy(True)
        self.sw = ScoreWindow()
        self.sw.destroyed.connect(lambda: self._set_busy(False))

    def _open_tut(self):
        self.overlay.setGeometry(self.rect())
        self.overlay.setPixmap(
            QPixmap("tutorial.png").scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
        )
        self.overlay.show(); self.overlay.raise_()
        self._set_busy(True)

    def _close_overlay(self):
        self.overlay.hide()
        self._set_busy(False)

    def _start_game(self):
        if self._busy: return
        self._set_busy(True)
        self.proc = QProcess(self)
        self.proc.finished.connect(self._done_game)
        self.proc.start(self.py, ["game_score.py"])

    def _done_game(self):
        out = self.proc.readAllStandardOutput().data().decode()
        score = next((int(s) for s in out.split() if s.isdigit()), None)
        if score:
            InitialsDialog(score).exec_()
            self._refresh_score()
        self._set_busy(False)

    def _run_test(self):
        if self._busy: return
        self._set_busy(True)
        self.proc = QProcess(self)
        self.proc.finished.connect(lambda: self._set_busy(False))
        self.proc.start(self.py, ["game_logic.py"])


    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape and self.overlay.isVisible():
            self._close_overlay()

if __name__ == "__main__":
    m = Menu()
    m.showFullScreen()
    sys.exit(app.exec_())
