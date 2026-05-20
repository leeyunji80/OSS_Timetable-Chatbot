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

    try:
        # llm_api 파일의 함수를 호출하여 결과 JSON을 받아옴
        json_result = parse_schedule_text(user_sentence, MY_API_KEY)
        print("\n 분석 성공! 결과 데이터:")

        print(json_result)
    except Exception as e:
        print(f" 에러 발생: {e}")

if __name__ == "__main__":
    main()