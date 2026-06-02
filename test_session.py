
import os
from llm_api import parse_schedule_text_with_history

API_KEY = os.environ.get("OPENAI_API_KEY", "본인의_실제_API_키_나_환경변수")
SESSION_ID = "test_user_1234"

print("=== [TEST 1] 단발성 입력 환경에서의 이전 버전 호환성 테스트 ===")
# 1차 입력: 금요일 공강, 월요일 오후 선호, 1교시 극혐
text_1 = "금요일은 꼭 공강으로 만들고 싶고, 월요일도 가능하면 오후 수업만 있었으면 좋겠어. 대신 전공필수는 최대한 많이 넣어줘. 오전 1교시는 절대 싫어."
result_1 = parse_schedule_text_with_history(SESSION_ID, text_1, API_KEY)
print(result_1)