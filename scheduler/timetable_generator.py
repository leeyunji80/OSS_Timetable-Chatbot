import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import pandas as pd
from itertools import combinations
import random

# from llm.llm_api import parse_schedule_text

from dotenv import load_dotenv

from scheduler.course_recommender import get_final_recommendations, students_list
from scheduler.timetable_colors import assign_course_colors
from scheduler.timetable_parser import parse_day_and_period
from scheduler.check_overlap import is_conflict, is_valid_combination

load_dotenv()




MAJOR_DATA_PATH = os.path.join(BASE_DIR, 'data', 'lectures_database.csv')
GE_DATA_PATH = os.path.join(BASE_DIR, 'data', 'liberal_arts.csv')


def matches_specific_period(course_slot, condition_slot):
    """
    강의 시간 slot이 사용자가 지정한 특정 교시 조건과 겹치는지 검사
    """
    if course_slot["day"] != condition_slot["day"]:
        return False

    specific_slots = condition_slot.get("specific_time_slot")

    if not specific_slots:
        return False

    for period in specific_slots:
        if course_slot["start_period"] <= period <= course_slot["end_period"]:
            return True

    return False



def evaluate_load(row):
    """
    강의계획서의 '평가_과제(%)' 비율만 확인합니다.
    - 많다 : 20% 초과
    - 적다 : 20% 이하
    """
    # 결측치(NaN)나 예외 상황을 방지하기 위해 숫자로 안전하게 변환
    assignment_ratio = pd.to_numeric(row.get('평가_과제(%)'), errors='coerce') or 0
    
    # 오직 과제 비율 기준으로만 판단
    if assignment_ratio > 20:
        return "많다"
    else:
        return "적다"

def evaluate_team_project(row):
    """
    강의계획서의 팀플 여부 판단
    - 있음 : 팀플 있음
    - 없음 : 팀플 없음
    """

    team_ratio = pd.to_numeric(row.get("방법_토의토론(%)"), errors='coerce') or 0

    # 팀플 관련 값이 있는 경우
    if team_ratio > 0:
        return "있음"

    return "없음"


def make_user_request_title(parsed_data):
    title_parts = []

    for slot in parsed_data.get("slots", []):
        day = str(slot.get("day", "")).replace("요일", "")
        condition = slot.get("condition")
        time_range = slot.get("time_range")
        specific_time_slot = normalize_specific_time(slot)

        if condition == "공강" and day:
            title_parts.append(f"{day}요일 공강")
            continue

        if condition == "피함":
            if day and specific_time_slot:
                title_parts.append(f"{day}요일 {','.join(map(str, specific_time_slot))}교시 피함")
            elif day and time_range:
                title_parts.append(f"{day}요일 {time_range} 피함")
            elif time_range:
                title_parts.append(f"{time_range} 피함")
            continue

        if condition == "선호":
            if day and specific_time_slot:
                title_parts.append(f"{day}요일 {','.join(map(str, specific_time_slot))}교시 선호")
            elif day and time_range:
                title_parts.append(f"{day}요일 {time_range} 선호")
            elif time_range:
                title_parts.append(f"{time_range} 선호")

    if parsed_data.get("assignment_preference"):
        title_parts.append(parsed_data["assignment_preference"])

    if parsed_data.get("team_project_preference"):
        title_parts.append(parsed_data["team_project_preference"])

    if parsed_data.get("target_credit"):
        title_parts.append(str(parsed_data["target_credit"]))

    if parsed_data.get("course_priority"):
        title_parts.append(parsed_data["course_priority"])

    for course_name in parsed_data.get("selected_courses", []):
        title_parts.append(course_name)

    unique_parts = []
    for part in title_parts:
        if part and part not in unique_parts:
            unique_parts.append(part)

    if unique_parts:
        return " · ".join(unique_parts[:3]) + " 시간표"

    return "추천 시간표"



def normalize_specific_time(slot):
    raw = slot.get("specific_time_slot")

    if not raw:
        return None

    # 이미 리스트면 통과
    if isinstance(raw, list):
        return [int(x) for x in raw]

    # "1,2,3교시" or "1,2,3"
    import re
    nums = re.findall(r"\d+", str(raw))

    return [int(n) for n in nums] if nums else None

def exceeds_needed_general_credits(ge_courses, needed_general_areas):
    achieved_tracker = {}

    for course in ge_courses:
        if not course.get("is_needed_ge", False):
            continue

        area_name = course.get("area")
        subarea_name = course.get("subarea")

        if not area_name:
            continue

        if area_name not in achieved_tracker:
            achieved_tracker[area_name] = {"total": 0, "subareas": {}}

        credit = course.get("credit", 0)
        achieved_tracker[area_name]["total"] += credit

        if subarea_name:
            subareas = achieved_tracker[area_name]["subareas"]
            subareas[subarea_name] = subareas.get(subarea_name, 0) + credit

    for area_name, achieved in achieved_tracker.items():
        req_info = needed_general_areas.get(area_name)

        if not isinstance(req_info, dict):
            continue

        if "총필요학점" in req_info:
            if achieved["total"] > req_info["총필요학점"]:
                return True
            continue

        for subarea_name, needed_credit in req_info.items():
            achieved_credit = achieved["subareas"].get(subarea_name, 0)
            if achieved_credit > needed_credit:
                return True

    return False

def generate_timetable_combinations(
    recommended_major_courses,  # 1순위: 전공 추천 리스트
    needed_general_areas,       # 2순위: 부족 교양 분석 결과
    missing_required_major_courses,
    filtered_df,                # 전체 개설 강좌 데이터프레임
    target_credits,             # 목표 학점
    empty_days,                 # 공강 요일 리스트
    avoid_time_slots,           # 피하고 싶은 시간대
    preferred_time_slots,
    user_preferences,            # 사용자 성향
    mode="user_priority"
):
    major_pool = []
    ge_needed_pool = []  # 2순위 부족 교양만 따로 모음
    missing_required_pool = []   # 3순위: 이전 학년 미이수 전공필수
    ge_normal_pool = []  # 4순위 일반 교양만 따로 모음
    
    assign_pref = user_preferences.get("assignment_preference")
    team_pref = user_preferences.get("team_preference") 

    selected_course_set = set(
        user_preferences.get("selected_courses", [])
    )

    excluded_course_set = set(
        user_preferences.get("excluded_courses", [])
    )

    
        
    
    
    if not isinstance(empty_days, list): empty_days = []
    if not isinstance(avoid_time_slots, list): avoid_time_slots = []
    if not isinstance(needed_general_areas, dict): needed_general_areas = {}
    if not isinstance(missing_required_major_courses, list): missing_required_major_courses = []
    recommended_major_set = set(recommended_major_courses) if recommended_major_courses else set()
    missing_required_set = set(missing_required_major_courses) if missing_required_major_courses else set()
    FORCED_GE_BY_SUBAREA = {"사회와역사": "공업법규와창업"}

    # -------------------------------------------------------------
    # [A] 1차 필터링 및 순위별 그룹 분리
    # -------------------------------------------------------------
    for _, row in filtered_df.iterrows():
        course_name = row['교과목명']
        is_ge = '교양' in str(row['이수구분'])
        target_text = str(row.get("수강 대상", ""))

        if "야간학생강좌" in target_text:
            continue

        if course_name in excluded_course_set:

            # user_priority에서는 제거
            if mode == "user_priority":
                continue

            # graduation_priority에서는
            # 추천 전공이면 살림
            if mode == "graduation_priority":

                if course_name not in recommended_major_set:
                    continue

        is_selected_course = (
            course_name in selected_course_set
        )

        # -------------------------------------------------
        # 전공 과목 분류
        # 1순위: 해당 학년 추천 전공
        # 3순위: 이전 학년 미이수 전공필수
        # -------------------------------------------------

        if mode == "user_priority":
            is_current_grade_major = (
                (not is_ge)
                and
                (
                    course_name in recommended_major_set
                    or is_selected_course
                )
            )
        else:
            is_current_grade_major = (
                (not is_ge)
                and
                (
                    course_name in recommended_major_set
                )
            )

        # 해당 학년 추천 전공이 아닌 경우에만
        # 미이수 전공필수 후보로 분류
        is_missing_required_major = (
            (not is_ge)
            and
            (not is_current_grade_major)
            and
            (course_name in missing_required_set)
        )

        is_recommended_major = (
            is_current_grade_major
            or is_missing_required_major
        )

        if not is_ge and not is_current_grade_major and not is_missing_required_major:
            continue

        if course_name in selected_course_set:
            print(f"[선택과목 발견] {course_name}")
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
                specific_slots = avoid.get("specific_time_slot")
                time_range = avoid.get("time_range")
                day = avoid.get("day")

                # 1순위: specific_time_slot이 있으면 해당 교시 피하기
                if specific_slots:
                    for period in specific_slots:
                        avoid_slots.append({
                            "day": day,
                            "start_period": int(period),
                            "end_period": int(period)
                        })

                # 2순위: specific_time_slot이 없고 오전/오후 조건만 있으면 범위로 처리
                elif time_range == "오전":
                    avoid_slots.append({
                        "day": day,
                        "start_period": 1,
                        "end_period": 4
                    })

                elif time_range == "오후":
                    avoid_slots.append({
                        "day": day,
                        "start_period": 5,
                        "end_period": 9
                    })

            has_avoid_time_conflict = is_conflict(
                current_course,
                {"time_slots": avoid_slots}
            )

        # -------------------------------------------------
        # 교양 과목은 공강/시간 회피 조건을 강하게 적용
        # -------------------------------------------------
        if is_ge:
            if has_empty_day_conflict:
                continue

            if has_avoid_time_conflict:
                continue


        # -------------------------------------------------
        # 과제/팀플 성향 필터링
        # 전공/교양 모두에 적용
        # 단, user_priority 모드에서만 강하게 필터링
        # -------------------------------------------------
        if mode == "user_priority":

            if assign_pref:
                current_load = evaluate_load(row)

                # 과제 적은 강의를 원하면, 과제 많음 과목 제외
                if assign_pref == "과제적음" and current_load in ["많다"]:
                    continue

                # 과제 많은 강의를 원하면, 과제 적은 과목 제외
                if assign_pref == "과제많음" and current_load == "적다":
                    continue

            if team_pref == "팀플없음":
                current_team = evaluate_team_project(row)

                if current_team == "있음":
                    continue

        # 가산점 계산 및 룸 정보 파싱
        area_name = str(row.get('교양대분류', '')).strip() if pd.notna(row.get('교양대분류')) else ''
        subarea_name = str(row.get('교양소분류', '')).strip() if pd.notna(row.get('교양소분류')) else ''
        base_score = 0
        
        # 사용자가 직접 선택한 과목 우선 반영
        if course_name in selected_course_set:

            if mode == "user_priority":
                base_score += 200000

            else:  # graduation_priority
                base_score += 1000
        
        room_info = ""
        room_info = str(row['강의실']).split('(')[0]

        assignment_load = evaluate_load(row)
        team_project = evaluate_team_project(row)

        course_item = {
            "name": course_name, "room": room_info, "credit": int(row['학점']) if pd.notna(row['학점']) else 0,
            "time_slots": time_slots, "is_required": is_recommended_major,"is_current_grade_major": is_current_grade_major,
            "is_missing_required_major": is_missing_required_major,
            "area": area_name, "subarea": subarea_name, "base_score": base_score,
            "assignment_load": assignment_load, "team_project": team_project
        }

        if has_avoid_time_conflict:
            if mode == "user_priority":
                course_item["base_score"] -= 5000
            else:
                course_item["base_score"] -= 1000

        # 선호 시간대 / 특정 교시 가산점
        if preferred_time_slots:

            for pref in preferred_time_slots:
                for slot in time_slots:

                    if slot["day"] != pref["day"]:
                        continue

                    # 1순위: 구체적인 교시 선호
                    if pref.get("specific_time_slot"):
                        if matches_specific_period(slot, pref):
                            course_item["base_score"] += 1500
                        else:
                            print(f"[DEBUG] 교시 미스매치: {slot} vs {pref}")
                        continue

                    # 2순위: 오전/오후 선호
                    if pref.get("time_range") == "오전" and slot["start_period"] < 5:
                        course_item["base_score"] += 500

                    if pref.get("time_range") == "오후" and slot["start_period"] >= 5:
                        course_item["base_score"] += 500

        # 그룹별로 명확하게 바구니 쪼갬
        if is_recommended_major:

            # -------------------------------------------------
            # graduation_priority:
            # 추천 전공은 공강/시간회피 조건 무시
            # -------------------------------------------------
            if mode == "graduation_priority":

                if is_current_grade_major:
                    major_pool.append(course_item)
                elif is_missing_required_major:
                    missing_required_pool.append(course_item)

            # -------------------------------------------------
            # user_priority:
            # 사용자 조건 적극 반영
            # -------------------------------------------------
            else:

                rule = user_preferences.get(
                    "conflict_resolution_rule",
                    "과목우선"
                )

                if rule == "공강우선":

                    if has_empty_day_conflict:
                        continue

                    if has_avoid_time_conflict:
                        continue

                elif rule == "균형추천":

                    if has_empty_day_conflict:
                        course_item["base_score"] -= 500

                    if has_avoid_time_conflict:
                        course_item["base_score"] -= 300

                else:
                    if has_empty_day_conflict:
                        course_item["base_score"] -= 100

                    if has_avoid_time_conflict:
                        continue

                if is_current_grade_major:
                    major_pool.append(course_item)
                elif is_missing_required_major:
                    missing_required_pool.append(course_item)
            
        elif is_ge:
            # 부족 교양 검사 (데이터 구조에 구애받지 않는 안전한 유효성 체크)
            is_needed_ge = False
            
            # 1. 대영역(area_name)이 부족 교양 딕셔너리의 Key에 존재하는지 확인
            if area_name and area_name in needed_general_areas:
                sub_info = needed_general_areas[area_name]
                
                # 시나리오 A: 딕셔너리 구조가 {'총필요학점': X, '선택가능영역': [...]} 일 때
                if isinstance(sub_info, dict) and "총필요학점" in sub_info:
                    # 선택가능영역 리스트에 들어있거나, 세부영역 정보가 아예 비어있으면 영역 매칭으로 인정
                    if subarea_name in sub_info.get("선택가능영역", []) or not sub_info.get("선택가능영역"):
                        is_needed_ge = True
                        
                # 시나리오 B: 딕셔너리 구조가 {'세부영역명': 부족학점} 일 때
                elif isinstance(sub_info, dict):
                    if subarea_name in sub_info:
                        is_needed_ge = True
                        
                # 시나리오 C: sub_info가 단순히 세부영역 이름들을 담은 리스트일 때
                elif isinstance(sub_info, list):
                    if subarea_name in sub_info:
                        is_needed_ge = True
            
            # 2. 예외 방지: 대영역이 아니라 세부영역 이름 자체가 대항목 Key로 바로 들어가 있는 경우 구제
            if not is_needed_ge and subarea_name in needed_general_areas:
                is_needed_ge = True

            if is_needed_ge and subarea_name in FORCED_GE_BY_SUBAREA:
                forced_course_name = FORCED_GE_BY_SUBAREA[subarea_name]

                if course_name != forced_course_name:
                    is_needed_ge = False

            # 판정 결과에 따른 바구니 배정
            if is_needed_ge:
                course_item["base_score"] += 2000  # 우선순위 가산점 대폭 상향
                ge_needed_pool.append(course_item)  # 부족 교양 바구니로 정상 분류
            else:
                course_item["base_score"] += 10
                ge_normal_pool.append(course_item)  # 일반 교양 바구니

    # -------------------------------------------------------------
    # [B] 후보 풀 다변화 
    # -------------------------------------------------------------
    # 객체 비교 오류를 방지하기 위해, 부족 교양 과목들에 명시적 마킹을 부여합니다.
    for item in ge_needed_pool:
        item["is_needed_ge"] = True
    for item in ge_normal_pool:
        item["is_needed_ge"] = False
    for item in missing_required_pool:
        item["is_needed_ge"] = False
        item["is_missing_required_major"] = True

    # 실행할 때마다 다양한 시간표를 보기 위해 셔플하되, 부족 교양이 항상 최우선 배치되도록 합니다.
    random.seed(random.randint(1, 10000))
    random.shuffle(ge_needed_pool)
    random.shuffle(missing_required_pool)
    random.shuffle(ge_normal_pool)
    
    # 부족 교양은 유실되면 안 되므로 최대한 넉넉히 담고, 일반 교양은 빈자리 메우기용으로만 제한합니다.
    sampled_ge_needed = ge_needed_pool[:25]  
    sampled_missing_required = missing_required_pool[:10]
    forced_ge_courses = []

    for course in ge_normal_pool:
        if course["name"] in selected_course_set:
            forced_ge_courses.append(course)

    sampled_ge_normal = []

    added = set()

    for course in forced_ge_courses:
        sampled_ge_normal.append(course)
        added.add(course["name"])

    for course in ge_normal_pool:
        if course["name"] in added:
            continue

        sampled_ge_normal.append(course)

        if len(sampled_ge_normal) >= 5:
            break
    
    # 최종 교양 풀 구성
    ge_pool = sampled_ge_needed + sampled_missing_required + sampled_ge_normal

    print("\n================ [필터링 결과 데이터 체크] ================")
    print(f"▶ 통과된 전공 과목 수: {len(major_pool)}개")
    print(f"▶ 통과된 부족 교양 수: {len(ge_needed_pool)}개 (후보 선발: {len(sampled_ge_needed)}개)")
    print(f"▶ 통과된 미이수 전공필수 수: {len(missing_required_pool)}개 (후보 선발: {len(sampled_missing_required)}개)")
    print(f"▶ 통과된 일반 교양 수: {len(ge_normal_pool)}개 (후보 선발: {len(sampled_ge_normal)}개)")
    print("============================================================\n")

    all_combinations = []

    # -------------------------------------------------------------
    # [C] 전공 우선 조합 알고리즘 (수정본: 조기종료 제거 및 힙 격하 방지)
    # -------------------------------------------------------------
    max_major_r = min(len(major_pool), 8) 
    min_major_r = 1 if len(major_pool) > 0 else 0

    for major_r in range(max_major_r, min_major_r - 1, -1):
        for major_combo in combinations(major_pool, major_r):
            major_combo_list = list(major_combo)
            
            # 전공끼리 시간표 겹치면 무조건 탈락
            if not is_valid_combination(major_combo_list):
                continue
                
            major_credits = sum(m["credit"] for m in major_combo_list)
            
            if mode == "graduation_priority":
                major_weight = 60000
            else:
                major_weight = 8000
            
            # 전공만으로 이미 목표 학점을 채운 경우
            if abs(major_credits - target_credits) <= 1:

                if mode == "user_priority":
                    full_course_names = {c["name"] for c in major_combo_list}
                    selected_courses = set(user_preferences.get("selected_courses", []))

                    if not selected_courses.issubset(full_course_names):
                        continue


                final_score = (
                    sum(c["base_score"] for c in major_combo_list)
                    + (major_r * major_weight)
                )
                all_combinations.append({"schedule": major_combo_list, "final_score": final_score})
                continue
            
            # 전공 고정 후 교양 과목 조합 매칭
            for ge_r in range(1, min(len(ge_pool) + 1, 6)):
                for ge_combo in combinations(ge_pool, ge_r):
                    ge_combo_list = list(ge_combo)
                    ge_credits = sum(g["credit"] for g in ge_combo_list)
                    
                    # 학점 마진 체크 (목표 학점 대조)
                    if abs((major_credits + ge_credits) - target_credits) > 2:
                        continue
                        
                    full_combo = major_combo_list + ge_combo_list
                    if not is_valid_combination(full_combo):
                        continue

                    if exceeds_needed_general_credits(ge_combo_list, needed_general_areas):
                        continue

                    # 사용자가 직접 선택한 과목은 반드시 포함
                    selected_courses = set(
                    user_preferences.get("selected_courses", [])
                    )

                    full_course_names = {
                        c["name"] for c in full_combo
                    }
                    if mode == "user_priority":
                        if not selected_courses.issubset(full_course_names):
                            continue
                        
                    if mode == "graduation_priority":
                        major_weight = 60000
                        needed_ge_weight = 15000


                    else:  # user_priority
                        major_weight = 8000
                        needed_ge_weight = 5000

                    if mode == "user_priority":

                        final_score = (
                            sum(c["base_score"] for c in full_combo)
                            + (major_r * major_weight)
                        )

                        # 사용자가 선택한 과목 매우 강하게 우대
                        selected_count = sum(
                            1 for c in full_combo
                            if c["name"] in selected_course_set
                        )

                        final_score += selected_count * 500000

                        missing_required_count = sum(
                            1 for c in full_combo
                            if c.get("is_missing_required_major", False)
                        )

                        final_score += missing_required_count * 6000
                    

                    else:  # graduation_priority
                        needed_ge_count = sum(
                            1 for c in ge_combo_list
                            if c.get("is_needed_ge", False)
                        )
                        missing_required_count = sum(
                            1 for c in ge_combo_list
                            if c.get("is_missing_required_major", False)
                        )

                        missing_required_weight = 12000

                        final_score = (
                            sum(c["base_score"] for c in full_combo)
                            + (major_r * major_weight)
                            + (needed_ge_count * needed_ge_weight)
                            + (missing_required_count * missing_required_weight)
                        )



                    # 부족 교양 영역 만족도 보너스 연산 (플래그 기반으로 정확하게 수정)
                    achieved_tracker = {}
                    for course in ge_combo_list:
                        if course.get("is_needed_ge", False):  # 마킹된 플래그 조건으로 명확하게 검사
                            a_name, s_name = course["area"], course["subarea"]
                            if a_name not in achieved_tracker:
                                achieved_tracker[a_name] = {"total": 0, "subareas": {}}
                            achieved_tracker[a_name]["total"] += course["credit"]
                            achieved_tracker[a_name]["subareas"][s_name] = achieved_tracker[a_name]["subareas"].get(s_name, 0) + course["credit"]

                    ge_bonus = 0
                    for a_name, req_info in needed_general_areas.items():

                        if a_name not in achieved_tracker:
                            continue

                        # -----------------------------
                        # 모드별 가산점 배율
                        # -----------------------------
                        if mode == "graduation_priority":
                            bonus_multiplier = 4000


                        else:  # user_priority
                            bonus_multiplier = 1000

                        # -----------------------------
                        # 트랙 2 구조
                        # -----------------------------
                        if "총필요학점" in req_info:

                            ge_bonus += min(
                                achieved_tracker[a_name]["total"],
                                req_info["총필요학점"]
                            ) * bonus_multiplier

                        # -----------------------------
                        # 트랙 1 구조
                        # -----------------------------
                        else:

                            for s_name, needed_sub_credit in req_info.items():

                                ge_bonus += min(
                                achieved_tracker[a_name]["subareas"].get(s_name, 0),
                                needed_sub_credit
                                ) * bonus_multiplier
                    
                    final_score += ge_bonus
                    all_combinations.append({"schedule": full_combo, "final_score": final_score})
                    
        # 조기 종료(found_enough)를 제거하는 대신, 메모리 과부하를 방지하기 위해 
        # 대형 루프가 한 번 끝날 때마다 점수 순으로 상위 300개만 남기고 슬라이싱합니다.
        if len(all_combinations) > 500:
            all_combinations.sort(key=lambda x: x["final_score"], reverse=True)
            all_combinations = all_combinations[:300]

    selected_courses = set(user_preferences.get("selected_courses", []))

    if mode == "user_priority" and selected_courses:

        valid_combinations = []

        for item in all_combinations:

            names = {
                c["name"]
                for c in item["schedule"]
            }

            if selected_courses.issubset(names):
                valid_combinations.append(item)

        all_combinations = valid_combinations

    if not all_combinations:
        return []



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
        if all_combinations:
            all_combinations.sort(
            key=lambda x: x["final_score"],
            reverse=True
        )
            print("===== 최종 후보 =====")

            for item in all_combinations[:5]:
                names = [c["name"] for c in item["schedule"]]
                print(names)

        return [all_combinations[0]["schedule"]]

    return []


def make_timetable_title(
    selected_schedule,
    selected_course_set,
    exclude_days,
    avoid_time_slots
):
    """
    시간표 조합의 여러 특징을 종합하여 UI용 시간표 제목을 생성
    예: 전공 우선 · 공강 반영 · 부족 교양 보완 시간표
    """

    title_parts = []

    # 1. 사용자가 직접 선택한 과목 포함 여부
    has_selected_course = any(
        course["name"] in selected_course_set
        for course in selected_schedule
    )

    if has_selected_course:
        title_parts.append("선택 과목 반영")

    # 2. 해당 학년 추천 전공 포함 여부
    current_grade_major_count = sum(
        1 for course in selected_schedule
        if course.get("is_current_grade_major", False)
    )

    if current_grade_major_count > 0:
        title_parts.append("전공 우선")

    # 3. 이전 학년 미이수 전공필수 포함 여부
    has_missing_required_major = any(
        course.get("is_missing_required_major", False)
        for course in selected_schedule
    )

    if has_missing_required_major:
        title_parts.append("미이수 전공필수 보완")

    # 4. 부족 교양 포함 여부
    has_needed_ge = any(
        course.get("is_needed_ge", False)
        for course in selected_schedule
    )

    if has_needed_ge:
        title_parts.append("부족 교양 보완")

    # 5. 공강 조건 만족 여부
    actual_days = {
        slot["day"]
        for course in selected_schedule
        for slot in course["time_slots"]
    }

    achieved_empty_days = [
        day for day in exclude_days
        if day not in actual_days
    ]

    if achieved_empty_days:
        title_parts.append("공강 반영")

    # 6. 피하고 싶은 시간대 반영 여부
    avoid_success_count = 0

    for avoid in avoid_time_slots:
        target_day = avoid.get("day")
        target_range = avoid.get("time_range")
        specific_slots = avoid.get("specific_time_slot")

        is_violated = False

        for course in selected_schedule:
            for slot in course["time_slots"]:

                if target_day and slot["day"] != target_day:
                    continue

                if specific_slots:
                    for period in specific_slots:
                        if slot["start_period"] <= period <= slot["end_period"]:
                            is_violated = True

                elif target_range == "오전" and slot["start_period"] < 5:
                    is_violated = True

                elif target_range == "오후" and slot["start_period"] >= 5:
                    is_violated = True

        if not is_violated:
            avoid_success_count += 1

    if avoid_success_count > 0:
        title_parts.append("시간대 선호 반영")

    # 7. 제목이 너무 길어지지 않도록 최대 3개 핵심만 사용
    if title_parts:
        return " · ".join(title_parts[:3]) + " 시간표"

    return "추천 시간표"

def build_timetable_json(
    timetable_results,
    parsed_data,
    exclude_days,
    avoid_time_slots
):
    selected_course_set = set(
        parsed_data.get("selected_courses", [])
    )

    if not timetable_results:
        return {
            "status": "error",
            "message": "조건을 만족하는 시간표 조합을 찾지 못했습니다. 조건을 완화해 주세요."
        }

    final_json_output = {
        "status": "success",
        "total_alternatives": 0,
        "alternatives": []
    }

    for index, selected_schedule in enumerate(timetable_results):
        actual_days = {
            slot["day"]
            for course in selected_schedule
            for slot in course["time_slots"]
        }

        failed_empty_days = [
            day for day in exclude_days
            if day in actual_days
        ]

        if failed_empty_days:
            continue

        course_color_map = assign_course_colors(selected_schedule)

        cleaned_courses = []
        required_course_names = []

        # -------------------------------------------------
        # [1] 과목별 UI 전달 정보 구성
        # -------------------------------------------------
        for course in selected_schedule:

            if course.get("is_required"):
                required_course_names.append(course["name"])

            cleaned_slots = []

            for slot in course["time_slots"]:
                cleaned_slots.append({
                    "day": slot["day"],
                    "time": slot["time_range"]
                })

            course_color = course_color_map[course["name"]]

            course_reason = []

            if course["name"] in selected_course_set:
                course_reason.append(
                    "사용자가 직접 선택한 과목입니다."
                )

            if course.get("is_current_grade_major", False):
                course_reason.append(
                    "해당 학년 표준이수모형에 포함된 전공 과목입니다."
                )

            if course.get("is_missing_required_major", False):
                course_reason.append(
                    "이전 학년에 이수하지 못한 전공필수 보완 과목입니다."
                )

            if course.get("is_needed_ge", False):
                course_reason.append(
                    "졸업요건상 부족한 교양 영역을 채우기 위한 과목입니다."
                )

            course_days = {
                slot["day"] for slot in course["time_slots"]
            }

            if exclude_days and not any(day in exclude_days for day in course_days):
                course_reason.append(
                    "사용자가 요청한 공강 요일을 침범하지 않는 과목입니다."
                )

            if not course_reason:
                course_reason.append(
                    "시간 충돌을 피하고 목표 학점에 맞추기 위해 선택된 과목입니다."
                )

            cleaned_courses.append({
                "course_name": course["name"],
                "classroom": course["room"],
                "schedule": cleaned_slots,
                "selection_reason": course_reason,
                "assignment_load": course.get("assignment_load"),
                "team_project": course.get("team_project"),
                "color": {
                    "background": course_color["background"],
                    "text": course_color["text"]
                }
            })

        # -------------------------------------------------
        # [2] 시간표 전체 조합 이유 생성
        # -------------------------------------------------
        reason_segments = []

        if index == 0:
            reason_segments.append(
                "사용자 요청 과목과 선호 조건을 우선적으로 반영했습니다."
            )
        elif index == 1:
            reason_segments.append(
                "졸업요건 충족과 부족한 교양 영역 보완을 우선적으로 고려했습니다."
            )
        else:
            reason_segments.append(
                "전공, 공강, 시간대 선호 조건을 균형 있게 반영했습니다."
            )

        included_needed_ge_areas = []

        for course in selected_schedule:
            if course.get("is_needed_ge", False):
                ge_label = (
                    f"{course['area']}({course['subarea']})"
                    if course["subarea"]
                    else course["area"]
                )

                if ge_label not in included_needed_ge_areas:
                    included_needed_ge_areas.append(ge_label)

        if included_needed_ge_areas:
            reason_segments.append(
                f"부족 교양 영역인 {', '.join(included_needed_ge_areas)} 과목을 포함했습니다."
            )

        achieved_empty_days = [
            day for day in exclude_days
            if day not in actual_days
        ]

        if achieved_empty_days:
            reason_segments.append(
                f"{', '.join(achieved_empty_days)}요일 공강 조건을 만족합니다."
            )

        avoid_success_days = []
        avoid_fail_details = []

        for avoid in avoid_time_slots:
            target_day = avoid.get("day")
            target_range = avoid.get("time_range")
            specific_slots = avoid.get("specific_time_slot")

            is_violated = False

            for course in selected_schedule:
                for slot in course["time_slots"]:

                    if target_day and slot["day"] != target_day:
                        continue

                    if specific_slots:
                        for period in specific_slots:
                            if slot["start_period"] <= period <= slot["end_period"]:
                                is_violated = True

                    elif target_range == "오전" and slot["start_period"] < 5:
                        is_violated = True

                    elif target_range == "오후" and slot["start_period"] >= 5:
                        is_violated = True

            if not is_violated:
                if specific_slots:
                    avoid_success_days.append(
                        f"{target_day if target_day else '전체 요일'} {specific_slots}교시"
                    )
                else:
                    avoid_success_days.append(
                        f"{target_day if target_day else '전체 요일'} {target_range}"
                    )
            else:
                if specific_slots:
                    avoid_fail_details.append(
                        f"{target_day if target_day else '전체 요일'} {specific_slots}교시"
                    )
                else:
                    avoid_fail_details.append(
                        f"{target_day if target_day else '전체 요일'} {target_range}"
                    )

        if avoid_success_days:
            reason_segments.append(
                f"요청한 {', '.join(avoid_success_days)} 조건을 반영했습니다."
            )

        if avoid_fail_details:
            reason_segments.append(
                f"다만 목표 학점과 필수 과목 반영을 위해 {', '.join(avoid_fail_details)} 조건은 일부 완화되었습니다."
            )

        if required_course_names:
            reason_segments.append(
                f"우선순위가 높은 과목인 {', '.join(required_course_names)}을 포함했습니다."
            )

        assignment_preference = parsed_data.get("assignment_preference")
        if assignment_preference == "과제적음":
            reason_segments.append("과제가 적은 과목 위주로 편성되었습니다.")
        elif assignment_preference == "과제많음":
            reason_segments.append("과제가 많은 과목 위주로 편성되었습니다.")

        team_project_preference = parsed_data.get("team_project_preference")
        if team_project_preference == "팀플없음":
            reason_segments.append("팀플이 없는 과목 위주로 편성되었습니다.")
        elif team_project_preference == "팀플있음":
            reason_segments.append("팀플이 있는 과목 위주로 편성되었습니다.")

        recommendation_reason = "시간표 조합 이유:\n" + "\n".join(
            f"  - {reason}" for reason in reason_segments
        )

        # -------------------------------------------------
        # [3] 복합 이유 기반 시간표 제목 생성
        # -------------------------------------------------
        timetable_title = make_user_request_title(parsed_data)

        alternative_item = {
            "alternative_id": index + 1,
            "timetable_title": timetable_title,
            "recommendation_reason": recommendation_reason,
            "courses": cleaned_courses
        }

        final_json_output["alternatives"].append(alternative_item)

    final_json_output["total_alternatives"] = len(final_json_output["alternatives"])

    if not final_json_output["alternatives"]:
        return {
            "status": "error",
            "message": "요청하신 공강 조건을 만족하는 시간표를 찾지 못했습니다. 공강 요일이나 목표 학점 조건을 완화해 주세요."
        }

    return final_json_output

def generate_timetable_response(parsed_data, login_student_id, target_semester=1):
    

    exclude_days = []
    avoid_time_slots = []
    preferred_time_slots = []

    for slot in parsed_data["slots"]:
        day = slot["day"].replace("요일", "")

        if slot["condition"] == "공강":
            if day not in exclude_days:
                exclude_days.append(day)
            continue

        if slot["condition"] == "피함":
            avoid_time_slots.append({
                "day": day,
                "time_range": slot["time_range"],
                "specific_time_slot": normalize_specific_time(slot)
            })

        if slot["condition"] == "선호":
            preferred_time_slots.append({
                "day": day,
                "time_range": slot["time_range"],
                "specific_time_slot": normalize_specific_time(slot)
            })

    slots_input = {
        "target_grade": parsed_data.get("target_grade"),
        "exclude_days": exclude_days,
        "target_credit": parsed_data.get("target_credit"),
        "avoid_time_slots": avoid_time_slots,
        "preferred_time_slots": preferred_time_slots
    }


    graduation_analysis = get_final_recommendations(
        student_id=login_student_id,
        target_semester=target_semester,
        students_json_data=students_list
    )

    if "error" in graduation_analysis:
        return {
            "status": "error",
            "message": graduation_analysis["error"]
        }

    recommended_majors = graduation_analysis.get("recommended_major_courses", [])
    needed_general_areas = graduation_analysis.get("needed_general_areas", {})
    missing_required_majors = graduation_analysis.get("missing_required_major_courses", [])

    all_lectures_df = pd.concat([
        pd.read_csv(MAJOR_DATA_PATH),
        pd.read_csv(GE_DATA_PATH)
    ], ignore_index=True)

    has_empty_day_request = bool(exclude_days)
    user_preferences_input = {
        "assignment_preference": parsed_data.get("assignment_preference"),
        "team_preference": parsed_data.get("team_project_preference"),
        "conflict_resolution_rule": (
            "공강우선"
            if has_empty_day_request
            else parsed_data.get("conflict_resolution_rule", "과목우선")
            ),
        "selected_courses": parsed_data.get("selected_courses", []),
        "excluded_courses": parsed_data.get("excluded_courses", []),
        "course_priority": parsed_data.get("course_priority")
    }

    import re

    raw_credit = slots_input.get("target_credit")

    if raw_credit:
        digit_match = re.search(r"\d+", str(raw_credit))
        target_credit_int = int(digit_match.group()) if digit_match else 18
    else:
        target_credit_int = 18

    user_priority_results = generate_timetable_combinations(
        recommended_major_courses=recommended_majors,
        needed_general_areas=needed_general_areas,
        missing_required_major_courses=missing_required_majors,
        filtered_df=all_lectures_df,
        target_credits=target_credit_int,
        empty_days=slots_input["exclude_days"],
        avoid_time_slots=slots_input["avoid_time_slots"],
        preferred_time_slots=slots_input["preferred_time_slots"],
        user_preferences=user_preferences_input,
        mode="user_priority"
    )

    graduation_priority_results = generate_timetable_combinations(
        recommended_major_courses=recommended_majors,
        needed_general_areas=needed_general_areas,
        missing_required_major_courses=missing_required_majors,
        filtered_df=all_lectures_df,
        target_credits=target_credit_int,
        empty_days=slots_input["exclude_days"],
        avoid_time_slots=slots_input["avoid_time_slots"],
        preferred_time_slots=slots_input["preferred_time_slots"],
        user_preferences=user_preferences_input,
        mode="graduation_priority"
    )

    selected_courses = set(parsed_data.get("selected_courses", []))

    if selected_courses and not user_priority_results:
        return {
            "status": "error",
            "message": "조건을 만족하는 시간표 조합을 찾지 못했습니다. 조건을 완화해 주세요."
        }

    timetable_results = []

    if user_priority_results:
        timetable_results.append(user_priority_results[0])

    if graduation_priority_results:
        timetable_results.append(graduation_priority_results[0])

    unique_results = []
    seen = set()

    for schedule in timetable_results:
        names = tuple(sorted(c["name"] for c in schedule))

        if names not in seen:
            seen.add(names)
            unique_results.append(schedule)

    timetable_results = unique_results

    final_json_output = build_timetable_json(
        timetable_results=timetable_results,
        parsed_data=parsed_data,
        exclude_days=exclude_days,
        avoid_time_slots=avoid_time_slots
    )

    return final_json_output

# if __name__ == "__main__":
#     user_sentence="캡스톤디자인 꼭 넣고 18학점 맞춰줘"
#     json_result = parse_schedule_text(user_sentence, MY_API_KEY)
#     parsed_data = json.loads(json_result)
#     result = generate_timetable_response(
#         parsed_data=parsed_data,
#          login_student_id="20250001",
#          target_semester=1
#     )

#     print(json.dumps(result, ensure_ascii=False, indent=2))
