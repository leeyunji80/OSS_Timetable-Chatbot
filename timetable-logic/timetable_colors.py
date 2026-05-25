# -----------------------------
# 과목 색상 팔레트
# -----------------------------

COLOR_PALETTE = [
    {
        "background": "#FFCDD2",
        "text": "#000000"
    },
    {
        "background": "#F8BBD0",
        "text": "#000000"
    },
    {
        "background": "#E1BEE7",
        "text": "#000000"
    },
    {
        "background": "#D1C4E9",
        "text": "#000000"
    },
    {
        "background": "#C5CAE9",
        "text": "#000000"
    },
    {
        "background": "#BBDEFB",
        "text": "#000000"
    },
    {
        "background": "#B2EBF2",
        "text": "#000000"
    },
    {
        "background": "#C8E6C9",
        "text": "#000000"
    },
    {
        "background": "#DCEDC8",
        "text": "#000000"
    },
    {
        "background": "#FFF9C4",
        "text": "#000000"
    }
]


# -----------------------------
# 과목별 색상 지정
# -----------------------------

def assign_course_colors(schedule):

    course_color_map = {}

    for index, course in enumerate(schedule):

        color = COLOR_PALETTE[index % len(COLOR_PALETTE)]

        course_color_map[course["name"]] = color

    return course_color_map