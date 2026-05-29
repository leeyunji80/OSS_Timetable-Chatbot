import sys
import webbrowser
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPixmap
from flask import Flask, render_template, request, jsonify, send_from_directory
from threading import Thread
import os
import PyQt5
import json

with open('./student/students.json', 'r', encoding='utf-8') as f:
    students = json.load(f)

os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(
    os.path.dirname(PyQt5.__file__),
    "Qt",
    "plugins",
    "platforms"
)

# Flask 서버 설정 (웹 화면 담당)
app = Flask(__name__)

# 데이터 영구 저장을 위한 서버 로컬 디렉토리 환경 구성
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chat_data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 학번별 독립적인 파일 경로 반환 도우미 함수
def get_user_data_path(student_id):
    return os.path.join(DATA_DIR, f"chat_sessions_{student_id}.json")

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

# 실시간 데이터 파일 저장을 위한 영구화 API 엔드포인트 구현
@app.route('/save_chat', methods=['POST'])
def save_chat():
    data = request.get_json()
    student_id = data.get('student_id')
    chat_sessions = data.get('chat_sessions')
    
    if not student_id:
        return jsonify({"success": False, "message": "학번 정보가 누락되었습니다."}), 400
        
    file_path = get_user_data_path(student_id)
    
    # 텍스트, 인코딩, 이미지 경로 포맷을 깨뜨리지 않고 안전하게 파일 시스템 백업
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(chat_sessions, f, ensure_ascii=False, indent=2)
        
    return jsonify({"success": True, "message": "서버에 영구 백업 완료"})

@app.route('/get_chats', methods=['GET'])
def get_chats():
    """이전 시간표 조회 API"""
    student_id = request.args.get('student_id')
    
    if not student_id:
        return jsonify({"success": False, "message": "학번 정보가 필요합니다."}), 400
        
    file_path = get_user_data_path(student_id)
    
    # 파일이 존재하면 읽어오고, 없으면 빈 배열 반환
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                saved_sessions = json.load(f)
            except json.JSONDecodeError:
                saved_sessions = []
    else:
        saved_sessions = []
        
    return jsonify({
        "success": True,
        "chat_sessions": saved_sessions
    })

def delete_chat():
    """채팅 삭제 API (특정 세션 ID만 JSON 파일에서 파기)"""
    data = request.get_json()
    student_id = data.get('student_id')
    session_id = data.get('session_id')  # 삭제 타겟 세션 고유 ID
    
    if not student_id or not session_id:
        return jsonify({"success": False, "message": "필수 파라미터가 누락되었습니다."}), 400
        
    file_path = get_user_data_path(student_id)
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                chat_sessions = json.load(f)
            except json.JSONDecodeError:
                chat_sessions = []
                
        # 전달받은 session_id와 일치하지 않는 데이터만 걸러내어 파일 업데이트
        filtered_sessions = [s for s in chat_sessions if s.get('id') != int(session_id)]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(filtered_sessions, f, ensure_ascii=False, indent=2)
            
        return jsonify({"success": True, "message": "서버 파일에서 세션 삭제 성공"})
        
    return jsonify({"success": False, "message": "삭제할 데이터 파일이 존재하지 않습니다."}), 404

@app.route('/login', methods=['POST'])
def login():

    data = request.get_json()

    student_name = data.get('name')
    student_id = data.get('student_id')

    for student in students:

        if (
            student['student_id'] == student_id
            and student['name'] == student_name
        ):
            
            # 해당 사용자의 파일 시스템 백업 기록 확인 후 자동 로드
            file_path = get_user_data_path(student_id)
            saved_sessions = []
            
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    saved_sessions = json.load(f)

            return jsonify({
                'success': True,
                'student': student,
                'chat_session': saved_sessions
            })

    return jsonify({
        'success': False
    })

@app.route('/student/<path:filename>')
def student_files(filename):

    return send_from_directory(
        'student',
        filename
    )

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