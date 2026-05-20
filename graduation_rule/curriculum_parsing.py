import argparse
import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader


KEEP_SUBJECTS = {
    "일반교양인간과문화분야택1",
}


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

def clean_subject_name(text: str) -> str:
    """
    최종 CSV에 저장할 과목명만 남김

    제거:
    - #
    - 괄호 내부
    - 3-3-0 같은 시수
    - 개신기초, 일반교양, 자연이공계기초과학 등 교양 구분
    """
    text = normalize_text(text)

    text = text.replace("#", "")
    text = text.replace("（", "(").replace("）", ")")

    text = re.sub(r"\d+\s*-\s*\d+\s*-\s*\d+.*$", " ", text)
    text = re.sub(r":.*$", " ", text)
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[①②③④⑤⑥⑦⑧⑨⑩]", " ", text)

    # "일반교양인간과문화분야 택1"은 교양 분류 문구가 아니라 실제 이수모형에
    # 들어가는 과목/영역명이므로, 아래의 일반 교양 분류 제거 규칙보다 먼저 보존합니다.
    if re.search(r"일\s*반\s*교\s*양\s*인\s*간\s*과\s*문\s*화\s*분\s*야\s*택\s*1", text):
        return "일반교양인간과문화분야택1"

    text = re.sub(
        r"(개\s*신\s*기(\s*초)?|일\s*반\s*교(\s*양)?|자\s*연\s*이\s*공\s*계\s*기\s*초\s*과\s*학).*",
        " ",
        text,
    )

    text = re.sub(r"학년도|전공과정|표준이수모형|학기|학년|비\s*고", " ", text)
    text = re.sub(r"^[\s:;,\-]+|[\s:;,\-]+$", "", text)
    text = re.sub(r"^\d+(?=[가-힣A-Za-z])", "", text)

    # 과목명 내부의 불필요한 공백 제거
    text = re.sub(r"\s+", "", text)

    # PDF 추출 순서/누락 보정
    corrections = {
        "프로그래밍C/C++": "C/C++프로그래밍",
        "기초컴퓨터프로그래밍개신기": "기초컴퓨터프로그래밍",
        "응용컴퓨터프로그래밍개신기": "응용컴퓨터프로그래밍",
        "빅데이터의이해와활용일반교": "빅데이터의이해와활용",
        "오픈소스이해및실습SW": "오픈소스SW이해및실습",
        "SW": "오픈소스SW이해및실습",
        "컴퓨터전": "컴퓨터비전",
        "AI": "AI증강프로그래밍",
    }

    return corrections.get(text, text)

def is_valid_subject(subject: str) -> bool:
    """과목명이 아닌 잡음 제거"""
    if not subject:
        return False

    if subject in KEEP_SUBJECTS:
        return True

    if len(subject) < 2:
        return False

    if re.fullmatch(r"[\d\s:,\-]+", subject):
        return False

    noise_keywords = [
        "전공선택",
        "전공필수",
        "합계",
        "학점",
        "총",
        "미이수",
        "졸업불가",
        "컴퓨터공학과",
    ]

    return not any(keyword in subject for keyword in noise_keywords)

def parse_pdf_page(page, page_index: int, pdf_path: str):
    """PDF 한 페이지에서 년도, 학년, 학기, 과목명 추출"""
    page_text = page.extract_text() or ""
    year = guess_year(page_text, page_index, pdf_path)

    fragments = collect_fragments(page)
    grade_centers = find_grade_centers(fragments)
    column_ranges = detect_column_ranges(fragments)

    cells = {
        (grade, semester): []
        for grade in [1, 2, 3, 4]
        for semester in [1, 2]
    }

    for row in group_rows_by_y(fragments):
        grade = get_grade_by_y(row["y"], grade_centers)

        if grade is None:
            continue

        for semester, (x_min, x_max) in column_ranges.items():
            items = [
                item
                for item in row["items"]
                if x_min <= item["x"] < x_max
            ]

            if items:
                cells[(grade, semester)].append(assemble_line(items))

    rows = []

    for (grade, semester), lines in cells.items():
        subject_lines = split_subject_lines(lines)

        for raw_subject in subject_lines:
            subject = clean_subject_name(raw_subject)

            if not is_valid_subject(subject):
                continue

            rows.append(
                {
                    "년도": year,
                    "학년": grade,
                    "학기": semester,
                    "과목명": subject,
                }
            )

    return rows


def parse_curriculum_pdf(pdf_path: str) -> pd.DataFrame:
    """전체 PDF를 파싱하여 DataFrame 생성"""
    reader = PdfReader(pdf_path)

    all_rows = []

    for page_index, page in enumerate(reader.pages):
        page_rows = parse_pdf_page(page, page_index, pdf_path)
        all_rows.extend(page_rows)

    df = pd.DataFrame(all_rows, columns=["년도", "학년", "학기", "과목명"])
    df = df.drop_duplicates(ignore_index=True)

    return df

def find_default_pdf() -> str:
    """
    F5로 실행할 때 PDF 경로를 직접 입력하지 않아도 되도록 조치
    """
    search_roots = [
        Path.cwd(),                    # VS Code에서 열린 프로젝트 폴더
        Path(__file__).resolve().parent,  # 현재 파이썬 파일이 있는 폴더
        Path(__file__).resolve().parent.parent,
    ]

    pdf_files = []

    for root in search_roots:
        if root.exists():
            pdf_files.extend(root.glob("*.pdf"))
            pdf_files.extend(root.rglob("*.pdf"))

    # 중복 제거
    pdf_files = list(dict.fromkeys(pdf_files))

    if not pdf_files:
        raise FileNotFoundError(
            "PDF 파일을 찾지 못했습니다. "
            "VS Code 프로젝트 폴더 또는 graduation_rule 폴더에 PDF를 넣어주세요."
        )

    # 교육과정 PDF를 우선 선택
    preferred_keywords = ["교육과정", "컴퓨터공학과", "2021-2026", "curriculum"]

    for keyword in preferred_keywords:
        for pdf in pdf_files:
            if keyword.lower() in pdf.name.lower():
                return str(pdf)

    # PDF가 하나뿐이면 그 파일 사용
    if len(pdf_files) == 1:
        return str(pdf_files[0])

    raise FileExistsError(
        "PDF 파일이 여러 개라 자동 선택할 수 없습니다.\n"
        + "\n".join(str(pdf) for pdf in pdf_files)
    )

def main():
    parser = argparse.ArgumentParser(description="컴퓨터공학과 표준이수모형 PDF를 CSV로 변환")

    # F5 실행을 위해 pdf 인자를 선택 사항으로 변경
    parser.add_argument(
        "pdf",
        nargs="?",
        default=None,
        help="입력 PDF 파일 경로. 생략하면 현재 프로젝트에서 자동 탐색합니다.",
    )

    parser.add_argument(
        "--output",
        default="standard_curriculum.csv",
        help="출력 CSV 파일 경로",
    )

    args = parser.parse_args()

    pdf_path = args.pdf if args.pdf else find_default_pdf()

    print(f"사용 PDF: {pdf_path}")

    df = parse_curriculum_pdf(pdf_path)
    df.to_csv(args.output, index=False, encoding="utf-8-sig")

    print(f"CSV 저장 완료: {args.output}")
    print(f"추출 과목 수: {len(df)}")


if __name__ == "__main__":
    main()
