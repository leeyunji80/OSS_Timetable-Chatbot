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
