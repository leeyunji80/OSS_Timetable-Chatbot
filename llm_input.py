# llm_api.py에서 우리가 만든 함수를 가져옵니다.
from llm_api import parse_schedule_text

#  [필수 변경] 본인의 실제 OpenAI API 키를 따옴표 안에 넣어주세요!
# 예: MY_API_KEY = "sk-proj-xxxx..."
MY_API_KEY = "your-api-key-here"

def main():
    # 1. 분석할 예시 문장
    user_sentence = "컴공 기준 월요일 오전수업 피하고 금공강 만들어줘"
    
    print(f"입력 문장: {user_sentence}")
    print(" LLM이 문장을 분석하는 중입니다. 잠시만 기다려주세요...\n")
    
    try:
        # 2. llm_api.py에 있는 함수를 호출해서 결과 받기
        json_result = parse_schedule_text(user_sentence, MY_API_KEY)
        
        print(" 분석 완료! 결과 JSON 데이터:")
        print(json_result)
        
    except Exception as e:
        print(f" 에러가 발생했습니다: {e}")
        print("API 키가 올바른지, 터미널에 pip install openai pydantic를 실행했는지 확인해 주세요.")

if __name__ == "__main__":
    main()