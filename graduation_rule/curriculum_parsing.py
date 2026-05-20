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
