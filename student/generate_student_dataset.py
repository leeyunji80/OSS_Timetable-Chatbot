import json
import random
import re
from pathlib import Path

import pandas as pd


# seed 값만 바꾸면 같은 시나리오에서 다른 랜덤 데이터셋을 재현 가능하게 만들 수 있음
RANDOM_SEED = 42

# 시간표 추천 대상 학기. 학생 데이터는 이 학기 시작 직전 상태로 생성
TARGET_YEAR = 2026
TARGET_SEMESTER = 1
DOWNLOAD_DIR = Path(r"C:\Users\leeyu\Downloads")
OUTPUT_DIR = Path(__file__).resolve().parent

LECTURES_PATH = DOWNLOAD_DIR / "lectures_database.csv"
LIBERAL_ARTS_PATH = DOWNLOAD_DIR / "liberal_arts.csv"
STANDARD_CURRICULUM_PATH = DOWNLOAD_DIR / "standard_curriculum.csv"
GRADUATION_PATH = DOWNLOAD_DIR / "graduation.json"

STUDENTS_PATH = OUTPUT_DIR / "students.json"
COURSE_HISTORY_PATH = OUTPUT_DIR / "course_history.csv"

COURSE_HISTORY_COLUMNS = [
    "student_id",
    "수강년도",
    "수강학기",
    "교과목번호",
    "교과목명",
    "이수구분",
    "영역",
    "세부영역",
    "학점",
]
# 시나리오를 추가하면 같은 생성 로직으로 학생 유형을 늘릴 수 있다.
student_scenarios = [
    {
        "student_id": "20210001",
        "name": "김컴공",
        "curriculum_year": 2021,
        "type": "normal",
        "target_completed_credits": [115, 130],
        "lack_major_required": False,
        "lack_major_elective": False,
        "lack_liberal_arts": False,
        "lack_basic_liberal": False,
        "lack_general_liberal": False,
        "prefer_standard_curriculum": True,
    },
    {
        "student_id": "20210002",
        "name": "이필수",
        "curriculum_year": 2021,
        "type": "lack_major_required",
        "target_completed_credits": [100, 120],
        "lack_major_required": True,
        "lack_major_elective": False,
        "lack_liberal_arts": False,
        "lack_basic_liberal": False,
        "lack_general_liberal": False,
        "prefer_standard_curriculum": True,
    },
    {
        "student_id": "20210003",
        "name": "박교양",
        "curriculum_year": 2021,
        "type": "lack_general_liberal",
        "target_completed_credits": [95, 115],
        "lack_major_required": False,
        "lack_major_elective": False,
        "lack_liberal_arts": False,
        "lack_basic_liberal": False,
        "lack_general_liberal": True,
        "prefer_standard_curriculum": True,
    },
    {
        "student_id": "20210004",
        "name": "최저학점",
        "curriculum_year": 2021,
        "type": "low_total_credits",
        "target_completed_credits": [70, 90],
        "semester_credit_range": [6, 12],
        "lack_major_required": False,
        "lack_major_elective": False,
        "lack_liberal_arts": False,
        "lack_basic_liberal": False,
        "lack_general_liberal": False,
        "prefer_standard_curriculum": True,
    },
    {
        "student_id": "20210005",
        "name": "정위험",
        "curriculum_year": 2021,
        "type": "graduation_risk",
        "target_completed_credits": [85, 100],
         "semester_credit_range": [8, 14],
        "lack_major_required": True,
        "lack_major_elective": True,
        "lack_liberal_arts": True,
        "lack_basic_liberal": False,
        "lack_general_liberal": True,
        "prefer_standard_curriculum": False,
    },
    {
        "student_id": "20260001",
        "name": "한새내",
        "curriculum_year": 2026,
        "type": "freshman",
        "target_completed_credits": [0, 0],
        "lack_major_required": False,
        "lack_major_elective": False,
        "lack_liberal_arts": False,
        "lack_basic_liberal": False,
        "lack_general_liberal": False,
        "prefer_standard_curriculum": True,
    },
    {
        "student_id": "20250001",
        "name": "오소포",
        "curriculum_year": 2025,
        "type": "sophomore",
        "target_completed_credits": [30, 36],
        "lack_major_required": False,
        "lack_major_elective": False,
        "lack_liberal_arts": False,
        "lack_basic_liberal": False,
        "lack_general_liberal": False,
        "prefer_standard_curriculum": True,
    },
    {
        "student_id": "20240001",
        "name": "서주니",
        "curriculum_year": 2024,
        "type": "junior",
        "target_completed_credits": [60, 72],
        "lack_major_required": False,
        "lack_major_elective": False,
        "lack_liberal_arts": False,
        "lack_basic_liberal": False,
        "lack_general_liberal": False,
        "prefer_standard_curriculum": True,
    },
    {
        "student_id": "20230001",
        "name": "윤시니",
        "curriculum_year": 2023,
        "type": "senior",
        "target_completed_credits": [90, 108],
        "lack_major_required": False,
        "lack_major_elective": False,
        "lack_liberal_arts": False,
        "lack_basic_liberal": False,
        "lack_general_liberal": False,
        "prefer_standard_curriculum": True,
    },
]

def read_source_files():
    """원본 CSV/JSON을 읽는다. 교과목 번호는 앞자리 0 보존을 위해 문자열로 읽는다."""
    lectures = pd.read_csv(LECTURES_PATH, encoding="utf-8-sig", dtype={"교과목 번호": str})
    liberal_arts = pd.read_csv(LIBERAL_ARTS_PATH, encoding="utf-8-sig", dtype={"교과목 번호": str})
    standard_curriculum = pd.read_csv(STANDARD_CURRICULUM_PATH, encoding="utf-8-sig")
    graduation = json.loads(GRADUATION_PATH.read_text(encoding="utf-8"))
    return lectures, liberal_arts, standard_curriculum, graduation

def normalize_course_name(name):
    """표준이수모형과 실제 CSV의 가벼운 표기 차이를 비교하기 위한 정규화."""
    normalized = str(name).upper()
    normalized = normalized.replace("Ⅰ", "I").replace("Ⅱ", "II").replace("Ⅲ", "III")
    normalized = re.sub(r"\s+", "", normalized)
    normalized = normalized.replace("·", "").replace("-", "").replace("_", "")
    return normalized

def parse_target_grade(value):
    """수강 대상 문자열에서 권장 학년을 추출한다. 없으면 전학년 과목처럼 1학년으로 둔다."""
    match = re.search(r"(\d)학년", str(value))
    return int(match.group(1)) if match else 1


def liberal_area_name(raw_area):
    """교양대분류를 students.json과 course_history.csv에서 사용할 영역명으로 맞춘다."""
    mapping = {
        "개신기초교양": "개신기초",
        "자연·이공계기초과학": "자연이공계기초",
        "일반교양": "일반",
        "확대교양": "확대",
    }
    return mapping.get(raw_area, raw_area)

def prepare_major_catalog(lectures):
    """전공 강의 CSV를 중복 분반 제거된 선택용 카탈로그로 변환한다."""
    catalog = lectures.drop_duplicates("교과목 번호").copy()
    catalog["교과목번호"] = catalog["교과목 번호"]
    catalog["영역"] = "전공"
    catalog["세부영역"] = catalog["이수구분"].map({"전공필수": "필수", "전공선택": "선택"})
    catalog["권장학년"] = catalog["수강 대상"].map(parse_target_grade)
    catalog["정규화과목명"] = catalog["교과목명"].map(normalize_course_name)
    return catalog

def prepare_liberal_catalog(liberal_arts):
    """교양 강의 CSV를 중복 분반 제거된 선택용 카탈로그로 변환한다."""
    catalog = liberal_arts.drop_duplicates("교과목 번호").copy()
    catalog["교과목번호"] = catalog["교과목 번호"]
    catalog["영역"] = catalog["교양대분류"].map(liberal_area_name)
    catalog["세부영역"] = catalog["교양소분류"]
    catalog["권장학년"] = catalog["수강 대상"].map(parse_target_grade)
    catalog["정규화과목명"] = catalog["교과목명"].map(normalize_course_name)
    return catalog

def graduation_requirements(graduation, curriculum_year):
    """입학연도에 맞는 졸업요건에서 required 값을 계산한다."""
    rule_sets = graduation["rule_sets"]
    year_key = str(curriculum_year)
    if year_key not in rule_sets:
        raise ValueError(f"graduation.json에 {curriculum_year}학년도 졸업요건이 없습니다.")

    rule = rule_sets[year_key]
    requirements = rule["requirements"]
    general = requirements["general_education"]
    major = requirements["major"]

    required = {
        "교양": {
            "개신기초": general["areas"]["gaesin_basic"]["min_credits"],
            "자연이공계기초": general["areas"]["basic_science_engineering"]["min_credits"],
            "일반": general["areas"]["general"]["min_credits"],
            "확대": general["areas"]["expanded"]["min_credits"],
            "OCU_기타": 0,
        },
        "전공": {
            "필수": major["types"]["major_required"]["min_credits"],
            "선택": major["types"]["major_elective"]["min_credits"],
        },
        "졸업학점": rule["graduation"]["min_total_credits"],
    }

    # graduation.json에 일반선택 필수 이수학점이 별도로 정의되어 있지 않으므로 0으로 처리한다.
    required["일반선택"] = 0
    return required

def semester_sequence(curriculum_year, completed_semesters):
    """입학연도와 이수학기 수를 기반으로 실제 이수한 학기 목록을 만든다."""
    semesters = []
    for index in range(1, completed_semesters + 1):
        semesters.append(
            {
                "term_index": index,
                "수강년도": curriculum_year + (index - 1) // 2,
                "수강학기": 1 if index % 2 == 1 else 2,
                "학년": min(4, (index + 1) // 2),
            }
        )
    return semesters


def calculate_max_completed_semesters(curriculum_year, target_year=TARGET_YEAR, target_semester=TARGET_SEMESTER):
    """
    추천 대상 학기 시작 직전까지 실제로 이수 완료 가능한 최대 학기 수를 계산
    예: TARGET_YEAR=2026, TARGET_SEMESTER=1이면 2026학번은 0학기, 2025학번은 2학기, 2024학번은 4학기까지 가능
    """
    completed = (target_year - curriculum_year) * 2 + (target_semester - 1)
    return max(0, completed)

def calculate_current_grade(curriculum_year, target_year=TARGET_YEAR, target_semester=TARGET_SEMESTER):
    """추천 대상 학기 기준 학생의 현재 학년을 계산"""
    completed_semesters = calculate_max_completed_semesters(curriculum_year, target_year, target_semester)
    return min(4, max(1, completed_semesters // 2 + 1))

def standard_items_for_term(standard_curriculum, curriculum_year, grade, semester):
    """해당 학년/학기의 표준이수모형 과목명과 '택1' 형태의 영역 힌트를 분리한다."""
    target = standard_curriculum[
        (standard_curriculum["년도"] == curriculum_year)
        & (standard_curriculum["학년"] == grade)
        & (standard_curriculum["학기"] == semester)
    ]

    course_names = []
    area_hints = []
    for name in target["과목명"].dropna().tolist():
        text = str(name)
        if "택" in text or "영역" in text or "분야" in text:
            if "확대교양" in text:
                area_hints.append({"영역": "확대", "세부영역": None})
            elif "일반교양" in text and "인간과문화" in text:
                area_hints.append({"영역": "일반", "세부영역": "인간과문화"})
            elif "일반교양" in text:
                area_hints.append({"영역": "일반", "세부영역": None})
            continue
        course_names.append(text)
    return course_names, area_hints

def is_standard_match(course_name, standard_names):
    """실제 과목명이 표준이수모형 과목명과 직접 또는 정규화 표기로 맞는지 검사한다."""
    course_normalized = normalize_course_name(course_name)
    for standard_name in standard_names:
        standard_normalized = normalize_course_name(standard_name)
        if (
            course_normalized == standard_normalized
            or standard_normalized in course_normalized
            or course_normalized in standard_normalized
        ):
            return True
    return False

def can_take_course(course, selected_course_numbers, academic_grade):
    """이미 수강한 과목과 학년 수준을 고려해 후보 과목을 거른다."""
    return (
        course["교과목번호"] not in selected_course_numbers
        and int(course["학점"]) > 0
        and int(course["권장학년"]) <= academic_grade
    )

def scenario_allows_course(course, scenario, standard_phase=False):
    """
    시나리오별 결핍 플래그를 반영한다.
    표준이수모형 우선 선발 단계에서는 너무 강하게 막지 않고 확률적으로 누락을 만든다.
    """
    area = course["영역"]
    subarea = course["세부영역"]

    if area == "전공" and subarea == "필수" and scenario.get("lack_major_required"):
        return random.random() < (0.25 if standard_phase else 0.08)
    if area == "전공" and subarea == "선택" and scenario.get("lack_major_elective"):
        return random.random() < (0.35 if standard_phase else 0.12)
    if area in ["개신기초", "자연이공계기초", "일반", "확대"] and scenario.get("lack_liberal_arts"):
        return random.random() < (0.35 if standard_phase else 0.12)
    if area == "개신기초" and scenario.get("lack_basic_liberal"):
        return random.random() < (0.35 if standard_phase else 0.10)
    if area == "일반" and scenario.get("lack_general_liberal"):
        return random.random() < (0.30 if standard_phase else 0.08)
    return True

def row_to_history(course, scenario, semester):
    """카탈로그 행을 course_history.csv 행 구조로 변환한다."""
    return {
        "student_id": scenario["student_id"],
        "수강년도": semester["수강년도"],
        "수강학기": semester["수강학기"],
        "교과목번호": course["교과목번호"],
        "교과목명": course["교과목명"],
        "이수구분": course["이수구분"],
        "영역": course["영역"],
        "세부영역": course["세부영역"],
        "학점": int(course["학점"]),
    }


def take_courses(candidates, selected_course_numbers, max_credits, max_courses=None):
    """후보 목록에서 남은 학점 범위 안에 들어가는 과목을 랜덤으로 고른다."""
    selected = []
    total = 0
    shuffled = list(candidates)
    random.shuffle(shuffled)

    for _, course in shuffled:
        credits = int(course["학점"])
        if credits <= 0:
            continue
        if total + credits > max_credits:
            continue
        selected.append(course)
        selected_course_numbers.add(course["교과목번호"])
        total += credits
        if max_courses is not None and len(selected) >= max_courses:
            break
    return selected

def select_major_courses(
    major_catalog,
    selected_course_numbers,
    academic_grade,
    max_credits,
    standard_names,
    scenario,
    preferred_subarea=None,
    standard_only=False,
    max_courses=None,
):
    """전공필수/전공선택 과목을 실제 lectures_database.csv 카탈로그에서 선택한다."""
    candidates = []
    for _, course in major_catalog.iterrows():
        if not can_take_course(course, selected_course_numbers, academic_grade):
            continue
        if preferred_subarea and course["세부영역"] != preferred_subarea:
            continue
        standard_match = is_standard_match(course["교과목명"], standard_names)
        if standard_only and not standard_match:
            continue
        if not scenario_allows_course(course, scenario, standard_phase=standard_only):
            continue
        candidates.append((standard_match, course))

    candidates.sort(key=lambda item: item[0], reverse=True)
    return take_courses(candidates, selected_course_numbers, max_credits, max_courses=max_courses)

def select_liberal_courses(
    liberal_catalog,
    selected_course_numbers,
    academic_grade,
    max_credits,
    standard_names,
    scenario,
    preferred_area=None,
    preferred_subarea=None,
    standard_only=False,
    max_courses=None,
):
    """교양 과목을 실제 liberal_arts.csv 카탈로그에서 선택한다."""
    candidates = []
    for _, course in liberal_catalog.iterrows():
        if not can_take_course(course, selected_course_numbers, academic_grade):
            continue
        if preferred_area and course["영역"] != preferred_area:
            continue
        if preferred_subarea and course["세부영역"] != preferred_subarea:
            continue
        standard_match = is_standard_match(course["교과목명"], standard_names)
        if standard_only and not standard_match:
            continue
        if not scenario_allows_course(course, scenario, standard_phase=standard_only):
            continue
        candidates.append((standard_match, course))

    candidates.sort(key=lambda item: item[0], reverse=True)
    return take_courses(candidates, selected_course_numbers, max_credits, max_courses=max_courses)

def distribute_credit_targets(total_credits, completed_semesters, scenario):
    """총 목표학점을 현실적인 학기별 목표학점으로 나눈다."""
    low, high = scenario.get("semester_credit_range", [12, 18])
    max_total = high * completed_semesters
    min_total = min(low * completed_semesters, max_total)
    total_credits = max(min_total, min(total_credits, max_total))

    targets = [random.randint(low, high) for _ in range(completed_semesters)]
    while sum(targets) != total_credits:
        diff = total_credits - sum(targets)
        adjustable = [
            index
            for index, value in enumerate(targets)
            if (diff > 0 and value < high) or (diff < 0 and value > low)
        ]
        if not adjustable:
            break
        index = random.choice(adjustable)
        targets[index] += 1 if diff > 0 else -1
    return targets

def next_fill_category(scenario, academic_grade, history_so_far, required):
    """
    다음에 채울 과목군을 고른다.
    학년이 올라갈수록 전공 비중이 커지고, 결핍 시나리오는 해당 영역 가중치를 낮춘다.
    """
    completed = calculate_completed_credits(history_so_far)
    liberal_done = sum(completed["교양"].values())
    major_required_done = completed["전공"]["필수"]
    major_elective_done = completed["전공"]["선택"]

    weights = {
        "major_required": 2 + academic_grade,
        "major_elective": 2 + academic_grade * 2,
        "basic_liberal": 4 if academic_grade <= 2 else 2,
        "science_liberal": 3 if academic_grade <= 2 else 1,
        "general_liberal": 2,
        "expanded_liberal": 1,
    }

    if major_required_done < min(required["전공"]["필수"], academic_grade * 7):
        weights["major_required"] += 4
    if major_elective_done < academic_grade * 9:
        weights["major_elective"] += 3
    if liberal_done < min(33, academic_grade * 10):
        weights["basic_liberal"] += 2
        weights["general_liberal"] += 2

    if scenario.get("lack_major_required"):
        weights["major_required"] = 1
    if scenario.get("lack_major_elective"):
        weights["major_elective"] = 1
    if scenario.get("lack_liberal_arts"):
        for key in ["basic_liberal", "science_liberal", "general_liberal", "expanded_liberal"]:
            weights[key] = 1
    if scenario.get("lack_basic_liberal"):
        weights["basic_liberal"] = 1
    if scenario.get("lack_general_liberal"):
        weights["general_liberal"] = 1

    choices = list(weights.keys())
    return random.choices(choices, weights=[weights[key] for key in choices], k=1)[0]

def add_courses_to_term(term_rows, courses, scenario, semester):
    """선택된 과목들을 현재 학기 행에 추가한다."""
    for course in courses:
        term_rows.append(row_to_history(course, scenario, semester))


def build_course_history(lectures, liberal_arts, standard_curriculum, graduation, scenario):
    """
    하나의 학생 시나리오를 기반으로 수강이력을 자동 생성한다.
    과목 선택은 항상 실제 lectures_database.csv / liberal_arts.csv 카탈로그에서만 수행한다.
    """
    major_catalog = prepare_major_catalog(lectures)
    liberal_catalog = prepare_liberal_catalog(liberal_arts)
    required = graduation_requirements(graduation, scenario["curriculum_year"])

    completed_semesters = calculate_max_completed_semesters(
        scenario["curriculum_year"],
        TARGET_YEAR,
        TARGET_SEMESTER,
    )

    if completed_semesters == 0:
        history = pd.DataFrame(columns=COURSE_HISTORY_COLUMNS)
        validate_history(history, lectures, liberal_arts, scenario)
        return history

    target_min, target_max = scenario["target_completed_credits"]
    target_total = random.randint(target_min, target_max)
    semesters = semester_sequence(scenario["curriculum_year"], completed_semesters)
    semester_targets = distribute_credit_targets(target_total, len(semesters), scenario)

    selected_course_numbers = set()
    rows = []

    for semester, semester_target in zip(semesters, semester_targets):
        term_rows = []
        standard_names, area_hints = standard_items_for_term(
            standard_curriculum,
            scenario["curriculum_year"],
            semester["학년"],
            semester["수강학기"],
        )
        academic_grade = semester["학년"]

        if scenario.get("prefer_standard_curriculum", True):
            # 표준이수모형에 실제 CSV 과목명으로 매칭되는 과목을 우선 배치한다.
            standard_room = min(semester_target, 18)
            liberal_standard = select_liberal_courses(
                liberal_catalog,
                selected_course_numbers,
                academic_grade,
                standard_room,
                standard_names,
                scenario,
                standard_only=True,
            )
            add_courses_to_term(term_rows, liberal_standard, scenario, semester)

            remaining_room = max(0, standard_room - sum(row["학점"] for row in term_rows))
            major_standard = select_major_courses(
                major_catalog,
                selected_course_numbers,
                academic_grade,
                remaining_room,
                standard_names,
                scenario,
                standard_only=True,
            )
            add_courses_to_term(term_rows, major_standard, scenario, semester)

        # 표준이수모형의 "확대교양 택1", "일반교양 인간과문화 택1" 같은 힌트를 실제 교양으로 채운다.
        for hint in area_hints:
            term_credits = sum(row["학점"] for row in term_rows)
            if term_credits >= semester_target:
                break
            courses = select_liberal_courses(
                liberal_catalog,
                selected_course_numbers,
                academic_grade,
                semester_target - term_credits,
                [],
                scenario,
                preferred_area=hint["영역"],
                preferred_subarea=hint["세부영역"],
                max_courses=1,
            )
            add_courses_to_term(term_rows, courses, scenario, semester)

        # 학기 목표학점에 도달할 때까지 시나리오와 학년 수준을 고려해 랜덤으로 채운다.
        attempts = 0
        while sum(row["학점"] for row in term_rows) < semester_target and attempts < 80:
            attempts += 1
            term_credits = sum(row["학점"] for row in term_rows)
            remaining = semester_target - term_credits
            category = next_fill_category(scenario, academic_grade, pd.DataFrame(rows + term_rows), required)

            if category == "major_required":
                courses = select_major_courses(
                    major_catalog,
                    selected_course_numbers,
                    academic_grade,
                    remaining,
                    [],
                    scenario,
                    preferred_subarea="필수",
                    max_courses=1,
                )
            elif category == "major_elective":
                courses = select_major_courses(
                    major_catalog,
                    selected_course_numbers,
                    academic_grade,
                    remaining,
                    [],
                    scenario,
                    preferred_subarea="선택",
                    max_courses=1,
                )
            elif category == "basic_liberal":
                courses = select_liberal_courses(
                    liberal_catalog,
                    selected_course_numbers,
                    academic_grade,
                    remaining,
                    [],
                    scenario,
                    preferred_area="개신기초",
                    max_courses=1,
                )
            elif category == "science_liberal":
                courses = select_liberal_courses(
                    liberal_catalog,
                    selected_course_numbers,
                    academic_grade,
                    remaining,
                    [],
                    scenario,
                    preferred_area="자연이공계기초",
                    max_courses=1,
                )
            elif category == "general_liberal":
                courses = select_liberal_courses(
                    liberal_catalog,
                    selected_course_numbers,
                    academic_grade,
                    remaining,
                    [],
                    scenario,
                    preferred_area="일반",
                    max_courses=1,
                )
            else:
                courses = select_liberal_courses(
                    liberal_catalog,
                    selected_course_numbers,
                    academic_grade,
                    remaining,
                    [],
                    scenario,
                    preferred_area="확대",
                    max_courses=1,
                )

            if not courses:
                continue
            add_courses_to_term(term_rows, courses, scenario, semester)

        rows.extend(term_rows)

    history = pd.DataFrame(rows, columns=COURSE_HISTORY_COLUMNS)
    validate_history(history, lectures, liberal_arts, scenario)
    return history

def validate_history(history, lectures, liberal_arts, scenario):
    """생성된 이력이 실제 과목만 사용했고 중복 수강이 없는지 검사한다."""
    if history.empty:
        if calculate_max_completed_semesters(scenario["curriculum_year"], TARGET_YEAR, TARGET_SEMESTER) == 0:
            return
        
        raise ValueError(f"{scenario['student_id']} 수강이력이 생성되지 않았습니다.")

    actual_courses = set(lectures["교과목명"]).union(set(liberal_arts["교과목명"]))
    missing_courses = sorted(set(history["교과목명"]) - actual_courses)
    if missing_courses:
        raise ValueError(f"원본 CSV에 없는 과목이 포함되었습니다: {missing_courses}")

    duplicated = history[history.duplicated(["student_id", "교과목번호"], keep=False)]
    if not duplicated.empty:
        raise ValueError(
            "중복 수강 과목이 있습니다:\n"
            + duplicated[["student_id", "교과목번호", "교과목명"]].to_string(index=False)
        )

    low, high = scenario.get("semester_credit_range", [12, 18])
    semester_credits = history.groupby(["수강년도", "수강학기"])["학점"].sum()
    if not semester_credits.between(low, high).all():
        raise ValueError(
            f"{scenario['student_id']} 학기별 학점이 범위를 벗어났습니다.\n"
            f"허용 범위: {low}-{high}\n{semester_credits}"
        )
    
    future_or_target = history[
        (history["수강년도"] > TARGET_YEAR)
        | ((history["수강년도"] == TARGET_YEAR) & (history["수강학기"] >= TARGET_SEMESTER))
    ]
    if not future_or_target.empty:
        raise ValueError(
            f"{TARGET_YEAR}-{TARGET_SEMESTER} 또는 이후 학기 수강이력이 포함되었습니다:\n"
            + future_or_target[["student_id", "수강년도", "수강학기", "교과목명"]].to_string(index=False)
        )
    
    target_min, target_max = scenario["target_completed_credits"]
    total = int(history["학점"].sum())
    if not target_min <= total <= target_max:
        raise ValueError(
            f"{scenario['student_id']} 총 취득학점 {total}이 목표 범위 "
            f"{target_min}-{target_max}를 벗어났습니다."
        )

def calculate_completed_credits(history):
    """생성된 course_history.csv 기준으로 completed 값을 집계한다."""
    completed = {
        "교양": {
            "개신기초": 0,
            "자연이공계기초": 0,
            "일반": 0,
            "확대": 0,
            "OCU_기타": 0,
        },
        "일반선택": 0,
        "전공": {"필수": 0, "선택": 0},
        "졸업학점": 0,
    }

    if history.empty:
        return completed

    completed["졸업학점"] = int(history["학점"].sum())
    for _, row in history.iterrows():
        credits = int(row["학점"])
        if row["영역"] in completed["교양"]:
            completed["교양"][row["영역"]] += credits
        elif row["영역"] == "전공":
            completed["전공"][row["세부영역"]] += credits
        elif row["영역"] == "일반선택":
            completed["일반선택"] += credits
    return completed

def generate_student(scenario, history, graduation):
    """한 학생의 students.json 엔트리를 생성한다."""
    required = graduation_requirements(graduation, scenario["curriculum_year"])
    completed = calculate_completed_credits(history)
    completed_semesters = calculate_max_completed_semesters(
        scenario["curriculum_year"],
        TARGET_YEAR,
        TARGET_SEMESTER,
    )
    grade = calculate_current_grade(
        scenario["curriculum_year"],
        TARGET_YEAR,
        TARGET_SEMESTER,
    )

    return {
        "student_id": scenario["student_id"],
        "name": scenario["name"],
        "grade": scenario["grade"],
        "college": scenario.get("college", "전자정보대학"),
        "department": scenario.get("department", "컴퓨터공학과"),
        "completed_semesters": scenario["completed_semesters"],
        "curriculum_year": scenario["curriculum_year"],
        "credits": {
            "교양": {
                area: {
                    "required": required["교양"][area],
                    "completed": completed["교양"][area],
                }
                for area in ["개신기초", "자연이공계기초", "일반", "확대", "OCU_기타"]
            },
            "일반선택": {
                "required": required["일반선택"],
                "completed": completed["일반선택"],
            },
            "전공": {
                major_type: {
                    "required": required["전공"][major_type],
                    "completed": completed["전공"][major_type],
                }
                for major_type in ["필수", "선택"]
            },
            "졸업학점": {
                "required": required["졸업학점"],
                "completed": completed["졸업학점"],
            },
        },
    }

def build_students_json(scenarios, all_history, graduation):
    """전체 학생 목록을 students.json 구조로 만든다."""
    students = []
    for scenario in scenarios:
        student_history = all_history[all_history["student_id"] == scenario["student_id"]]
        students.append(generate_student(scenario, student_history, graduation))
    return students

def main():
    random.seed(RANDOM_SEED)

    lectures, liberal_arts, standard_curriculum, graduation = read_source_files()

    histories = []
    for scenario in student_scenarios:
        history = build_course_history(
            lectures,
            liberal_arts,
            standard_curriculum,
            graduation,
            scenario,
        )
        histories.append(history)

    all_history = pd.concat(histories, ignore_index=True)
    students = build_students_json(student_scenarios, all_history, graduation)

    all_history.to_csv(COURSE_HISTORY_PATH, index=False, encoding="utf-8-sig")
    STUDENTS_PATH.write_text(json.dumps(students, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"RANDOM_SEED: {RANDOM_SEED}")
    print(f"생성 완료: {STUDENTS_PATH}")
    print(f"생성 완료: {COURSE_HISTORY_PATH}")
    print("\n학생별 총 취득학점")
    print(all_history.groupby("student_id")["학점"].sum().to_string())
    print("\n학생별 학기별 학점")
    print(all_history.groupby(["student_id", "수강년도", "수강학기"])["학점"].sum().to_string())


if __name__ == "__main__":
    main()