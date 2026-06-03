"""
buildings.csv에서 건물 코드만 추출한 뒤,
방향 중복이 없는 모든 건물 쌍을 생성하여 building_pairs.csv로 저장한다.

사용 예:
    python generate_building_pairs.py

입력 파일:
    buildings.csv

출력 파일:
    building_pairs.csv
"""

from itertools import combinations

import pandas as pd


# 입력/출력 파일명을 상수로 관리하면,
# 나중에 파일명이 바뀌어도 이 부분만 수정하면 된다.
INPUT_FILE = "buildings.csv"
OUTPUT_FILE = "building_pairs.csv"


def find_building_code_column(df: pd.DataFrame) -> str:
    """
    buildings.csv에서 건물 코드 컬럼명을 찾는다.

    예시 데이터는 building_code를 사용하지만,
    실제 CSV가 한국어 컬럼명인 '건물 코드'를 사용할 수도 있으므로
    두 경우를 모두 지원한다.
    """
    candidate_columns = [
        "building_code",
        "건물 코드",
        "건물코드",
    ]

    for column in candidate_columns:
        if column in df.columns:
            return column

    raise ValueError(
        "건물 코드 컬럼을 찾을 수 없습니다. "
        "CSV에 'building_code' 또는 '건물 코드' 컬럼이 있는지 확인하세요."
    )


def main() -> None:
    """
    건물 조합 CSV를 생성하는 메인 함수.
    """
    # utf-8-sig 인코딩을 사용하면 Excel에서 한글 컬럼명이 깨질 가능성을 줄일 수 있다.
    buildings_df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")

    # 입력 CSV에서 건물 코드 컬럼을 찾는다.
    building_code_column = find_building_code_column(buildings_df)

    # 건물 코드만 추출한다.
    # dropna(): 비어 있는 건물 코드는 제외
    # astype(str): 숫자처럼 인식된 코드도 문자열로 변환
    # str.strip(): 앞뒤 공백 제거
    # drop_duplicates(): 같은 건물 코드가 여러 번 있어도 조합에는 한 번만 사용
    building_codes = (
        buildings_df[building_code_column]
        .dropna()
        .astype(str)
        .str.strip()
        .loc[lambda codes: codes != ""]
        .drop_duplicates()
        .tolist()
    )

    # itertools.combinations(building_codes, 2)는 순서가 없는 2개 조합만 생성한다.
    # 예를 들어 (E8-1, N16)이 생성되면 (N16, E8-1)은 생성하지 않는다.
    building_pairs = list(combinations(building_codes, 2))

    # 출력 CSV의 컬럼명을 요구사항에 맞게 설정한다.
    pairs_df = pd.DataFrame(
        building_pairs,
        columns=["출발 건물", "도착 건물"],
    )

    # 생성된 건물 조합을 CSV 파일로 저장한다.
    # index=False를 지정해야 pandas의 행 번호 컬럼이 CSV에 추가되지 않는다.
    pairs_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    # 실행 결과를 터미널에서 바로 확인할 수 있도록 조합 개수를 출력한다.
    print(f"건물 수: {len(building_codes)}개")
    print(f"생성된 건물 조합 수: {len(building_pairs)}개")
    print(f"저장 완료: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
