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

admission_year = 2025

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