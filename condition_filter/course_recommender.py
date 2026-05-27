import json
import pandas as pd


# ---------------------------------
# 파일 경로
# ---------------------------------

GRADUATION_RULE_PATH = (
    "graduation_rule/graduation.json"
)

CURRICULUM_MODEL_PATH = (
    "graduation_rule/standard_curriculum.csv"
)

COURSE_HISTORY_PATH = (
    "student/course_history.csv"
)

STUDENT_DATA_PATH = "student/students.json"

def load_students_data(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

# ---------------------------------
# 졸업요건 JSON 로드
# ---------------------------------

def load_graduation_rules(json_path):

    with open(
        json_path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ---------------------------------
# 표준이수모형 CSV 로드
# ---------------------------------

def load_curriculum_model(csv_path):

    return pd.read_csv(
        csv_path,
        encoding="utf-8-sig"
    )


# ---------------------------------
# 입학년도에 맞는 졸업요건 선택
# ---------------------------------

def get_graduation_rule(
    rules_data,
    admission_year
):

    for _, rule in rules_data["rule_sets"].items():

        applies = rule["applies_to"]

        if (
            applies["admission_year_from"]
            <= admission_year
            <= applies["admission_year_to"]
        ):

            return rule

    return None


# ---------------------------------
# 학생 이수 현황 분석
# ---------------------------------

def analyze_graduation_status(
    completed_courses
):

    status = {

    "total_credits": 0,

    "major_required": 0,

    "major_elective": 0,

    "areas": {},

    "subareas": {},

    "completed_course_names": set()
}

    for course in completed_courses:

        credit = course.get(
            "credit",
            0
        )

        status["total_credits"] += credit

        status["completed_course_names"].add(
            course["name"]
        )

        category = course.get(
            "subcategory",
            ""
        )

        if category == "전공필수":

            status["major_required"] += credit

        elif category == "전공선택":

            status["major_elective"] += credit

        area = course.get("area")

        subarea = course.get("subarea")

        if subarea:

           if subarea not in status["subareas"]:

               status["subareas"][subarea] = 0

           status["subareas"][subarea] += credit

        if area:

            if area not in status["areas"]:

                status["areas"][area] = 0

            status["areas"][area] += credit

    return status

# ---------------------------------
# 학생 수강 이력 로드
# ---------------------------------

def load_completed_courses(
    csv_path,
    student_id
):

    df = pd.read_csv(
        csv_path,
        encoding="utf-8-sig"
    )

    student_df = df[
    df["student_id"].astype(str) == str(student_id)
    ]

    completed_courses = []

    for _, row in student_df.iterrows():

        completed_courses.append({

            "name": row["교과목명"],

            "credit": int(row["학점"]),

            "subcategory": row["이수구분"],

            "area": row["영역"],

            "subarea": row["세부영역"]
        })

    return completed_courses

# ---------------------------------
# 데이터 로드
# ---------------------------------

rules_data = load_graduation_rules(
    GRADUATION_RULE_PATH
)

curriculum_df = load_curriculum_model(
    CURRICULUM_MODEL_PATH
)

students_list = load_students_data(STUDENT_DATA_PATH)
# ---------------------------------
# 테스트
# ---------------------------------



# ---------------------------------
# 졸업요건 부족 현황 계산
# ---------------------------------

def calculate_remaining_requirements(
    graduation_rule,
    graduation_status
):

    remaining = {}

    # -----------------------------
    # 전공
    # -----------------------------

    major_rules = graduation_rule[
        "requirements"
    ]["major"]["types"]

    required_major_required = major_rules[
        "major_required"
    ]["min_credits"]

    required_major_elective = major_rules[
        "major_elective"
    ]["min_credits"]

    remaining["major_required"] = max(
        0,
        required_major_required
        - graduation_status["major_required"]
    )

    remaining["major_elective"] = max(
        0,
        required_major_elective
        - graduation_status["major_elective"]
    )

    # -----------------------------
    # 교양 세부영역
    # -----------------------------

    remaining["areas"] = {}

    areas = graduation_rule[
        "requirements"
    ]["general_education"]["areas"]

    for area_key, area_data in areas.items():
        area_name = area_data["name"]       # 예: "개신기초교양", "일반교양"
        area_min_credit = area_data.get("min_credits")
        subareas_data = area_data.get("subareas", {})

        completed_area_credit = 0
        for sub_key, sub_data in subareas_data.items():
            sub_name = sub_data["name"]
            completed_area_credit += graduation_status["subareas"].get(sub_name, 0)

        if area_name not in remaining["areas"]:
            remaining["areas"][area_name] = {}

        has_subarea_min = any(s.get("min_credits") is not None for s in subareas_data.values())
        
        # ---------------------------------------------------------
        # 트랙 1: 세부 영역별 최소 필수 학점 조건이 명시적으로 있는 경우 (예: 개신기초교양)
        # ---------------------------------------------------------
        if has_subarea_min:
            for sub_key, sub_data in subareas_data.items():
                sub_name = sub_data["name"]
                required_sub_credit = sub_data.get("min_credits", 0)
                
                completed_sub_credit = graduation_status["subareas"].get(sub_name, 0)
                sub_shortage = max(0, required_sub_credit - completed_sub_credit)
                
                if sub_shortage > 0:
                    remaining["areas"][area_name][sub_name] = sub_shortage

        # ---------------------------------------------------------
        # 트랙 2: 대분류 총점 기준만 채우면 되는 경우 (예: 일반교양, 확대교양 등)
        # ---------------------------------------------------------
        elif area_min_credit is not None:
            area_shortage = max(0, area_min_credit - completed_area_credit)
            
            if area_shortage > 0:
                uncompleted_subareas = [
                    sub_data["name"] for sub_data in subareas_data.values()
                    if graduation_status["subareas"].get(sub_data["name"], 0) == 0
                ]
                final_targets = uncompleted_subareas if uncompleted_subareas else [s["name"] for s in subareas_data.values()]
                
                # 깔끔하게 이 두 가지만 저장하고, 개별 소분류 반복문(for)은 과감히 삭제합니다.
                remaining["areas"][area_name] = {
                    "총필요학점": area_shortage,
                    "선택가능영역": final_targets
                }

        if not remaining["areas"][area_name]:
            del remaining["areas"][area_name]

    return remaining



def get_recommended_courses(
    curriculum_df,
    curriculum_year,
    current_grade,
    current_semester
):
    # 해당 학년/학기 데이터 필터링
    recommended_df = curriculum_df[
        (curriculum_df["년도"] == curriculum_year)
        & (curriculum_df["학년"] == current_grade)
        & (curriculum_df["학기"] == current_semester)
    ].drop_duplicates(subset=["과목명"])

    all_courses = recommended_df["과목명"].tolist()
    
    major_courses = []
    general_courses = []
    
    for course in all_courses:
        # 과목명에 '택1', '교양', '영역' 등이 포함되어 있으면 교양으로 분류
        if "택1" in course or "교양" in course or "영역" in course:
            general_courses.append(course)
        else:
            major_courses.append(course)
            
    return {"major": major_courses, "general": general_courses}



def filter_completed_courses(recommended_courses, completed_set):

    return [
        course for course in recommended_courses
        if course not in completed_set
    ]

# ---------------------------------
# 로그인 팀원에게 학번을 받아 처리하는 통합 함수
# ---------------------------------
def get_final_recommendations(student_id, target_semester, students_json_data):
    # 1. 넘겨받은 student_id로 JSON에서 학생 정보 찾기
    student_info = None
    for s in students_json_data:
        if str(s["student_id"]) == str(student_id):
            student_info = s
            break
            
    if not student_info:
        return {"error": "존재하지 않는 학생 학번입니다."}
    
    # 2. 학생 정보에서 동적으로 변수 추출
    admission_year = student_info["curriculum_year"]
    current_grade = student_info["grade"]
    
    # 3. 입학년도에 맞는 졸업 규칙 로드
    graduation_rule = get_graduation_rule(rules_data, admission_year)
    if not graduation_rule:
        return {"error": f"{admission_year}년도 졸업 요건 정의가 존재하지 않습니다."}
        
    # 4. 학생 수강 이력 로드 및 분석
    completed_courses = load_completed_courses(COURSE_HISTORY_PATH, student_id)
    graduation_status = analyze_graduation_status(completed_courses)
    
    # 5. 부족한 요건 분석
    remaining_reqs = calculate_remaining_requirements(graduation_rule, graduation_status)
    
    
    
    # 6. 표준이수모형에서 과목 가져오기
    rec_dict = get_recommended_courses(
        curriculum_df, 
        curriculum_year=admission_year, 
        current_grade=current_grade, 
        current_semester=target_semester
    )
    
    # 7. 이미 이수한 과목 필터링 (전공 / 교양 각각 진행)
    completed_set = graduation_status["completed_course_names"]
    filtered_major = filter_completed_courses(rec_dict["major"], completed_set)
    filtered_general = filter_completed_courses(rec_dict["general"], completed_set)
    
    needed_general_areas = {}
    for area_name, sub_dict in remaining_reqs["areas"].items():
        # 트랙 2 구조("총필요학점" 키가 있는 경우)는 필터링을 건너뛰고 그대로 통과
        if "총필요학점" in sub_dict:
            if sub_dict["총필요학점"] > 0:
                needed_general_areas[area_name] = sub_dict
        else:
            # 트랙 1 구조(개신기초교양 등 소분류 딕셔너리)는 기존처럼 학점 0 초과만 솎아내기
            filtered_sub = {sub_name: credit for sub_name, credit in sub_dict.items() if credit > 0}
            if filtered_sub:
                needed_general_areas[area_name] = filtered_sub

    return {
        "needed_general_areas": needed_general_areas,
        "recommended_major_courses": filtered_major
    }

# ---------------------------------
# 실행 예시 (서버 구동 시 또는 라우터 내부에서 호출)
# ---------------------------------
# students_list = [ ... 상단에 적어주신 학생 JSON 리스트 ... ]
# result = get_final_recommendations(student_id="20210001", target_semester=1, students_json_data=students_list)
# print(result)

# =============================================================
# 실제 함수 호출 및 테스트 구역
# =============================================================
if __name__ == "__main__":
    
    # 1. 로그인 담당 팀원이 넘겨준 "학번"과 "추천받을 학기" 예시
    login_student_id = "20210005"
    target_semester = 1

    # 2. 파일에서 불러온 students_list를 그대로 인자에 주입!
    final_result = get_final_recommendations(
        student_id=login_student_id,
        target_semester=target_semester,
        students_json_data=students_list
    )

    # 3. 결과 출력
    print(f"\n==== {login_student_id} 학생의 최종 분석 및 추천 결과 ====")
    print(json.dumps(final_result, indent=4, ensure_ascii=False))