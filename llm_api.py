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

    specific_time_slot: Optional[Literal[
        "09시", "10시", "11시", "12시", "13시", "14시", "15시", "16시", "17시", "18시이후",
        "1교시", "2교시", "3교시", "4교시", "5교시", "6교시"
    ]] = Field(
        None, 
        description="문장에 구체적인 시간이나 교시가 언급된 경우 해당 키워드로만 매핑"
    )
    
    # 시간대 키워드 제한 (오전/오후/공강 분기)
    time_range: Optional[Literal["아침", "오전", "점심", "오후", "야간"]] = Field(
        None, 
        description="9시 전후는 '아침', 18시 이후는 '야간', 그 외 점심 전후 분류"
    )

    special_condition: Optional[Literal["우주공강", "연강", "풀강", "반공강"]] = Field(
        None, 
        description="우주공강, 연강, 풀강, 반공강 등 대학생 특유의 시간표 성향 키워드"
    )

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

    system_instruction = (
        "너는 대학생들의 시간표 요구사항 문장에서 핵심 슬롯을 추출하는 완벽한 AI 파서야.\n"
        "반드시 JSON 스키마에 정의된 Literal 선택지 안의 단어로만 매핑해야 하며, 임의의 텍스트를 생성해서는 절대 안 돼.\n\n"
        "주요 매핑 규칙:\n"
        "- '9시 수업 극혐', '아침 9시 절대 피해' -> specific_time_slot='09시', time_range='아침', condition='피함'\n"
        "- '3교시 끝나고 바로', '3교시 연강' -> specific_time_slot='3교시', condition='선호'\n"
        "- '6시 이후 야간 수업', '저녁 수업' -> specific_time_slot='18시이후', time_range='야간'\n"
        "- '수업 사이에 시간 뜨는 거 극혐' -> special_condition='우주공강', condition='피함'\n"
        "- '금요일 자체 휴강', '금요일 비워줘' -> day='금요일', condition='공강'"
    )
    
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_text}
        ],

        response_format=ExtractedSchedule,
    )
    return response.choices[0].message.content