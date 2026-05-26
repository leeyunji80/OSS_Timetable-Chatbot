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

    for _, area_data in areas.items():

        subareas = area_data.get(
            "subareas",
            {}
        )

        for _, subarea_data in subareas.items():

            subarea_name = subarea_data["name"]

            required_credit = subarea_data.get(
                "min_credits"
            )

            if required_credit is None:
                continue

            completed_credit = (
                graduation_status["subareas"].get(
                    subarea_name,
                    0
                )
            )

            remaining_credit = max(
                0,
                required_credit
                - completed_credit
            )

            remaining["areas"][
                subarea_name
            ] = remaining_credit

    return remaining



def get_recommended_courses(
    curriculum_df,
    curriculum_year,
    current_grade,
    current_semester
):

    recommended_df = curriculum_df[
        (curriculum_df["년도"] == curriculum_year)
        &
        (curriculum_df["학년"] == current_grade)
        &
        (curriculum_df["학기"] == current_semester)
    ].drop_duplicates(subset=["과목명"])

    return recommended_df["과목명"].tolist()



def filter_completed_courses(recommended_courses, completed_set):

    return [
        course for course in recommended_courses
        if course not in completed_set
    ]

# ---------------------------------
# [수정] 로그인 팀원에게 학번을 받아 처리하는 통합 함수
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
    # (주의: curriculum_df의 '년도'가 교육과정 지정 년도인지 확인 필요)
    recommended_courses = get_recommended_courses(
        curriculum_df, 
        curriculum_year=admission_year, 
        current_grade=current_grade, 
        current_semester=target_semester
    )
    
    # 7. 이미 이수한 과목 필터링
    completed_set = graduation_status["completed_course_names"]
    filtered_courses = filter_completed_courses(recommended_courses, completed_set)
    
    # ---------------------------------
    # 부족한 교양 세부영역 추출
    # ---------------------------------

    needed_general_areas = {
        area_name: remain_credit
        for area_name, remain_credit
        in remaining_reqs["areas"].items()
        if remain_credit > 0
}

    return {
        "student_name": student_info["name"],

        # 학생 정보
        "student_context": {
            "grade": current_grade,
            "curriculum_year": admission_year
        },

        # 부족 전공 학점
        "remaining_major": {
            "major_required": remaining_reqs["major_required"],
            "major_elective": remaining_reqs["major_elective"]
        },

        # 부족 교양 세부영역
        "needed_general_areas": needed_general_areas,
 
        # 현재 학년 추천 전공 과목
        "recommended_major_courses": filtered_courses
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
    login_student_id = "20260001"
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