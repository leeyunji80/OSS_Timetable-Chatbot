import argparse
import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader


def normalize_text(text: str) -> str:
    """PDF에서 추출된 텍스트의 공백과 특수 문자를 정리"""
    text = text.strip()
    text = text.replace("：", ":")
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def collect_fragments(page):
    """
    PDF 한 페이지에서 텍스트 조각과 좌표를 추출

    반환 형식:
    [
        {"x": x좌표, "y": y좌표, "text": 텍스트},
        ...
    ]
    """
    fragments = []

    def visitor(text, cm, tm, font_dict, font_size):
        text = normalize_text(text)
        if text:
            fragments.append(
                {
                    "x": float(tm[4]),
                    "y": float(tm[5]),
                    "text": text,
                }
            )

    page.extract_text(visitor_text=visitor)
    return fragments

def guess_year(page_text: str, page_index: int, pdf_path: str) -> str:
    """
    페이지의 년도 추출

    2021~2025 페이지는 PDF 텍스트에서 년도가 잡히고,
    2026 페이지처럼 년도가 누락되는 경우 파일명 2021-2026을 기준으로 보정
    """
    years = re.findall(r"20\d{2}", page_text)

    if years:
        return years[0]

    file_years = re.findall(r"20\d{2}", Path(pdf_path).stem)

    if len(file_years) >= 2:
        start_year = int(file_years[0])
        return str(start_year + page_index)

    return ""

def group_rows_by_y(fragments, tolerance: float = 3.2):
    """비슷한 y좌표를 가진 텍스트 조각들을 같은 줄로 묶음"""
    rows = []

    for frag in sorted(fragments, key=lambda item: item["y"]):
        if not rows or abs(rows[-1]["y"] - frag["y"]) > tolerance:
            rows.append({"y": frag["y"], "items": []})

        rows[-1]["items"].append(frag)

    return rows

def find_grade_centers(fragments):
    """
    표의 학년 숫자 1, 2, 3, 4 위치를 찾음

    학년 숫자는 보통 왼쪽 열에 있으므로 x좌표 70~110 사이에서 탐색
    """
    centers = {}

    for frag in fragments:
        text = frag["text"]

        if 70 <= frag["x"] <= 110 and text in {"1", "2", "3", "4"}:
            centers[int(text)] = frag["y"]

    return centers


def get_grade_by_y(y: float, grade_centers: dict[int, float]):
    """현재 줄의 y좌표가 어느 학년 영역에 속하는지 판단"""
    if len(grade_centers) < 4:
        return None

    y_values = [grade_centers[i] for i in [1, 2, 3, 4]]

    gap_1_2 = y_values[1] - y_values[0]
    gap_3_4 = y_values[3] - y_values[2]

    top_limit = y_values[0] - gap_1_2 * 0.58
    bottom_limit = y_values[3] + gap_3_4 * 0.45

    if y < top_limit or y > bottom_limit:
        return None

    return min([1, 2, 3, 4], key=lambda grade: abs(y - grade_centers[grade]))

def find_min_x(fragments, pattern: str, default=None):
    """특정 텍스트 패턴이 등장하는 최소 x좌표를 찾음"""
    xs = [
        frag["x"]
        for frag in fragments
        if re.search(pattern, frag["text"])
    ]

    if xs:
        return min(xs)

    return default


def detect_column_ranges(fragments):
    """
    PDF 페이지별 1학기/2학기 열의 x좌표 범위를 추정

    페이지마다 PDF 내부 좌표가 조금씩 달라서 고정 좌표 대신
    '대학글쓰기', '역사와비판적사고', '전공선택' 같은 기준 텍스트 위치를 이용
    """
    semester_1_start = find_min_x(fragments, r"대학글쓰기", 126) - 15
    semester_2_start = find_min_x(fragments, r"역사와비판적사고", 292) - 3

    note_candidates = [
        frag["x"]
        for frag in fragments
        if frag["x"] > semester_2_start + 80
        and re.search(r"개신기초교양|전공선택|전공필수|합계|일반교양", frag["text"])
    ]

    note_start = min(note_candidates) if note_candidates else semester_2_start + 180

    return {
        1: (semester_1_start, semester_2_start),
        2: (semester_2_start, note_start - 2),
    }

def is_credit_fragment(text: str) -> bool:
    """3-3-0 같은 시수 정보 조각인지 확인"""
    return bool(re.search(r"\d+\s*-\s*\d+\s*-\s*\d+", text)) or text.startswith(("#", ":"))


def assemble_line(items):
    """
    같은 줄의 텍스트 조각들을 하나의 문자열로 조립

    PDF에서 '# : 3-3-0'이 과목명보다 앞에 추출되는 경우가 있어
    과목명 조각을 먼저, 시수 정보 조각을 뒤로 보냄
    """
    normal_parts = []
    credit_parts = []

    for frag in sorted(items, key=lambda item: item["x"]):
        text = normalize_text(frag["text"])

        if is_credit_fragment(text):
            credit_parts.append(text)
        else:
            normal_parts.append(text)

    return normalize_text(" ".join(normal_parts + credit_parts))


def has_credit_info(line: str) -> bool:
    """줄 안에 3-3-0 형태의 시수 정보가 있는지 확인"""
    return bool(re.search(r"\d+\s*-\s*\d+\s*-\s*\d+", line))


def is_credit_only(line: str) -> bool:
    """줄 전체가 시수 정보뿐인지 확인"""
    return bool(re.fullmatch(r"[:#\s]*\d+\s*-\s*\d+\s*-\s*\d+\s*", line))


def split_subject_lines(lines):
    """
    셀 안의 줄들을 과목 단위로 묶음

    예:
    기초컴퓨터프로그래밍 개신기초④:
    3-2-2

    위처럼 시수 정보가 다음 줄에 있으면 이전 과목명과 합침
    """
    subjects = []
    buffer = ""

    for line in lines:
        line = normalize_text(line)

        if not line:
            continue

        if is_credit_only(line):
            if buffer:
                subjects.append(f"{buffer} {line}".strip())
                buffer = ""
            continue

        if has_credit_info(line):
            if buffer:
                subjects.append(f"{buffer} {line}".strip())
                buffer = ""
            else:
                subjects.append(line)
            continue

        buffer = f"{buffer} {line}".strip() if buffer else line

    if buffer:
        subjects.append(buffer)

    return subjects
