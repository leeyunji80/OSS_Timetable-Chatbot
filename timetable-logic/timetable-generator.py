import pandas as pd
import io
from itertools import combinations
import random

def parse_day_and_period(day_raw, period_raw):
    """
    요일과 교시 문자열을 시각화 팀원이 가공 없이 바로 쓸 수 있게 텍스트와 숫자 형태로만 정제
    """
    if pd.isna(day_raw) or pd.isna(period_raw):
        return []
        
    time_slots = []
    
    # 파이프(|)를 기준으로 다중 요일/교시 분할
    day_splits = str(day_raw).split('|')
    period_splits = str(period_raw).replace('"', '').split('|')
    
    for day_chunk, period_chunk in zip(day_splits, period_splits):
        day_str = day_chunk.strip()
        
        # 교시 문자열을 숫자로 변환 (예: "06" -> 6)
        periods = [int(p.strip()) for p in period_chunk.split(',') if p.strip().isdigit()]
        
        for p_num in periods:
            time_slots.append({
                "day": day_str,      # '월', '화', '수' 등 요일 텍스트
                "period": p_num      # 실제 교시 숫자 (예: 6)
            })
            
    return time_slots

def generate_timetable_combinations(file_path, slots):
    """
    슬롯 데이터를 바탕으로 필터링 후, 시각화 팀원에게 줄 핵심 3가지 정보(과목명, 강의실, 시간)만 추출
    """
    # 1. 파일에서 데이터 로드
    df = pd.read_csv(file_path)
    
    # 2. 자연어 슬롯 데이터 반영하여 필터링
    target_grade = slots.get("target_grade", "2학년")
    exclude_days = slots.get("exclude_days", [])
    num_to_pick = slots.get("num_to_pick", 5)
    
    # 기본 학년 필터링 (야간 강좌 제외)
    mask = df['수강 대상'].str.contains(target_grade) & ~df['수강 대상'].str.contains("야간")
    filtered_df = df[mask].copy()
    
    # 제외 요일 반영
    if exclude_days:
        for day in exclude_days:
            filtered_df = filtered_df[~filtered_df['요일'].str.contains(day, na=False)]
            
    # 3. 과목명, 강의실, 요일/교시 정보만 추출하여 풀(Pool) 구성
    course_pool = []
    for _, row in filtered_df.iterrows():
        time_slots = parse_day_and_period(row['요일'], row['교시'])
        
        course_pool.append({
            "name": row['교과목명'],                                         # 1. 과목명
            "room": row['강의실'].split('(')[0] if pd.notna(row['강의실']) else "", # 2. 강의실명
            "time_slots": time_slots                                        # 3. 요일 및 교시 (격자 제외)
        })
        
    # 4. 모든 과목 조합 생성 (충돌 검증 없이 리스트화)
    all_combinations = list(combinations(course_pool, num_to_pick))[:10]
    
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
timetable_results = generate_timetable_combinations("lectures.csv", slots_input)

# 구조 확인용 프린트 (첫 번째 조합의 첫 번째 과목 데이터 형태)
if timetable_results:
    import json
    print("--- 격자 인덱스가 제외된 최종 데이터 구조 샘플 ---")
    for course in timetable_results[0]:

        print(json.dumps(course, ensure_ascii=False, indent=2))