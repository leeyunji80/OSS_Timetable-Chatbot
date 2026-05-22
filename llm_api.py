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



# 사용자의 학적 정보 및 전체 시간표 메타 요구사항을 정의하는 클래스
class ExtractedSchedule(BaseModel):
    # 1. 개인정보 및 학적 정보 
    major: Literal["컴퓨터공학", "일반전공", "비전공"] = Field(
        "일반전공", 
        description="사용자의 주전공 분류 (학과별 표준이수모형 매핑용)"
    )
    grade: Optional[Literal["1학년", "2학년", "3학년", "4학년"]] = Field(
        None, 
        description="사용자의 현재 학년 (해당 학년 전공 필수/선택 추천용)"
    )
    
    # 2. 이수 조건 및 졸업 조건 관련 키워드 추출
    course_priority: Optional[List[Literal["전공필수", "전공선택", "교양필수", "일반교양"]]] = Field(
        default=[],
        description="표준이수모형 충족을 위해 우선적으로 배치해야 하는 과목 유형 목록"
    )
    
    # 3. 글로벌 시간표 제어 조건 (공강 일수 등)
    target_free_days: Optional[Literal["0일", "1일", "2일"]] = Field(
        None,
        description="사용자가 희망하는 주중 총 공강 일수 지점"
    )

    slots: List[TimeSlot] = Field(description="추출된 요일별 상세 시간대 조건 목록")




def parse_schedule_text(user_text: str, api_key: str) -> str:
    # OpenAI 클라이언트 객체를 생성하는 구간
    # 전달받은 api_key를 활용함
    client = OpenAI(api_key=api_key)

    system_instruction = (
        "너는 대학생들의 복합적인 수강신청 요구사항 문장에서 학적 메타데이터와 시간표 슬롯을 추출하는 상위 레벨 파서야.\n"
        "문맥을 분석하여 학년, 과목 우선순위, 목표 공강 일수를 정해진 규칙에 따라 완벽하게 JSON으로 변환해줘.\n\n"
        "규칙 설명:\n"
        "1. [학년/전공]: '컴공 2학년' -> major='컴퓨터공학', grade='2학년'\n"
        "2. [이수 과목 우선순위]: '전필이랑 전선', '표준이수모형' -> course_priority=['전공필수', '전공선택']\n"
        "3. [전체 공강 일수]: '공강은 하루만', '주 4일 시간표' -> target_free_days='1일'\n"
        "4. [요일별 상세 슬롯]: '월요일 1교시는 피해줘' -> day='월요일', specific_time_slot='1교시', condition='피함'"
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