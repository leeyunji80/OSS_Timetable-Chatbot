from openai import OpenAI
import json

client = OpenAI(
    api_key="여기에_API키_붙여넣기"
)

user_input = "월요일 오전 수업은 피하고 오후 수업은 넣고 싶어"

prompt = f"""
사용자의 시간표 요구사항을 분석하여
JSON 형태로 반환해라.

반드시 JSON만 출력해라.

형식 예시:

[
  {{
    "요일": "월요일",
    "시간": "오전",
    "조건": "회피"
  }},
  {{
    "요일": "월요일",
    "시간": "오후",
    "조건": "선호"
  }}
]

사용자 입력:
{user_input}
"""

response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ]
)

result = response.choices[0].message.content

print(result)
