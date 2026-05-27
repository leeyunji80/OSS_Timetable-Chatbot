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

def generate_timetable_combinations(
    recommended_major_courses,  # 1순위: 전공 추천 리스트
    needed_general_areas,       # 2순위: 부족 교양 분석 결과
    filtered_df,                # 전체 개설 강좌 데이터프레임
    target_credits,             # 목표 학점
    empty_days,                 # 공강 요일 리스트
    avoid_time_slots,           # 피하고 싶은 시간대
    user_preferences            # 사용자 성향
):
    major_pool = []
    ge_needed_pool = []  # 2순위 부족 교양만 따로 모음
    ge_normal_pool = []  # 3순위 일반 교양만 따로 모음
    
    assign_pref = user_preferences.get("assignment_preference")
    team_pref = user_preferences.get("team_preference") 
    
    if not isinstance(empty_days, list): empty_days = []
    if not isinstance(avoid_time_slots, list): avoid_time_slots = []
    if not isinstance(needed_general_areas, dict): needed_general_areas = {}
    recommended_major_set = set(recommended_major_courses) if recommended_major_courses else set()

    # -------------------------------------------------------------
    # [A] 1차 필터링 및 순위별 그룹 분리 (문제 1번 해결을 위한 정밀 분류)
    # -------------------------------------------------------------
    for _, row in filtered_df.iterrows():
        course_name = row['교과목명']
        is_ge = '교양' in str(row['이수구분'])
        is_recommended_major = (not is_ge) and (course_name in recommended_major_set)
        
        if not is_ge and not is_recommended_major:
            continue
            
        time_slots = parse_day_and_period(row['요일'], row['교시'])
        if not time_slots: 
            continue
            
        current_course = {
            "name": course_name,
            "time_slots": time_slots
        }
        
        # 공강 요일 조건 검사
        has_empty_day_conflict = False
        if empty_days:
            empty_slots = [{"day": d, "start_period": 1, "end_period": 9} for d in empty_days]
            has_empty_day_conflict = is_conflict(current_course, {"time_slots": empty_slots})
            
        # 피하고 싶은 시간대 조건 검사
        has_avoid_time_conflict = False
        if avoid_time_slots:
            avoid_slots = []
            for avoid in avoid_time_slots:
                start, end = (1, 4) if avoid["time_range"] == "오전" else (5, 9)
                avoid_slots.append({"day": avoid["day"], "start_period": start, "end_period": end})
            has_avoid_time_conflict = is_conflict(current_course, {"time_slots": avoid_slots})

        # 교양 과목 성향 필터링 (과제/팀플)
        if is_ge:
            if has_empty_day_conflict: 
                continue
            if assign_pref:
                current_load = evaluate_load(row)
                if assign_pref == "과제적음" and current_load in ["많다", "보통이다"]: continue
                if assign_pref == "과제많음" and current_load == "적다": continue
            if team_pref == "팀플없음":
                current_team = evaluate_team_project(row)
                if current_team == "많음": continue

        # 가산점 계산 및 룸 정보 파싱
        area_name = row.get('영역', '') if pd.notna(row.get('영역')) else ''
        subarea_name = row.get('세부영역', '') if pd.notna(row.get('세부영역')) else ''
        base_score = 0
        
        room_info = ""
        room_info = str(row['강의실']).split('(')[0]

        course_item = {
            "name": course_name, "room": room_info, "credit": int(row['학점']) if pd.notna(row['학점']) else 0,
            "time_slots": time_slots, "is_required": is_recommended_major,
            "area": area_name, "subarea": subarea_name, "base_score": base_score
        }

        # 소프트 패널티 적용
        if is_ge and has_avoid_time_conflict:
            course_item["base_score"] -= 300

        # 그룹별로 명확하게 바구니 쪼갬
        if is_recommended_major:
            if has_empty_day_conflict or has_avoid_time_conflict:
                course_item["base_score"] -= 100
            major_pool.append(course_item)
        elif is_ge:
            # 부족 교양 검사
            is_needed_ge = False
            if area_name in needed_general_areas:
                sub_info = needed_general_areas[area_name]
                if "총필요학점" in sub_info:
                    if subarea_name in sub_info.get("선택가능영역", []): is_needed_ge = True
                elif subarea_name in sub_info:
                    is_needed_ge = True
            
            if is_needed_ge:
                course_item["base_score"] += 1000
                ge_needed_pool.append(course_item)  # 2순위 부족 교양 바구니
            else:
                course_item["base_score"] += 10
                ge_normal_pool.append(course_item)  # 3순위 일반 교양 바구니

    # -------------------------------------------------------------
    # [B] 후보 풀 다변화 
    # -------------------------------------------------------------
    random.seed(random.randint(1, 10000)) # 실행할 때마다 결과가 바뀌도록 시드 유연화
    
    # 부족교양과 일반교양을 각각 랜덤하게 섞은 후 필요한 만큼 추출해서 후보군 중복 방지
    random.shuffle(ge_needed_pool)
    random.shuffle(ge_normal_pool)
    
    # 부족 교양은 최대한 많이(전체 혹은 최대 40개), 일반 교양은 빈자리 채우기용으로 20개만 셈플링
    sampled_ge_needed = ge_needed_pool[:40]
    sampled_ge_normal = ge_normal_pool[:20]
    
    # 교양 최종 풀은 '부족 교양'이 무조건 앞 순위를 차지하도록 합침
    ge_pool = sampled_ge_needed + sampled_ge_normal

    print("\n================ [필터링 결과 데이터 체크] ================")
    print(f"▶ 통과된 전공 과목 수: {len(major_pool)}개")
    print(f"▶ 통과된 부족 교양 수: {len(ge_needed_pool)}개 (후보 선발: {len(sampled_ge_needed)}개)")
    print(f"▶ 통과된 일반 교양 수: {len(ge_normal_pool)}개 (후보 선발: {len(sampled_ge_normal)}개)")
    print("============================================================\n")

    all_combinations = []
    found_enough = False

    # -------------------------------------------------------------
    # [C] 전공 우선 조합 알고리즘 
    # -------------------------------------------------------------
    max_major_r = min(len(major_pool), 8) 
    min_major_r = 1 if len(major_pool) > 0 else 0

    for major_r in range(max_major_r, min_major_r - 1, -1):
        if found_enough: break
        for major_combo in combinations(major_pool, major_r):
            major_combo_list = list(major_combo)
            
            # 전공끼리 시간표 겹치면 탈락
            if not is_valid_combination(major_combo_list):
                continue
                
            major_credits = sum(m["credit"] for m in major_combo_list)
            
            # -------------------------------------------------------------
            # 전공만으로 이미 목표 학점을 채운 완벽한 케이스 우선 처리
            # -------------------------------------------------------------
            if abs(major_credits - target_credits) <= 1:
                # 전공을 많이 들을수록 압도적인 점수를 부여 (개당 10,000점 가산)
                final_score = sum(m["base_score"] for m in major_combo_list) + (major_r * 10000)
                all_combinations.append({"schedule": major_combo_list, "final_score": final_score})
                
                # 전공으로 꽉 채웠으니 더 이상 교양을 붙일 필요가 없으므로 다음 전공 조합 탐색
                if len(all_combinations) >= 150:
                    found_enough = True
                    break
                continue
            
            # -------------------------------------------------------------
            # 전공을 넣고 학점이 모자라 교양을 붙여야 하는 케이스
            # -------------------------------------------------------------
            needed_credits = target_credits - major_credits
            
            # 교양 과목을 0개부터 최대 6개까지 붙일 수 있도록 범위 유연화
            for ge_r in range(0, min(len(ge_pool) + 1, 7)):
                for ge_combo in combinations(ge_pool, ge_r):
                    ge_combo_list = list(ge_combo)
                    ge_credits = sum(g["credit"] for g in ge_combo_list)
                    
                    # 학점 마진 체크 (허용 오차를 ±1에서 ±2로 살짝 넓혀 유연성 확보)
                    if abs((major_credits + ge_credits) - target_credits) > 2:
                        continue
                        
                    full_combo = major_combo_list + ge_combo_list
                    if not is_valid_combination(full_combo):
                        continue
                        
                    # 전공 개수에 비례한 강력한 가산점 배치 (전공 6개 조합이 무조건 이기도록)
                    final_score = sum(c["base_score"] for c in full_combo) + (major_r * 8000)
                    
                    # 부족 교양 영역 만족도 보너스 연산
                    achieved_tracker = {}
                    for course in ge_combo_list:
                        if any(neck["name"] == course["name"] for neck in ge_needed_pool):
                            a_name, s_name = course["area"], course["subarea"]
                            if a_name not in achieved_tracker:
                                achieved_tracker[a_name] = {"total": 0, "subareas": {}}
                            achieved_tracker[a_name]["total"] += course["credit"]
                            achieved_tracker[a_name]["subareas"][s_name] = achieved_tracker[a_name]["subareas"].get(s_name, 0) + course["credit"]

                    ge_bonus = 0
                    for a_name, req_info in needed_general_areas.items():
                        if a_name in achieved_tracker:
                            if "총필요학점" in req_info:
                                ge_bonus += min(achieved_tracker[a_name]["total"], req_info["총필요학점"]) * 200
                            else:
                                for s_name, needed_sub_credit in req_info.items():
                                    ge_bonus += min(achieved_tracker[a_name]["subareas"].get(s_name, 0), needed_sub_credit) * 200
                    
                    final_score += ge_bonus
                    all_combinations.append({"schedule": full_combo, "final_score": final_score})
                    
                    if len(all_combinations) >= 150: # 탐색 풀을 늘려 6개짜리 조합이 뒤늦게 나와도 잘리지 않게 함
                        found_enough = True
                        break
                if found_enough: break

    if all_combinations:
        # 점수 높은 순(전공 가득 + 부족교양 포함 + 성향 만족)으로 정렬하여 탑 3 반환
        all_combinations.sort(key=lambda x: x["final_score"], reverse=True)
        
        # 중복 결과 방지를 위해 과목 이름 셋으로 필터링하여 고유 대안 3개 추출
        unique_schedules = []
        seen_names = set()
        for item in all_combinations:
            names_str = ",".join(sorted([c["name"] for c in item["schedule"]]))
            if names_str not in seen_names:
                seen_names.add(names_str)
                unique_schedules.append(item["schedule"])
            if len(unique_schedules) == 3:
                break
        return unique_schedules
        
    return []

user_sentence = "시간표 추천해줘"

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

login_student_id = "20250001"
target_semester = 1 

# 파일에서 불러온 함수를 직접 실행해서 결과를 메모리에 얹습니다.
graduation_analysis = get_final_recommendations(
    student_id=login_student_id,
    target_semester=target_semester,
    students_json_data=students_list
)

# 최종 추천 과목 리스트 추출
recommended_majors = graduation_analysis.get("recommended_major_courses", [])
needed_general_areas = graduation_analysis.get("needed_general_areas", {})

# 1. 파일 경로에서 데이터를 읽어와 하나로 합쳐줍니다.
all_lectures_df = pd.concat([pd.read_csv(MAJOR_DATA_PATH), pd.read_csv(GE_DATA_PATH)], ignore_index=True)

user_preferences_input = {
    "assignment_preference": parsed_data.get("assignment_preference"),
    "conflict_resolution_rule": parsed_data.get("conflict_resolution_rule", "과목우선")
}

import re
raw_credit = slots_input.get("target_credit") 
if raw_credit:
    digit_match = re.search(r'\d+', str(raw_credit))
    target_credit_int = int(digit_match.group()) if digit_match else 18
else:
    target_credit_int = 18

# 2. 딕셔너리에 뭉쳐있던 인자들을 하나씩 풀어서 정확한 매개변수 이름으로 전달합니다.
timetable_results = generate_timetable_combinations(
    recommended_major_courses=recommended_majors,  # 1순위 전공 리스트 넘기기
    needed_general_areas=needed_general_areas,      # 2순위 부족 교양 딕셔너리 넘기기
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

if timetable_results:
    print("\n-------- [시각화 팀 전달용 최종 JSON 출력] --------")

    final_json_output = {
        "status": "success",
        "total_alternatives": len(timetable_results),
        "alternatives": []
    }

    # 최대 3개의 시간표 대안을 순회하며 JSON 구조를 생성
    for index, selected_schedule in enumerate(timetable_results):
        course_color_map = assign_course_colors(selected_schedule)
        
        # 1. 이 시간표의 특징을 분석하여 추천 사유(Reason)를 동적으로 생성
        
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

            matched_rows = all_lectures_df[all_lectures_df['교과목명'] == course["name"]]
            if not matched_rows.empty:
                course_row = matched_rows.iloc[0]
                load_status = evaluate_load(course_row)  # "많다", "보통이다", "적다"
                raw_ratio = pd.to_numeric(course_row.get('평가_과제(%)'), errors='coerce') or 0
            else:
                load_status = "정보 없음"
                raw_ratio = 0

            course_color = course_color_map[course["name"]]
            
            cleaned_courses.append({
                "name": course["name"],
                "room": course["room"],
                "credit": course["credit"],
                "is_required": course.get("is_required", False),
                # 임시 출력
                "assignment_load_test": load_status,         # "적다", "보통이다", "많다"
                "assignment_percentage_test": f"{raw_ratio}%", # "15.0%" 형태

                "background_color": course_color["background"],
                "text_color": course_color["text"],
                "time_slots": cleaned_slots
            })

        
        # 2. 요일별 오전/오후 회피 성공 여부 분석 및 추천 사유 생성
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