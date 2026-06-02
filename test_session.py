import os
from dotenv import load_dotenv
from llm_api import parse_schedule_text_with_history

load_dotenv()

API_KEY = os.environ.get("OPENAI_API_KEY")
SESSION_ID = "test_user_1234"

# 시나리오 1단계: 단발성 입력 환경
print("== [TEST 1] 단발성 입력 환경에서의 이전 버전 호환성 테스트 ==")
# 1차 입력
text_1 = "수요일 오후 수업은 빼주고 18학점 맞춰줘"
print(f">> 유저 입력 문장: {text_1}\n")
result_1 = parse_schedule_text_with_history(SESSION_ID, text_1, API_KEY)
print(result_1)

# 시나리오 2단계: 누적 데이터 검증 구간
print("\n== [TEST 2] 연속 입력 시나리오 테스트 ==")
# 2차 입력
text_2 = "2교시 빼줘"
print(f">> 유저 입력 문장: {text_2}\n")
result_2 = parse_schedule_text_with_history(SESSION_ID, text_2, API_KEY)
print(result_2)

# 시나리오 3단계: 조건 취소 및 수정 데이터 검증 완료
print("\n== [TEST 3] 조건 취소 및 수정 시나리오 테스트 ==")
# 3차 입력
text_3 = "생각해보니까 월요일은 그냥 2교시 들어도 상관없을 거 같아. 대신 화요일 공강 추가해줘 그리고 이산수학은 안들을래 "
print(f">> 유저 입력 문장: {text_3}\n")
result_3 = parse_schedule_text_with_history(SESSION_ID, text_3, API_KEY)
print(result_3)



