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

# 건물 코드 앞뒤 공백 제거
buildings_df["건물 코드"] = buildings_df["건물 코드"].astype(str).str.strip()

# 건물 코드를 기준으로 빠르게 조회할 수 있도록 index 설정
buildings_df = buildings_df.set_index("건물 코드")


# 건물 좌표 조회 함수
def get_building_coordinates(building_code):
    """
    건물 코드를 입력받아 buildings.csv에서 위도, 경도를 조회합니다.

    반환:
        (위도, 경도)

    예:
        S1-1 -> (36.6279, 127.4567)
    """
    building_code = str(building_code).strip()

    if building_code == "" or building_code.lower() == "nan":
        raise ValueError("건물 코드가 비어 있습니다.")

    if building_code not in buildings_df.index:
        raise ValueError(f"존재하지 않는 건물 코드입니다: {building_code}")

    latitude = buildings_df.loc[building_code, "위도"]
    longitude = buildings_df.loc[building_code, "경도"]

    if pd.isna(latitude) or pd.isna(longitude):
        raise ValueError(f"위도/경도 값이 누락되었습니다: {building_code}")

    if str(latitude).strip() == "" or str(longitude).strip() == "":
        raise ValueError(f"위도/경도 값이 빈 값입니다: {building_code}")

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except ValueError:
        raise ValueError(f"잘못된 좌표 형식입니다: {building_code}")

    return latitude, longitude

# Haversine 거리 계산 함수
def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """
    Haversine 공식을 사용하여 두 좌표 사이의 직선거리를 계산합니다.

    입력:
        lat1, lon1: 출발지 위도, 경도
        lat2, lon2: 도착지 위도, 경도

    반환:
        거리, meter 단위
    """
    # 위도와 경도를 degree에서 radian으로 변환
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # 좌표 차이 계산
    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad

    # Haversine 공식
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance_meters = EARTH_RADIUS_METERS * c

    return distance_meters
