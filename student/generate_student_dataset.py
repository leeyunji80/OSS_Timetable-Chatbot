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
