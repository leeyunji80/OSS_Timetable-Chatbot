class Course:
    def __init__(self, name, day, start, end):
        self.name = name #교과목 명
        self.day = day
        self.start = start
        self.end = end

    def __repr__(self):
        return f"{self.name}({self.day} {self.start}-{self.end})"
    

