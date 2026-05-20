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