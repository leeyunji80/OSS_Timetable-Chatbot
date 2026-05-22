import pandas as pd
from itertools import combinations
import random

import importlib.util

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


def parse_day_and_period(day_raw, period_raw):
    """
    요일과 교시 문자열을 시각화 팀원이 가공 없이 바로 쓸 수 있게 텍스트와 숫자 형태로만 정제
    """
    if pd.isna(day_raw) or pd.isna(period_raw):
        return []
        
    PERIOD_TO_TIME = {
        0: ("08:00, 09:00"),
        1: ("09:00, 10:00"),
        2: ("10:00 , 11:00"),
        3: ("11:00, 12:00"),
        4: ("12:00, 13:00"),
        5: ("13:00, 14:00"),
        6: ("14:00, 15:00"),
        7: ("15:00, 16:00"),
        8: ("16:00, 17:00"),
        9: ("17:00, 18:00"),
        10: ("18:00, 19:00"),
        11: ("19:00, 20:00"),
        12: ("20:00, 21:00"),
        13: ("21:00, 22:00"),
        14: ("22:00, 23:00")
    }

    time_slots = []
    
    # 파이프(|)를 기준으로 다중 요일/교시 분할
    day_splits = str(day_raw).split('|')
    period_splits = str(period_raw).replace('"', '').split('|')
    
    for day_chunk, period_chunk in zip(day_splits, period_splits):
        day_str = day_chunk.strip()
        
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

def generate_timetable_combinations(major_path, ge_path, slots):
    """
    슬롯 데이터를 바탕으로 필터링 후, 시각화 팀원에게 줄 핵심 3가지 정보(과목명, 강의실, 시간)만 추출
    """
    # 원래 있던 컴퓨터공학과 전공 데이터 로드
    df_major = pd.read_csv(major_path)
    df_ge = pd.read_csv(ge_path)
    
    
    # 2. 전공과 교양 데이터프레임을 하나로 통합
    df = pd.concat([df_major, df_ge], ignore_index=True)

    target_grade = slots.get("target_grade")
    exclude_days = slots.get("exclude_days", [])
    num_to_pick = slots.get("num_to_pick")
    
    df['수강 대상'] = df['수강 대상'].fillna('')
    df['이수구분'] = df['이수구분'].fillna('')

    # 2. 조건 설정
    is_target_grade = df['수강 대상'].str.contains(target_grade)
    is_general_edu = df['이수구분'].str.contains('교양')
    is_not_night = ~df['수강 대상'].str.contains("야간")

    # 3. 필터링 (전공은 해당학년만, 교양은 무조건 합격 / 둘 다 야간은 제외)
    mask = (is_target_grade | is_general_edu) & is_not_night
    filtered_df = df[mask].copy()
    
    if exclude_days:
        for day in exclude_days:
            filtered_df = filtered_df[~filtered_df['요일'].str.contains(day, na=False)]
            
    course_pool = []
    for _, row in filtered_df.iterrows():
        time_slots = parse_day_and_period(row['요일'], row['교시'])

        assignment_status = evaluate_load(row)
        
        course_pool.append({
            "name": row['교과목명'],
            "room": row['강의실'].split('(')[0] if pd.notna(row['강의실']) else "",
            "time_slots": time_slots,
            "assignment": assignment_status  # "많다", "보통이다", "적다" 출력
        })
        

    # combinations를 돌리기 전에 과목 순서를 완전히 무작위로 섞어버립니다.
    random.shuffle(course_pool)

    all_combinations = []

    for combo in combinations(course_pool, num_to_pick):

       combo_list = list(combo)

    # 시간 충돌 없을 때만 추가
       if is_valid_combination(combo_list):
          all_combinations.append(combo_list)

    # 최대 10개만 저장
          if len(all_combinations) >= 10:
               break
    
    return [list(combo) for combo in all_combinations]

def generate_random_slots():

    grades = ["1학년", "2학년", "3학년", "4학년"]
    days = ["월", "화", "수", "목", "금"]
    counts = [3, 4, 5, 6]

    target_grade = random.choice(grades)

    exclude_days = random.sample(days, random.randint(1, 2))

    num_to_pick = random.choice(counts)

    # 실제 LLM이 추출했다고 가정하는 슬롯 데이터
    slots_input = {
        "target_grade": target_grade,
        "exclude_days": exclude_days,
        "num_to_pick": num_to_pick
    }

    return slots_input

# -----------------------------
# 랜덤 슬롯 생성
# -----------------------------

slots_input = generate_random_slots()

print("생성된 슬롯:")
print(slots_input)

# 함수 호출 결과
timetable_results = generate_timetable_combinations(MAJOR_DATA_PATH, GE_DATA_PATH, slots_input)

# 구조 확인용 프린트 (첫 번째 조합의 첫 번째 과목 데이터 형태)
if timetable_results:
    import json
    print("-------- 예시 출력 --------")
    for course in timetable_results[0]:

        print(json.dumps(course, ensure_ascii=False, indent=2))