class Course:
    def __init__(self, name, day, start, end):
        self.name = name #교과목 명
        self.day = day
        self.start = start
        self.end = end

    def __repr__(self):
        return f"{self.name}({self.day} {self.start}-{self.end})"
    
# 강의 2개가 겹치는 지 확인
def is_conflict(c1, c2):
    if c1.day != c2.day:
        return False
    return not (c1.end <= c2.start or c2.end <= c1.start)

# 여러 개의 강의가 겹치는 지 확인
def is_valid(schedule):
    day_map = {}

    # 요일별로 묶기
    for c in schedule:
        day_map.setdefault(c.day, []).append(c)

    # 같은 요일끼리만 비교
    for day_courses in day_map.values():
        for i in range(len(day_courses)):
            for j in range(i + 1, len(day_courses)):
                if is_conflict(day_courses[i], day_courses[j]):
                    return False

    return True