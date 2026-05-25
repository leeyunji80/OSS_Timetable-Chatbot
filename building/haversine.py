import pandas as pd
import math

BUILDINGS_CSV = "buildings.csv"
BUILDING_PAIRS_CSV = "building_pairs.csv"
OUTPUT_CSV = "building_distance.csv"

# 지구 반지름, meter 단위
EARTH_RADIUS_METERS = 6371000

# 캠퍼스 내부 실제 이동거리는 직선거리보다 길 수 있으므로 1.2배 보정
DISTANCE_CORRECTION_RATE = 1.2

# 평균 보행 속도: 분당 80m
WALKING_SPEED_METERS_PER_MINUTE = 80


# CSV 파일 읽기
buildings_df = pd.read_csv(BUILDINGS_CSV, encoding="utf-8-sig")
pairs_df = pd.read_csv(BUILDING_PAIRS_CSV, encoding="utf-8-sig")

# 필수 컬럼 확인
required_building_columns = ["건물 코드", "위도", "경도"]
required_pair_columns = ["출발 건물", "도착 건물"]

for column in required_building_columns:
    if column not in buildings_df.columns:
        raise ValueError(f"buildings.csv에 '{column}' 컬럼이 없습니다.")

for column in required_pair_columns:
    if column not in pairs_df.columns:
        raise ValueError(f"building_pairs.csv에 '{column}' 컬럼이 없습니다.")
