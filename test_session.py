
# 연속 대화형 시간표 분석 파서 최종 검증 스크립트 (2026-06-02)
import os
from dotenv import load_dotenv
from llm_api import parse_schedule_text_with_history


#주의
# 로컬 개발 환경의 .env 파일에 OPENAI_API_KEY가 반드시 정의되어 있어야 합니다.
load_dotenv()

API_KEY = os.environ.get("OPENAI_API_KEY")
SESSION_ID = "test_user_1234"

print("== [TEST 1] 단발성 입력 환경에서의 이전 버전 호환성 테스트 ==")
# 1차 입력
text_1 = "금요일은 꼭 공강으로 만들고 싶고, 21학점들을거야. 문화로보는생활사 넣어줘. 대신 전공필수는 최대한 많이 넣어줘. 오전 1교시는 절대 싫어."
print(f">> 유저 입력 문장: {text_1}\n")
result_1 = parse_schedule_text_with_history(SESSION_ID, text_1, API_KEY)
print(result_1)

# 시나리오 2단계: 누적 데이터 검증 구간
print("\n== [TEST 2] 연속 입력 시나리오 테스트 (누적 확인) ==")
# 2차 입력: 수요일 오후 알바 추가 (기존 금요일 공강, 월요일 오후 선호가 유지되어야 함)
text_2 = "나 수요일은 알바 있어서 일찍 끝내줘"
print(f">> 유저 입력 문장: {text_2}\n")
result_2 = parse_schedule_text_with_history(SESSION_ID, text_2, API_KEY)
print(result_2)

# 시나리오 3단계: 조건 취소 및 수정 데이터 검증 완료
print("\n== [TEST 3] 조건 취소 및 수정 시나리오 테스트 ==")
# 3차 입력: 월요일 1교시 싫다고 한 거 취소
text_3 = "생각해보니까 월요일은 그냥 1교시 들어도 상관없을 거 같아. 대신 화요일 공강 추가해줘"
print(f">> 유저 입력 문장: {text_3}\n")
result_3 = parse_schedule_text_with_history(SESSION_ID, text_3, API_KEY)
print(result_3)




