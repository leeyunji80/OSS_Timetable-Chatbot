from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return "<h1>Flask 웹 페이지가 실행되었습니다!</h1>"

if __name__ == '__main__':
    app.run(port=5000)