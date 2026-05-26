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
from timetable_colors import assign_course_colors
from timetable_parser import parse_day_and_period

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

def evaluate_team_project(row):
    """
    강의계획서의 팀플 여부 판단
    - 많음 : 팀플 있음
    - 없음 : 팀플 없음
    """

    team_ratio = pd.to_numeric(row.get("방법_토의토론(%)"), errors='coerce') or 0

    # 팀플 관련 값이 있는 경우
    if team_ratio > 0:
        return "많음"

    return "없음"

def generate_timetable_combinations(recommended_major_courses,
    required_ge_areas, filtered_df, target_credits, empty_days, avoid_time_slots, user_preferences):

    required_ge_areas_cleaned = {
        str(area).strip(): credit
        for area, credit in required_ge_areas.items()
    }

    course_row_map = {
        row["교과목명"]: row
        for _, row in filtered_df.iterrows()
    }
    # 추천 과목 이름 추출
    recommended_course_names = set(recommended_major_courses)
    
    major_pool = []
    priority_ge_pool = []
    normal_ge_pool = []

    assign_pref = user_preferences.get("assignment_preference")     # "과제적음", "과제많음" 또는 None
    team_pref = user_preferences.get("team_project_preference")

    # 전체 데이터 프레임을 돌면서 전공(추천과목)과 교양을 분류하여 담습니다.
    for _, row in filtered_df.iterrows():
        is_priority_ge = False
        course_name = row['교과목명']
        is_ge = '교양' in row['이수구분']
        is_recommended = course_name in recommended_course_names
        
        major_category = str(
            row.get("교양대분류", "")
        ).strip()

        sub_category = str(
            row.get("교양소분류", "")
        ).strip()

        course_credit = int(row["학점"]) if pd.notna(row["학점"]) else 0


        # 전공 과목 처리
        if not is_ge:

            if not is_recommended:
                continue

        # 교양 과목 처리
        else:

            required_ge_areas_cleaned = {
                str(area).strip(): credit
                for area, credit in required_ge_areas.items()
            }

   

            remaining_credit = required_ge_areas_cleaned.get(
                sub_category,
                0
            )


            is_priority_ge = remaining_credit > 0
            

        if not is_recommended: # 필수/추천 전공 과목은 졸업을 위해 필터링 면제
            
            # 1. 기존에 만든 evaluate_load 함수 활용하기
            if assign_pref:
                # 현재 과목의 과제 양 판단 ("많다", "보통이다", "적다" 중 하나 반환)
                current_load = evaluate_load(row) 
                
                # 사용자가 과제 적은 걸 원하는데, "많다" 또는 "보통이다"가 나오면 패스
                if assign_pref == "과제적음" and current_load in ["많다", "보통이다"]:
                    continue
                
                # 사용자가 과제 많은 걸 원하는데, "적다"가 나오면 패스 (취향에 따라 보통이다도 패스 가능)
                if assign_pref == "과제많음" and current_load == "적다":
                    continue
            
            # 팀플 선호도 필터링
            if team_pref:

                current_team_status = evaluate_team_project(row)

                # 팀플 없는 수업 선호
                if team_pref == "팀플없음" and current_team_status == "많음":
                    continue

                # 팀플 있는 수업 선호
                if team_pref == "팀플많음" and current_team_status == "없음":
                    continue

        time_slots = parse_day_and_period(row['요일'], row['교시'])
        course_item = {
            "name": course_name,
            # 원본 코드의 '강의室' 혹은 '강의실' 컬럼 대응
            "room": row['강의室'].split('(')[0] if '강의室' in row and pd.notna(row['강의室']) else (row['강의실'].split('(')[0] if '강의실' in row and pd.notna(row['강의실']) else ""),
            "credit": int(row['학점']) if pd.notna(row['학점']) else 0,
            "time_slots": time_slots,
            "is_required": is_recommended,
            "is_priority_ge": is_priority_ge
        }
        
        if is_ge:

            if course_item["is_priority_ge"]:
                priority_ge_pool.append(course_item)

            else:
                normal_ge_pool.append(course_item)

        else:
            major_pool.append(course_item)

    if len(normal_ge_pool) > 30:

        normal_ge_pool = random.sample(
            normal_ge_pool,
            30
        )

    course_pool = (
    major_pool
    + priority_ge_pool
    + normal_ge_pool
    )
    #디버깅을 위한 출력
    print("\n===== 전공 과목 수 =====")
    print(len(major_pool))

    print("\n===== 부족 교양 과목 수 =====")
    print(len(priority_ge_pool))

    print("\n===== 일반 교양 과목 수 =====")
    print(len(normal_ge_pool))

    all_combinations = []
    
    MAX_ITERATIONS = 300000
    iteration_count = 0
    
    if target_credits >= 21:
        start_r = 6
    elif target_credits >= 18:
        start_r = 5
    else:
        start_r = 4
    # 조합 탐색 시작 
    max_r = min(start_r + 2, len(course_pool) + 1)

    for r in range(start_r, max_r):
        for combo in combinations(course_pool, r):
            iteration_count += 1
            
            # 탐색 횟수가 5만 번을 넘어가면 컴퓨터를 쉬게 하고 지금까지 찾은 최선의 조합을 반환합니다.
            if iteration_count > MAX_ITERATIONS:
                if all_combinations:
                    all_combinations.sort(key=lambda x: x["required_count"], reverse=True)
                    return [item["schedule"] for item in all_combinations[:3]]
                return []

            combo_list = list(combo)

            # -----------------------------
            # 부족 교양 학점 충족 여부 검사
            # -----------------------------
            ge_credit_progress = {
                area: 0
                for area in required_ge_areas_cleaned
            }

            for course in combo_list:

                if not course.get("is_priority_ge"):
                    continue

                course_name = course["name"]

                row = course_row_map.get(course_name)

                if row is None:
                   continue

                sub_category = str(
                    row.get("교양소분류", "")
                ).strip()

                ge_credit_progress[sub_category] += course["credit"]

             # 부족 학점 충족 여부 확인
            is_ge_requirement_satisfied = True

            for area, required_credit in required_ge_areas_cleaned.items():

                 if ge_credit_progress.get(area, 0) < required_credit:
                     is_ge_requirement_satisfied = False
                     break

            if not is_ge_requirement_satisfied:
                continue
            
            # 학점 총합 계산
            total_credits = sum(course["credit"] for course in combo_list)
            if total_credits != target_credits:
                continue

            # 시간표 충돌 및 공강 요일 검사
            if not is_valid_combination(combo_list):
                continue

            # 공강 요일 검사를 위해 이 조합에 포함된 요일들만 모읍니다.
            actual_days = {slot["day"] for course in combo_list for slot in course["time_slots"]}

            violates_empty_day = False
            for day in empty_days:
                if day in actual_days:
                    violates_empty_day = True
                    break
            
            if violates_empty_day:
                continue
           
            avoid_penalty = 0
            for course in combo_list:
                # 필수 과목은 오전에 듣든 오후에 듣든 페널티를 면제해 줍니다.
                if course.get("is_required", False):
                    continue

                for slot in course["time_slots"]:
                    for avoid in avoid_time_slots:
                        # 1단계: 사용자가 지정한 '요일'과 현재 수업의 '요일'이 일치하는지 확인
                        if slot["day"] == avoid["day"]:
                            
                            # 조건 A: 해당 요일에 '오전'을 피하고 싶을 때 (1~4교시 걸리면 페널티)
                            if avoid["time_range"] == "오전" and slot["start_period"] < 5:
                                avoid_penalty += 1
                            
                            # 조건 B: 해당 요일에 '오후'를 피하고 싶을 때 (5교시/13:00 이후 걸리면 페널티)
                            # 보통 5교시(13시)부터 대다수 오후 수업이 시작됩니다.
                            if avoid["time_range"] == "오후" and slot["start_period"] >= 5:
                                avoid_penalty += 1

            # 5. 필수 과목 개수 카운트
            required_count = sum(
                1 for course in combo_list
                if course["is_required"]
            )

            priority_ge_count = sum(
                 1 for course in combo_list
                 if course.get("is_priority_ge", False)
            )
            # 6. 유효한 시간표 조합 안전하게 딱 한 번만 저장 (페널티 포함)
            all_combinations.append({
                "schedule": combo_list,
                "required_count": required_count,
                "priority_ge_count": priority_ge_count,
                "avoid_penalty": avoid_penalty
            })

            # 7. 최적의 시간표 300개를 찾았다면 즉시 루프 종료 후 반환
            if len(all_combinations) >= 300:
                all_combinations.sort( key=lambda x: (
                    -x["required_count"],
                    -x["priority_ge_count"],
                     x["avoid_penalty"]
                ))
                return [item["schedule"] for item in all_combinations[:3]]

    # 8. 5만 번 탐색을 마쳤거나 전체 루프가 끝났을 때의 최종 정렬 반환
    if all_combinations:
        all_combinations.sort(key=lambda x: (
            -x["required_count"],
            -x["priority_ge_count"],
            x["avoid_penalty"]
        ))
        return [item["schedule"] for item in all_combinations[:3]]
        
    return []

user_sentence = "과제 적은 시간표 추천해줘"

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

login_student_id = "20240001"
target_semester = 1 

# 파일에서 불러온 함수를 직접 실행해서 결과를 메모리에 얹습니다.
graduation_analysis = get_final_recommendations(
    student_id=login_student_id,
    target_semester=target_semester,
    students_json_data=students_list
)

recommended_major_courses = graduation_analysis.get(
    "recommended_major_courses",
    []
)

required_ge_areas = graduation_analysis.get(
    "needed_general_areas",
    {}
)

print("추천 전공 과목:")
print(recommended_major_courses)

print("부족 교양 영역:")
print(required_ge_areas)

# 1. 파일 경로에서 데이터를 읽어와 하나로 합쳐줍니다.
all_lectures_df = pd.concat([pd.read_csv(MAJOR_DATA_PATH), pd.read_csv(GE_DATA_PATH)], ignore_index=True)
all_lectures_df.columns = (
    all_lectures_df.columns
    .str.strip()
)
print(all_lectures_df.columns.tolist())
print("===== 이수구분 종류 =====")
print(all_lectures_df["이수구분"].unique())
lecture_row_map = {
    row["교과목명"]: row
    for _, row in all_lectures_df.iterrows()
 }

user_preferences_input = {
    "assignment_preference": parsed_data.get("assignment_preference"),
    "team_project_preference": parsed_data.get("team_project_preference"),
    "conflict_resolution_rule": parsed_data.get("conflict_resolution_rule", "과목우선")

}

import re
raw_credit = slots_input.get("target_credit") # 단수형 키로 정확하게 매핑
if raw_credit:
    digit_match = re.search(r'\d+', str(raw_credit))
    target_credit_int = int(digit_match.group()) if digit_match else 18
else:
    target_credit_int = 18

# 2. 딕셔너리에 뭉쳐있던 인자들을 하나씩 풀어서 정확한 매개변수 이름으로 전달합니다.
timetable_results = generate_timetable_combinations(
    recommended_major_courses=recommended_major_courses,
    required_ge_areas=required_ge_areas,
    filtered_df=all_lectures_df,
    target_credits=target_credit_int,
    empty_days=slots_input["exclude_days"],
    avoid_time_slots=slots_input["avoid_time_slots"],
    user_preferences=user_preferences_input
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

assign_pref = parsed_data.get("assignment_preference")
team_pref = parsed_data.get("team_project_preference")

if timetable_results:
    print("\n-------- [시각화 팀 전달용 최종 JSON 출력] --------")

    final_json_output = {
        "status": "success",
        "total_alternatives": len(timetable_results),
        "alternatives": []
    }

    # 최대 3개의 시간표 대안을 순회하며 JSON 구조를 생성합니다.
    for index, selected_schedule in enumerate(timetable_results):
        course_color_map = assign_course_colors(selected_schedule)
        
        # 1. 이 시간표의 특징을 분석하여 추천 사유(Reason)를 동적으로 생성합니다.
        
        morning_course_count = 0
        total_credits_sum = 0
        required_course_names = []

        cleaned_courses = []
        for course in selected_schedule:
            total_credits_sum += course["credit"]
            if course.get("is_required"):
                required_course_names.append(course["name"])

            cleaned_slots = []
            for slot in course["time_slots"]:
                cleaned_slots.append({
                    "day": slot["day"],
                    "time_range": slot["time_range"],
                })
                # 오전 수업(5교시/13시 이전 시작) 개수 카운트
                if slot["start_period"] < 5:
                    morning_course_count += 1

           

            course_row = lecture_row_map.get(course["name"])

            if course_row is not None:
                load_status = evaluate_load(course_row)
                raw_ratio = pd.to_numeric(
                    course_row.get('평가_과제(%)'),
                    errors='coerce'
                ) or 0

                team_status = evaluate_team_project(course_row)

            else:
                load_status = "정보 없음"
                raw_ratio = 0
                team_status = "정보 없음"

            course_color = course_color_map[course["name"]]
            
            cleaned_courses.append({
                "name": course["name"],
                "room": course["room"],
                "credit": course["credit"],
                "is_required": course.get("is_required", False),
                # 임시 출력
                "assignment_load_test": load_status,         # "적다", "보통이다", "많다"
                "assignment_percentage_test": f"{raw_ratio}%", # "15.0%" 형태
                "team_project_status": team_status,

                "background_color": course_color["background"],
                "text_color": course_color["text"],
                "time_slots": cleaned_slots
            })

        
        # 2. 요일별 오전/오후 회피 성공 여부 분석 및 추천 사유(Reason) 생성
        reason_segments = []
        
        # [공강 요일 반영 여부 체크]
        actual_days = {slot["day"] for c in selected_schedule for slot in c["time_slots"]}
        achieved_empty_days = [day for day in exclude_days if day not in actual_days]
        if achieved_empty_days:
            reason_segments.append(f"{', '.join(achieved_empty_days)}요일 공강을 완벽히 확보했습니다.")

        if assign_pref:
            # 이 시간표 조합에 포함된 교양(is_required=False) 과목들의 과제 성향 확인
            ge_courses_in_schedule = [c for c in selected_schedule if not c.get("is_required")]
            
            if ge_courses_in_schedule:
                # 사용자가 과제 적은 걸 원했고, 실제로 교양 과목들이 다 잘 필터링 되었는지 검증
                if assign_pref == "과제적음":
                    reason_segments.append("과제 부담이 적은 교양 과목 위주로 구성된 시간표입니다.")
                elif assign_pref == "과제많음":
                    reason_segments.append("과제 비중이 있는 과목들로 구성되었습니다.")
       
        if team_pref:

            if team_pref == "팀플없음":
                reason_segments.append(
                    "팀 프로젝트 부담이 적은 과목 위주로 구성되었습니다."
                )

            elif team_pref == "팀플많음":
                reason_segments.append(
                    "협업 중심의 팀 프로젝트 과목이 포함되어 있습니다."
                )

        # 요일별 오전/오후 회피 성공 여부 체크
        avoid_success_days = []
        avoid_fail_details = []

        for avoid in avoid_time_slots:
            target_day = avoid["day"]
            target_range = avoid["time_range"]
            
            # 현재 시간표에서 해당 요일, 해당 시간대에 걸리는 수업이 있는지 확인
            is_violated = False
            for course in selected_schedule:
                for slot in course["time_slots"]:
                    if slot["day"] == target_day:
                        if target_range == "오전" and slot["start_period"] < 5:
                            is_violated = True
                        if target_range == "오후" and slot["start_period"] >= 5:
                            is_violated = True
            
            if not is_violated:
                avoid_success_days.append(f"{target_day}요일 {target_range}")
            else:
                avoid_fail_details.append(f"{target_day}요일 {target_range}")

        # 문장 엮기
        if avoid_success_days:
            reason_segments.append(f"요청하신 {', '.join(avoid_success_days)} 수업을 깔끔하게 피했습니다.")
        if avoid_fail_details:
            # 어쩔 수 없이 들어간 경우 안내 (페널티 기반이라 들어갈 수도 있음)
            reason_segments.append(f"다만 전체 학점 맞춤을 위해 {', '.join(avoid_fail_details)} 수업이 불가피하게 일부 포함되었습니다.")
        # -------------------------------------------------------------------------

        # [우선순위 추천 과목 체크]
        if required_course_names:
            reason_segments.append(f"우선순위가 높은 추천 과목({', '.join(required_course_names)})이 포함되어 있습니다.")

        # 최종 합치기
        recommendation_reason = " ".join(reason_segments)

        # 3. 개별 시간표 대안 구조화
        alternative_item = {
            "alternative_id": index + 1,
            "total_credits": total_credits_sum,
            "recommendation_reason": recommendation_reason,
            "courses": cleaned_courses
        }
        
        final_json_output["alternatives"].append(alternative_item)

    # 시각화 팀이 바로 복사해서 쓸 수 있도록 깔끔한 JSON 스트링으로 출력
    print(json.dumps(final_json_output, ensure_ascii=False, indent=2))

else:
    print(json.dumps({
        "status": "error",
        "message": "조건을 만족하는 시간표 조합을 찾지 못했습니다. 조건을 완화해 주세요."
    }, ensure_ascii=False, indent=2))