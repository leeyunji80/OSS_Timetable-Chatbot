import os
import time
from PIL import Image, ImageDraw, ImageFont

def draw_timetable_image(alternative_data, student_id="guest"):
    """
    입력된 데이터의 가장 늦은 시간에 맞춰 높이가 '자동으로 조절'되는 시간표 생성 함수입니다.
    모든 시간 데이터는 정시("09:00", "13:00" 등)로 딱 떨어진다고 가정합니다.
    """
    # ---------------------------------------------------------------------------
    # 1. 입력 데이터를 기반으로 시간표의 최대 종료 시간 계산 (동적 높이 설정)
    # ---------------------------------------------------------------------------
    default_start_hour = 9
    default_end_hour = 18  # 기본 오후 6시
    min_course_hour = default_start_hour
    max_course_hour = default_end_hour

    courses = alternative_data.get("courses", [])
    for course in courses:
        for sch in course.get("schedule", []):
            time_range = sch.get("time")  # 예: "09:00-13:00" 또는 "17:00-21:00"
            if time_range and "-" in time_range:
                try:
                    start_time_str, end_time_str = time_range.split("-")

                    start_hour = int(start_time_str.split(":")[0])
                    end_hour = int(end_time_str.split(":")[0])

                    if start_hour < min_course_hour:
                        min_course_hour = start_hour

                    if end_hour > max_course_hour:
                        max_course_hour = end_hour
                except Exception:
                    pass

    # 가장 늦은 수업 종료 시간에 맞춰서 시간표 마감 시간 설정 (최소 오후 6시 보장)
    timetable_start_hour = min_course_hour
    timetable_end_hour = max_course_hour

    # ---------------------------------------------------------------------------
    # 2. 레이아웃 상수 및 동적 캔버스 크기 계산
    # ---------------------------------------------------------------------------
    start_x = 80
    start_y = 100
    col_width = 120    # 요일 칸 가로 너비
    width = 750
    hour_height = 70   # 1시간당 세로 높이 총 픽셀

    # 총 표시해야 할 시간의 수 (예: 9시 ~ 18시면 9시간)
    total_hours = timetable_end_hour - timetable_start_hour

    # 위쪽 여백(start_y) + 시간표 총 높이 + 아래쪽 여백(80)을 더해 높이를 자동 계산합니다.
    height = start_y + (total_hours * hour_height) + 80

    # 캔버스 생성
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    
    # ---------------------------------------------------------------------------
    # 3. 폰트 설정 (환경에 맞게 경로 수정 필요)
    # ---------------------------------------------------------------------------
        # 간단하게
    font_title = ImageFont.truetype("malgun.ttf", 22)
    font_course = ImageFont.truetype("malgun.ttf", 15)
    font_room = ImageFont.truetype("malgun.ttf", 12)
    font_sub = ImageFont.truetype("malgun.ttf", 11)

    # 상단 타이틀 표기
    title_text = alternative_data.get("timetable_title", "추천 시간표")
    draw.text((30, 30), title_text, fill="#2c3e50", font=font_title)

    days = ["월", "화", "수", "목", "금"]
    day_map = {day: idx for idx, day in enumerate(days)}

    # ---------------------------------------------------------------------------
    # 4. 배경 그리드(요일 텍스트 및 시간선) 그리기
    # ---------------------------------------------------------------------------
    # 요일 헤더 그리기
    for i, day in enumerate(days):
        x = start_x + (i * col_width)
        # 글자가 칸 중앙에 오도록 살짝 보정하여 그리기
        bbox = draw.textbbox((0, 0), day, font=font_course)

        draw.text(
            (
                x + (col_width - (bbox[2] - bbox[0])) / 2,
                start_y - 35
            ),
            day,
            fill="#1f2937",
            font=font_course
        )

    # 가로 시간선 및 시간 라벨 그리기
    for hour in range(timetable_start_hour, timetable_end_hour + 1):
        current_y = start_y + ((hour - timetable_start_hour) * hour_height)
        draw.text((20, current_y - 7), f"{hour:02d}:00", fill="#7f8c8d", font=font_sub)
        draw.line([(start_x, current_y), (start_x + len(days) * col_width, current_y)], fill="#e2e8f0", width=1)

    # 세로 요일 구분선 그리기
    for i in range(len(days) + 1):
        x = start_x + (i * col_width)
        draw.line([(x, start_y), (x, start_y + total_hours * hour_height)], fill="#e2e8f0", width=1)

    # ---------------------------------------------------------------------------
    # 5. 시간축 좌표 매핑 함수 (정시 기준)
    # ---------------------------------------------------------------------------
    def time_to_y(time_str):
        # "09:00" -> 9 추출
        hour = int(time_str.split(":")[0])
        return start_y + ((hour - timetable_start_hour) * hour_height)
    
    def text_width(text, font):
        return draw.textbbox((0, 0), text, font=font)[2]

    def wrap_text_to_width(text, font, max_width):
        text = str(text)

        lines = []
        current = ""

        for ch in text:
            if text_width(current + ch, font) <= max_width:
                current += ch
            else:
                lines.append(current)
                current = ch

        if current:
            lines.append(current)

        # 너무 짧은 마지막 줄 보정
        if len(lines) >= 2 and len(lines[-1]) <= 2:
            lines[-2] += lines[-1]
            lines.pop()

        return lines

    def draw_text_in_box(text, x, y, max_width, max_height, font, fill, line_gap=3):
        lines = wrap_text_to_width(text, font, max_width)
        line_height = font_course.size + 6

        max_lines = max(1, max_height // line_height)
        visible_lines = lines[:max_lines]

        if len(lines) > max_lines:
            last = visible_lines[-1]
            while last and text_width(last + "...", font) > max_width:
                last = last[:-1]
            visible_lines[-1] = last + "..."

        for idx, line in enumerate(visible_lines):
            draw.text((x, y + idx * line_height), line, fill=fill, font=font)

    # ---------------------------------------------------------------------------
    # 6. JSON 과목 데이터를 순회하며 시간표 블록 채우기
    # ---------------------------------------------------------------------------
    for course in courses:
        course_name = course.get("course_name")
        classroom = course.get("classroom", "")
        
        # 색상 정보 가져오기
        color_info = course.get("color", {})
        bg_color = color_info.get("background", "#E3F2FD")
        text_color = color_info.get("text", "#1F2937")

        for sch in course.get("schedule", []):
            day = sch.get("day")
            time_range = sch.get("time")

            if day not in day_map or not time_range or "-" not in time_range:
                continue

            start_time, end_time = time_range.split("-")
            x = start_x + day_map[day] * col_width
            y1 = time_to_y(start_time)
            y2 = time_to_y(end_time)

            # 본 블록
            draw.rounded_rectangle(
                [(x + 4, y1 + 4), (x + col_width - 4, y2 - 4)],
                radius=10,
                fill=bg_color,
                outline="#cbd5e1",
                width=1
            )

            padding = 16

            inner_x = x + padding
            inner_y = y1 + padding

            inner_width = col_width - (padding * 2)
            inner_height = y2 - y1 - (padding * 2)

            course_lines = wrap_text_to_width(
                course_name,
                font_course,
                inner_width
            )

            line_height = draw.textbbox(
                (0, 0),
                "가",
                font=font_course
            )[3] + 2

            current_y = inner_y

            # 과목명
            for line in course_lines[:3]:
                draw.text(
                    (inner_x, current_y),
                    line,
                    fill=text_color,
                    font=font_course
                )
                current_y += line_height

            # 과목명 아래 여백
            current_y += 4

            # 강의실
            if classroom:
                draw.text(
                    (inner_x, current_y),
                    classroom,
                    fill="#6b7280",
                    font=font_room
                )
    output_dir = os.path.join(os.path.dirname(__file__), "templates", "timetable_image")
    os.makedirs(output_dir, exist_ok=True)

    safe_student_id = str(student_id).replace("/", "_").replace("\\", "_")
    filename = f"timetable_{safe_student_id}_{int(time.time())}.png"
    output_path = os.path.join(output_dir, filename)

    image.save(output_path)
    return filename