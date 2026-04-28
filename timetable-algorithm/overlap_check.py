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

