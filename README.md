# OSS_Timetable-Chatbot

OSS_Timetable-Chatbot은 학생의 자연어 요청을 분석해 수강 이력, 졸업 요건, 전공/교양 추천, 공강 및 시간대 선호를 반영한 시간표를 생성하는 챗봇 프로젝트입니다. 
Flask 기반 웹 UI와 PyQt5 런처를 사용하며, OpenAI API를 통해 사용자의 시간표 요구사항을 구조화합니다.

## 주요 기능
- 자연어 기반 시간표 조건 분석
- 전공/교양/졸업요건 기반 과목 추천
- 공강 요일, 회피 시간대, 선호 시간대 반영
- 과제량 및 팀플 선호 조건 반영
- 추천 시간표 이미지 생성
- 학생별 채팅 세션 저장 및 불러오기

# 설치 방법

Repository Clone

```bash
git clone https://github.com/leeyunji80/OSS_Timetable-Chatbot.git
cd OSS_Timetable-Chatbot
```

# 의존성

```bash
pip install Flask==3.1.3
pip install openai==2.38.0
pip install pandas==3.0.3
pip install pillow==12.2.0
pip install pydantic==2.13.4
pip install PyQt5==5.15.11
pip install python-dotenv==1.2.2
pip install openpyxl==3.1.5
pip install pypdf==6.11.0 (권장사항)
```
- OS : Windows 11
- Language : Python 3.11
- IDE : Visual Studio Code
- Framework : Flask
- Database : CSV / JSON

## 주요 라이브러리
| Library  | 	Version  |	용도 |
| Flask	|   3.1.3  |	웹 서버 및 API |
| openai	|  2.38.0  |	자연어 요청 분석 |
| pandas	|  3.0.3  |       강의/학생/졸업 데이터 처리 |
| pillow	| 12.2.0  |	시간표 이미지 생성 |
| pydantic	| 2.13.4  |	LLM 응답 구조화 |
| PyQt5	| 5.15.11  |	데스크톱 런처 UI |
| python-dotenv  | 1.2.2  |	환경변수 로드 |

## 환경변수 설정
프로젝트 루트에 .env 파일을 생성하고 OpenAI API Key를 설정합니다.

```bash
OPENAI_API_KEY=your_openai_api_key
```

# 사용(실행) 방법
프로젝트 루트에서 다음 명령어를 실행합니다.
```bash
python -m ui/app.py
```
실행 후 PyQt5 런처 아이콘이 표시됩니다. 아이콘을 클릭하면 브라우저에서 다음 주소가 열립니다.
```bash
http://127.0.0.1:5000
```
브라우저에서 직접 접속해도 됩니다.

## 사용 흐름
학생 이름과 학번으로 로그인합니다. 

| 이름 | 학번 |
|------|--------|
| 김컴공 | 20210001 |
| 이필수 | 20210002 |
| 박교양 | 20210003 |
| 최저학점 | 20210004 |
| 정위험 | 20210005 |
| 한새내 | 20260001 |
| 오소포 | 20250001 |
| 서주니 | 20240001 |
| 윤시니 | 20230001 |
| 김서현 | 2025046026 |

채팅창에 원하는 시간표 조건을 자연어로 입력합니다.
시스템이 조건을 분석하고 추천 시간표와 시간표 이미지를 생성합니다.

예시:
```bash
월요일은 공강으로 하고, 화요일 오전 수업은 피하고 싶어. 전공 위주로 18학점 추천해줘.
```
종료방법 : 아이콘 우클릭

# Unit Test 실행 방법
```bash
pip install coverage

python -m coverage erase

python -m coverage run --source=. -m unittest discover -s tests -p "test_*.py"

python -m coverage report -m 
```

# 라이선스
```bash
MIT License

Copyright (c) 2026 leeyunji80

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
# Contributor name
- 김서현 @cbnu-ksh
- 이현지 @leeyunji80
- 정채린 @bluemoon5555
- 조연경 @chaean0318






