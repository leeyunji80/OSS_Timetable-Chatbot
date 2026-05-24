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


# ---------------------------------
# 테스트
# ---------------------------------

admission_year = 2021

graduation_rule = get_graduation_rule(
    rules_data,
    admission_year
)

print("\n선택된 졸업요건")
print(graduation_rule["name"])

student_id = "20210001"

completed_courses = load_completed_courses(
    COURSE_HISTORY_PATH,
    student_id
)

graduation_status = analyze_graduation_status(
    completed_courses
)

print("\n학생 이수 현황")
print(graduation_status)

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

remaining_requirements = (
    calculate_remaining_requirements(
        graduation_rule,
        graduation_status
    )
)

print("\n남은 졸업요건")
print(remaining_requirements)

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

recommended_courses = get_recommended_courses(
    curriculum_df,
    2021,
    3,
    1
)

print(recommended_courses)

def filter_completed_courses(recommended_courses, completed_set):

    return [
        course for course in recommended_courses
        if course not in completed_set
    ]
completed_set = graduation_status["completed_course_names"]

filtered_courses = filter_completed_courses(
    recommended_courses,
    completed_set
)

print("\n추천 과목 (필터 적용 후)")
print(filtered_courses)