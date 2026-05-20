# 라이브러리 로드 세트
# os: 환경 변수 관리
# pydantic: 데이터 구조 검증용
import os
from pydantic import BaseModel, Field

from typing import List, Optional, Literal
from openai import OpenAI

# 시간표의 단일 슬롯을 정의하는 클래스
class TimeSlot(BaseModel):
    day: Literal["월요일", "화요일", "수요일", "목요일", "금요일"] = Field(
        description="요청사항에 언급된 요일 (주말은 제외)"
    )
    # 시간대 키워드 제한 (오전/오후/공강 분기)
    time_range: Optional[Literal["오전", "오후", "우주공강", "연강"]] = Field(None)

    condition: Literal["선호", "피함", "공강"] = Field(
        description="사용자의 최종 요구 조건 상태"
    )

class ExtractedSchedule(BaseModel):
    slots: List[TimeSlot] = Field(description="추출된 시간표 조건 목록")
    major: Optional[Literal["컴퓨터공학", "일반"]] = Field(
        "일반", 
        description="전공 언급 분류"
    )

def parse_schedule_text(user_text: str, api_key: str) -> str:
    # OpenAI 클라이언트 객체를 생성하는 구간
    # 전달받은 api_key를 활용함
    client = OpenAI(api_key=api_key)

    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "너는 대학생들의 시간표 요구사항 문장에서 핵심 슬롯을 추출하는 AI야."},
            {"role": "user", "content": user_text}
        ],

        response_format=ExtractedSchedule,
    )
    return response.choices[0].message.content