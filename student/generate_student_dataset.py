import json
import random
import re
from pathlib import Path

import pandas as pd


# seed 값만 바꾸면 같은 시나리오에서 다른 랜덤 데이터셋을 재현 가능하게 만들 수 있음
RANDOM_SEED = 42

DOWNLOAD_DIR = Path(r"C:\Users\leeyu\Downloads")
OUTPUT_DIR = Path(__file__).resolve().parent

LECTURES_PATH = DOWNLOAD_DIR / "lectures_database.csv"
LIBERAL_ARTS_PATH = DOWNLOAD_DIR / "liberal_arts.csv"
STANDARD_CURRICULUM_PATH = DOWNLOAD_DIR / "standard_curriculum.csv"
GRADUATION_PATH = DOWNLOAD_DIR / "graduation.json"

STUDENTS_PATH = OUTPUT_DIR / "students.json"
COURSE_HISTORY_PATH = OUTPUT_DIR / "course_history.csv"

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