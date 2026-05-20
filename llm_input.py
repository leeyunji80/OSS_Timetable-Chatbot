# llm_api.py에서 작성한 함수를 가져옴
# 사용자의 문장을 넘겨주기 위한 메인 실행 파일
from llm_api import parse_schedule_text

# 사용할 오픈AI API 키를 변수로 지정

MY_API_KEY = "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"

def main():
# 사용자가 입력할 예시 문장 정의 단계 
    user_sentence = "컴공 기준 월요일 오전수업 피하고 금공강 만들어줘"
    
    print(f"입력된 문장: {user_sentence}")
    print(" LLM 엔진 분석을 시작합니다...")