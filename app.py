import sys
import webbrowser
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPixmap
from flask import Flask, render_template
from threading import Thread

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
        # 배경 투명하게 만들기
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.label = QLabel(self)
        # 중요: images 폴더에 icon.png 파일이 존재
        pixmap = QPixmap('ui-icon/icon.png')
        self.label.setPixmap(pixmap)
        self.resize(pixmap.width(), pixmap.height())
        self.oldPos = self.pos()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()
            # 아이콘 클릭 시 브라우저 열기
            webbrowser.open('http://127.0.0.1:5000')

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()

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