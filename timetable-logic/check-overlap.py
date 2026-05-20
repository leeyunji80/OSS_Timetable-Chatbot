# -----------------------------
# 시간 충돌 검사
# -----------------------------

def is_conflict(course1, course2):

    for slot1 in course1["time_slots"]:
        for slot2 in course2["time_slots"]:

            # 요일 + 교시가 같으면 충돌
            if (
                slot1["day"] == slot2["day"]
                and slot1["period"] == slot2["period"]
            ):
                return True

    return False


# -----------------------------
# 시간표 전체 충돌 검사
# -----------------------------

def is_valid_combination(schedule):

    for i in range(len(schedule)):
        for j in range(i + 1, len(schedule)):

            if is_conflict(schedule[i], schedule[j]):
                return False

    return True