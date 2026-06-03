import pandas as pd

def parse_day_and_period(day_raw, period_raw):
    """
    요일과 교시 문자열을 시각화 팀원이 가공 없이 바로 쓸 수 있게 텍스트와 숫자 형태로만 정제
    """
    if pd.isna(day_raw) or pd.isna(period_raw):
        return []
        
    PERIOD_TO_TIME = {
        0: ("08:00", "09:00"),
        1: ("09:00", "10:00"),
        2: ("10:00", "11:00"),
        3: ("11:00", "12:00"),
        4: ("12:00", "13:00"),
        5: ("13:00", "14:00"),
        6: ("14:00", "15:00"),
        7: ("15:00", "16:00"),
        8: ("16:00", "17:00"),
        9: ("17:00", "18:00"),
        10: ("18:00", "19:00"),
        11: ("19:00", "20:00"),
        12: ("20:00", "21:00"),
        13: ("21:00", "22:00"),
        14: ("22:00", "23:00")
    }

    time_slots = []
    
    # 파이프(|)를 기준으로 다중 요일/교시 분할
    day_splits = str(day_raw).split('|')
    period_splits = str(period_raw).replace('"', '').split('|')
    
    for day_chunk, period_chunk in zip(day_splits, period_splits):
        day_str = day_chunk.strip()
        
         # 1~3 형태 처리
        if '~' in period_chunk:

            start_period, end_period = map(
                int,
                period_chunk.split('~')
            )

            periods = list(range(start_period, end_period + 1))

        else:
            # 1,2,3 형태 처리
            periods = sorted([
                int(p.strip())
                for p in period_chunk.split(',')
                if p.strip().isdigit()
            ])

        if not periods:
            continue

        start_period = periods[0]
        end_period = periods[-1]

        start_time = PERIOD_TO_TIME[start_period][0]
        end_time = PERIOD_TO_TIME[end_period][1]

        time_slots.append({
            "day": day_str,
            "start_period": start_period,
            "end_period": end_period,
            "time_range": f"{start_time} ~ {end_time}"
        })

    return time_slots
