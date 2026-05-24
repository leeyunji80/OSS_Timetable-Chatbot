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

def generate_timetable_combinations(major_path, ge_path, slots, recommended_course_names):
    """
    슬롯 데이터를 바탕으로 필터링 후, 시각화 팀원에게 줄 핵심 3가지 정보(과목명, 강의실, 시간)만 추출
    """
    # 원래 있던 컴퓨터공학과 전공 데이터 로드
    df_major = pd.read_csv(major_path)
    df_ge = pd.read_csv(ge_path)
    
    
   # 2. 전공과 교양 데이터프레임을 하나로 통합
    df = pd.concat([df_major, df_ge], ignore_index=True)

    exclude_days = slots.get("exclude_days", [])
    target_credit = slots.get("target_credit") or 18  # 결측치 대비 기본값 설정
    avoid_time_slots = slots.get("avoid_time_slots", [])
    
    # 기본 결측치 채우기 및 전처리
    df['교과목명'] = df['교과목명'].fillna('')
    df['이수구분'] = df['이수구분'].fillna('')
    df['요일'] = df['요일'].fillna('')

    # 공강 요일이 있다면 원본 df에서 먼저 제거
    if exclude_days:
        for day in exclude_days:
            df = df[~df['요일'].str.contains(day)]
            
    filtered_df = df # 시간대 검사로 넘겨줄 베이스 데이터프레임 지정
   
   # 시간대 필터링
    filtered_rows = []

    for _, row in filtered_df.iterrows():

        remove_course = False

        parsed_slots = parse_day_and_period(
            row['요일'],
            row['교시']
        )

        for avoid_slot in avoid_time_slots:

            avoid_day = avoid_slot["day"]
            avoid_time = avoid_slot["time_range"]

            for slot in parsed_slots:

                # 같은 요일 검사
                if slot["day"] != avoid_day:
                    continue

                # 오전 검사
                if avoid_time == "오전":

                    if slot["start_period"] <= 3:
                        remove_course = True
                        break

                # 오후 검사
                elif avoid_time == "오후":

                    if slot["start_period"] >= 4:
                        remove_course = True
                        break

            if remove_course:
                break

        if not remove_course:
            filtered_rows.append(row)

    filtered_df = pd.DataFrame(filtered_rows)
            
    course_pool = []
    for _, row in filtered_df.iterrows():
        course_name = row['교과목명']
        is_ge = '교양' in row['이수구분']
        is_recommended = course_name in recommended_course_names
        
        # [필터] 교양이 아니면서(즉, 전공인데) 졸업 추천 필수과목 리스트에 없다면 패스
        if not is_ge and not is_recommended:
            continue

        time_slots = parse_day_and_period(row['요일'], row['교시'])
        
        course_pool.append({
            "name": course_name,
            "room": row['강의실'].split('(')[0] if pd.notna(row['강의실']) else "",
            "credit": int(row['학점']) if pd.notna(row['학점']) else 0,
            "time_slots": time_slots,
            "is_required": is_recommended  # 필수 과목인지 여부를 저장 (가중치용)
        })
        

    # combinations를 돌리기 전에 과목 순서를 완전히 무작위로 섞어버립니다.
    random.shuffle(course_pool)

    all_combinations = []

    for r in range(5, len(course_pool) + 1):

     for combo in combinations(course_pool, r):

         combo_list = list(combo)

         total_credit = sum(
            course["credit"]
            for course in combo_list
         )

         # 목표 학점 범위 검사
         if target_credit is not None:

            if total_credit < target_credit - 1:
                continue

            if total_credit > target_credit + 1:
                continue
           
        # 시간 충돌 검사
        # 시간 충돌 검사
         if is_valid_combination(combo_list):
             # 이 조합 안에 추천 전공과목이 몇 개나 섞여있는지 계산
             required_count = sum(1 for c in combo_list if c["is_required"])
             all_combinations.append({
                 "schedule": combo_list,
                 "required_count": required_count
             })

         # [추가] 딕셔너리 형태로 저장된 조합이 10개 이상 쌓이면 안쪽 루프 탈출
         if len(all_combinations) >= 10:
             break

     # [추가] 조합이 10개 이상 쌓이면 바깥쪽 루프도 탈출
     if len(all_combinations) >= 10:
         break

    # 추천 전공과목 개수가 많은 순서대로 내림차순 정렬
    all_combinations.sort(key=lambda x: x["required_count"], reverse=True)
    
    # 정렬된 결과에서 상위 10개의 시간표 데이터만 추출해서 반환
    return [item["schedule"] for item in all_combinations[:10]]

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

# 시간표 조합 함수 호출
timetable_results = generate_timetable_combinations(
    MAJOR_DATA_PATH,
    GE_DATA_PATH,
    slots_input,
    recommended_course_names=recommended_courses
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