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
