import sys
import webbrowser
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPixmap
from flask import Flask, render_template
from threading import Thread
import os
import PyQt5

os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(
    os.path.dirname(PyQt5.__file__),
    "Qt",
    "plugins",
    "platforms"
)

# 1. Flask 서버 설정 (웹 화면 담당)
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

def run_flask():
    app.run(port=5000)

# 2. 캐릭터 런처 설정 (데스크탑 아이콘 담당)
class CharacterLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.label = QLabel(self)
        pixmap = QPixmap('ui-icon/icon.png')
        #아이콘 크기 조절
        pixmap = pixmap.scaled(130, 130, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label.setPixmap(pixmap)
        self.resize(pixmap.width(), pixmap.height())

        self.oldPos = self.pos()
        self.isDragging = False  # 이거 꼭 추가

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            QApplication.quit()
        elif event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()
            self.isDragging = False

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        if delta.manhattanLength() > 5:
            self.isDragging = True
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and not self.isDragging:
            webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    # Flask 서버를 배경에서 실행
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # 캐릭터 위젯 실행
    qt_app = QApplication(sys.argv)
    launcher = CharacterLauncher()
    launcher.show()
    sys.exit(qt_app.exec_())