# .env 파일에 저장된 환경 변수를 로드하기 위한 라이브러리 추가
# 이를 통해 코드가 실제 API 키 값을 올바르게 인식하게 됨
import os
from dotenv import load_dotenv
load_dotenv()


# llm_api.py에서 작성한 함수를 가져옴
# 사용자의 문장을 넘겨주기 위한 메인 실행 파일
from llm_api import parse_schedule_text

# 사용할 오픈AI API 키를 변수로 지정

MY_API_KEY = os.environ.get("OPENAI_API_KEY")

def main():
# 사용자가 입력할 예시 문장 정의 단계 
    user_sentence = "나는 컴공 2학년인데 표준이수모형에 맞게 전선과 전필을 최대한 넣어주되 월요일 1교시는 피해주고 금요일은 공강 만들어줘 교양은 문화로보는생활사는 넣어줘"
    
    print(f"입력된 문장: {user_sentence}")
    print(" LLM 엔진 분석을 시작합니다...")

    try:
        # llm_api 파일의 함수를 호출하여 결과 JSON을 받아옴
        json_result = parse_schedule_text(user_sentence, MY_API_KEY)
        print("\n 분석 성공! 결과 데이터:")

        print(json_result)
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    main()