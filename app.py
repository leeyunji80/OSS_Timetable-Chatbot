import sys
import webbrowser
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPixmap
from flask import Flask, render_template, request, jsonify
from threading import Thread
import os
import PyQt5
import json

with open('students.json', 'r', encoding='utf-8') as f:
    students = json.load(f)

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

@app.route('/chat', methods=['POST'])
def chat():

    data = request.get_json()

    user_message = data['message']

    print(user_message)

    return jsonify({
        'reply': f'"{user_message}" 조건의 시간표를 생성했습니다.',
        'image': '/static/timetable.png'
    })

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

        # 화면 우측 하단 배치 로직
        # 현재 주 모니터의 전체 화면 크기(해상도) 감지
        screen = QApplication.primaryScreen().geometry()
        screen_width = screen.width()
        screen_height = screen.height()

       # 모니터 가로의 95%, 세로의 90% 지점을 기준으로 정렬 (예시)
        x = int(screen_width * 93/100) - pixmap.width()
        y = int(screen_height * 90/100) - pixmap.height()

        # 계산된 좌표로 초기 위치 설정
        self.move(x, y)

        self.oldPos = self.pos()
        self.isDragging = False  

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