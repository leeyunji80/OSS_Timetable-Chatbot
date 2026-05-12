import pandas as pd
import io
from itertools import combinations

def generate_timetable_combinations(csv_data, target_grade, num_to_pick=5, exclude_days=None):
    # 1. 데이터 로드
    df = pd.read_csv(io.StringIO(csv_data))
    
    # 2. 기본 필터링 (학년 및 야간 강좌 제외)
    # LLM이 "2학년꺼 짜줘"라고 하면 해당 학년만 남깁니다.
    mask = df['수강 대상'].str.contains(target_grade) & ~df['수강 대상'].str.contains("야간")
    filtered_df = df[mask].copy()
    
    # 3. 사용자 요구사항 반영 (특정 요일 제외)
    # 예: "금요일 공강 만들어줘" -> 금요일 수업이 포함된 행 삭제
    if exclude_days:
        for day in exclude_days:
            filtered_df = filtered_df[~filtered_df['강의시간/강의실'].str.contains(day)]
    
    # 4. 과목명 리스트 추출
    course_pool = filtered_df['교과목명'].unique().tolist()
    
    # 5. 시간표 조합 생성
    # pool에 있는 과목들 중 사용자가 원하는 개수(num_to_pick)만큼 뽑는 모든 경우의 수
    all_combinations = list(combinations(course_pool, num_to_pick))
    
    # 6. 결과 반환 (리스트의 리스트 형태)
    # 이 결과값을 '충돌 방지 로직' 브랜치에 있는 함수에 넣어서 검증하면 됩니다.
    return [list(combo) for combo in all_combinations]

# --- 사용 예시 ---
raw_data = """개설 연도,개설 학과,수강 대상,교과목명,강의시간/강의실... (데이터 생략)"""

# LLM 담당자가 부를 함수 형태
# "2학년 과목 중에서 금요일 수업 빼고 5개 골라줘"
results = generate_timetable_combinations(
    csv_data=raw_data, 
    target_grade="2학년", 
    num_to_pick=5, 
    exclude_days=['금']
)

print(f"생성된 조합 개수: {len(results)}")
print(f"첫 번째 조합 예시: {results[0] if results else '없음'}")