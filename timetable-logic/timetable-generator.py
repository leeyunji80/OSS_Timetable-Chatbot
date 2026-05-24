import pandas as pd
from itertools import combinations
import random

import importlib.util

from llm_api import parse_schedule_text
import os
from dotenv import load_dotenv
import json
# 테스트를 위한 임시 파일에서 함수를 불러옴
from condition import get_final_recommendations, students_list

load_dotenv()

MY_API_KEY = os.environ.get("OPENAI_API_KEY")

spec = importlib.util.spec_from_file_location(
    "check_overlap",
    "timetable-logic/check-overlap.py"
)

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

MAJOR_DATA_PATH = "data_processor/lectures_database.csv"
GE_DATA_PATH = "data_processor/liberal_arts.csv"

# -----------------------------
# 시간 충돌 검사
# -----------------------------

def is_conflict(course1, course2):

    for slot1 in course1["time_slots"]:
        for slot2 in course2["time_slots"]:

            same_day = slot1["day"] == slot2["day"]

            overlap = not (
                slot1["end_period"] < slot2["start_period"]
                or slot2["end_period"] < slot1["start_period"]
            )

            if same_day and overlap:
                return True

    return False


# -----------------------------
# 시간표 전체 충돌 검사
# -----------------------------

def is_valid_combination(schedule):

    for i in range(len(schedule)):
        for j in range(i + 1, len(schedule)):
            
            if schedule[i]["name"] == schedule[j]["name"]:
                return False

            if is_conflict(schedule[i], schedule[j]):
                return False

    return True

# -----------------------------
# 과목 색상 팔레트
# -----------------------------

COLOR_PALETTE = [
    {
        "background": "#FFCDD2",
        "text": "#000000"
    },
    {
        "background": "#F8BBD0",
        "text": "#000000"
    },
    {
        "background": "#E1BEE7",
        "text": "#000000"
    },
    {
        "background": "#D1C4E9",
        "text": "#000000"
    },
    {
        "background": "#C5CAE9",
        "text": "#000000"
    },
    {
        "background": "#BBDEFB",
        "text": "#000000"
    },
    {
        "background": "#B2EBF2",
        "text": "#000000"
    },
    {
        "background": "#C8E6C9",
        "text": "#000000"
    },
    {
        "background": "#DCEDC8",
        "text": "#000000"
    },
    {
        "background": "#FFF9C4",
        "text": "#000000"
    }
]


# -----------------------------
# 과목별 색상 지정
# -----------------------------

def assign_course_colors(schedule):

    course_color_map = {}

    for index, course in enumerate(schedule):

        color = COLOR_PALETTE[index % len(COLOR_PALETTE)]

        course_color_map[course["name"]] = color

    return course_color_map


def parse_day_and_period(day_raw, period_raw):
    """
    요일과 교시 문자열을 시각화 팀원이 가공 없이 바로 쓸 수 있게 텍스트와 숫자 형태로만 정제
    """
    if pd.isna(day_raw) or pd.isna(period_raw):
        return []
        
    PERIOD_TO_TIME = {
        0: ("08:00", "09:00"),
        1: ("09:00", "10:00"),
        2: ("10:00", "11:00"),
        3: ("11:00", "12:00"),
        4: ("12:00", "13:00"),
        5: ("13:00", "14:00"),
        6: ("14:00", "15:00"),
        7: ("15:00", "16:00"),
        8: ("16:00", "17:00"),
        9: ("17:00", "18:00"),
        10: ("18:00", "19:00"),
        11: ("19:00", "20:00"),
        12: ("20:00", "21:00"),
        13: ("21:00", "22:00"),
        14: ("22:00", "23:00")
    }

    time_slots = []
    
    # 파이프(|)를 기준으로 다중 요일/교시 분할
    day_splits = str(day_raw).split('|')
    period_splits = str(period_raw).replace('"', '').split('|')
    
    for day_chunk, period_chunk in zip(day_splits, period_splits):
        day_str = day_chunk.strip()
        
         # 1~3 형태 처리
        if '~' in period_chunk:

            start_period, end_period = map(
                int,
                period_chunk.split('~')
            )

            periods = list(range(start_period, end_period + 1))

        else:
            # 1,2,3 형태 처리
            periods = sorted([
                int(p.strip())
                for p in period_chunk.split(',')
                if p.strip().isdigit()
            ])

        if not periods:
            continue

        start_period = periods[0]
        end_period = periods[-1]

        start_time = PERIOD_TO_TIME[start_period][0]
        end_time = PERIOD_TO_TIME[end_period][1]

        time_slots.append({
            "day": day_str,
            "start_period": start_period,
            "end_period": end_period,
            "time_range": f"{start_time} ~ {end_time}"
        })

    return time_slots


def evaluate_load(row):
    """
    강의계획서의 '평가_과제(%)' 비율만 확인합니다.
    - 많다 : 40% 이상
    - 보통이다 : 20% 이상 ~ 40% 미만
    - 적다 : 20% 미만
    """
    # 결측치(NaN)나 예외 상황을 방지하기 위해 숫자로 안전하게 변환
    assignment_ratio = pd.to_numeric(row.get('평가_과제(%)'), errors='coerce') or 0
    
    # 오직 과제 비율 기준으로만 판단
    if assignment_ratio >= 40:
        return "많다"
    elif assignment_ratio >= 20:
        return "보통이다"
    else:
        return "적다"

def generate_timetable_combinations(recommended_courses_df, filtered_df, target_credits, empty_days):
    # 추천 과목 이름 추출
    recommended_course_names = set(recommended_courses_df)
    
    major_pool = []
    ge_pool = []

    # 전체 데이터 프레임을 돌면서 전공(추천과목)과 교양을 분류하여 담습니다.
    for _, row in filtered_df.iterrows():
        course_name = row['교과목명']
        is_ge = '교양' in row['이수구분']
        is_recommended = course_name in recommended_course_names
        
        # 전공 과목인데 추천 리스트에 없거나, 교양 과목이 아니면 건너뜁니다.
        if not is_ge and not is_recommended:
            continue

        time_slots = parse_day_and_period(row['요일'], row['교시'])
        course_item = {
            "name": course_name,
            # 원본 코드의 '강의室' 혹은 '강의실' 컬럼 대응
            "room": row['강의室'].split('(')[0] if '강의室' in row and pd.notna(row['강의室']) else (row['강의실'].split('(')[0] if '강의실' in row and pd.notna(row['강의실']) else ""),
            "credit": int(row['학점']) if pd.notna(row['학점']) else 0,
            "time_slots": time_slots,
            "is_required": is_recommended
        }
        
        if is_ge:
            ge_pool.append(course_item)
        else:
            major_pool.append(course_item)

    # ⭐ [수정 핵심]: 무한 루프(오랜 멈춤)를 방지하기 위해 교양 과목 풀을 최대 15개로 제한합니다.
    if len(ge_pool) > 15:
        ge_pool = random.sample(ge_pool, 15)

    # 전공 필수/추천 과목과 제한된 교양 과목을 합쳐서 최종 과목 풀을 만듭니다.
    course_pool = major_pool + ge_pool
    random.shuffle(course_pool)

    all_combinations = []
    
    # ⚠️ [수정 핵심 2]: 과도한 조합 연산으로 멈추는 것을 막기 위한 안전장치 추가
    MAX_ITERATIONS = 50000
    iteration_count = 0

    # 조합 탐색 시작 (4개 과목 조합부터 전체 과목 조합까지)
    for r in range(4, len(course_pool) + 1):
        for combo in combinations(course_pool, r):
            iteration_count += 1
            
            # 탐색 횟수가 5만 번을 넘어가면 컴퓨터를 쉬게 하고 지금까지 찾은 최선의 조합을 반환합니다.
            if iteration_count > MAX_ITERATIONS:
                if all_combinations:
                    all_combinations.sort(key=lambda x: x["required_count"], reverse=True)
                    return [item["schedule"] for item in all_combinations[:3]]
                return []

            combo_list = list(combo)
            
            # 학점 총합 계산
            total_credits = sum(course["credit"] for course in combo_list)
            if total_credits != target_credits:
                continue

            # 시간표 충돌 및 공강 요일 검사
            #  [새 코드] 지운 자리에 상단에 정의된 함수를 써서 딱 3줄만 넣으세요:
            # 이미 상단에 구현해 두신 전체 충돌 검사 함수를 그대로 활용합니다!
            if not is_valid_combination(combo_list):
                continue

            # 공강 요일 검사를 위해 이 조합에 포함된 요일들만 모읍니다.
            actual_days = {slot["day"] for course in combo_list for slot in course["time_slots"]}

            # 사용자가 지정한 공강 요일에 수업이 들어갔는지 검사
            violates_empty_day = False
            for day in empty_days:
                if day in actual_days:
                    violates_empty_day = True
                    break
            
            if violates_empty_day:
                continue

            # 추천(필수) 과목이 몇 개 포함되었는지 카운트
            required_count = sum(1 for course in combo_list if course["is_required"])

            # 유효한 시간표 조합 저장
            all_combinations.append({
                "schedule": combo_list,
                "required_count": required_count
            })

            # 최적의 시간표 3개를 찾았다면 즉시 루프를 종료하고 반환합니다.
            if len(all_combinations) >= 3:
                all_combinations.sort(key=lambda x: x["required_count"], reverse=True)
                return [item["schedule"] for item in all_combinations[:3]]

    # 모든 조합을 돌았는데 3개가 안 채워졌다면 있는 것만이라도 반환
    if all_combinations:
        all_combinations.sort(key=lambda x: x["required_count"], reverse=True)
        return [item["schedule"] for item in all_combinations[:3]]
        
    return []

user_sentence = "목요일 공강이고 오전 수업은 피하고 싶어"

json_result = parse_schedule_text(user_sentence, MY_API_KEY)

parsed_data = json.loads(json_result)

print("LLM 분석 결과:")
print(json.dumps(parsed_data, ensure_ascii=False, indent=2))

exclude_days = []
avoid_time_slots = []

for slot in parsed_data["slots"]:

    day = slot["day"].replace("요일", "")

    # 공강 처리
    if slot["condition"] == "공강":

       day = slot["day"].replace("요일", "")

       if day not in exclude_days:
           exclude_days.append(day)

       continue

    # 특정 시간대 피하기 처리
    if slot["condition"] == "피함":

        avoid_time_slots.append({
            "day": day,
            "time_range": slot["time_range"]
        })

slots_input = {
    "target_grade": parsed_data.get("target_grade"),
    "exclude_days": exclude_days,
    "target_credit": parsed_data.get("target_credit"),
    "avoid_time_slots": avoid_time_slots
}

# ... (LLM 분석 및 slots_input 정제 완료 후) ...

login_student_id = "20210001"
target_semester = 1 

# 파일에서 불러온 함수를 직접 실행해서 결과를 메모리에 얹습니다.
graduation_analysis = get_final_recommendations(
    student_id=login_student_id,
    target_semester=target_semester,
    students_json_data=students_list
)

# 최종 추천 과목 리스트 추출
recommended_courses = graduation_analysis.get("recommended_courses", [])

# 1. 파일 경로에서 데이터를 읽어와 하나로 합쳐줍니다.
all_lectures_df = pd.concat([pd.read_csv(MAJOR_DATA_PATH), pd.read_csv(GE_DATA_PATH)], ignore_index=True)

# 2. 딕셔너리에 뭉쳐있던 인자들을 하나씩 풀어서 정확한 매개변수 이름으로 전달합니다.
timetable_results = generate_timetable_combinations(
    recommended_courses_df=recommended_courses,
    filtered_df=all_lectures_df,
    target_credits=slots_input["target_credit"] if slots_input["target_credit"] else 18,
    empty_days=slots_input["exclude_days"]
)

if timetable_results:
    print("-------- 예시 출력 --------")

    clean_result = []

    selected_schedule = timetable_results[0]

    course_color_map = assign_course_colors(
        selected_schedule
    )


    for course in selected_schedule:

        cleaned_slots = []

        for slot in course["time_slots"]:
            cleaned_slots.append({
                "day": slot["day"],
                "time_range": slot["time_range"]
            })

        course_color = course_color_map[
            course["name"]
        ]

        clean_course = {
            "name": course["name"],
            "room": course["room"],
            "time_slots": cleaned_slots,
             "background_color": course_color["background"],
            "text_color": course_color["text"],
        }

        clean_result.append(clean_course)

    print(json.dumps(clean_result, ensure_ascii=False, indent=2))

    print("exclude_days =", exclude_days)
print("avoid_time_slots =", avoid_time_slots)