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
