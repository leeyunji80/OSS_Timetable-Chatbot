import unittest
from scheduler.timetable_colors import (
    COLOR_PALETTE,
    assign_course_colors
)


class TestTimetableColors(unittest.TestCase):

    # -----------------------------
    # 기본 색상 지정 테스트
    # -----------------------------

    def test_assign_course_colors_basic(self):
        schedule = [
            {"name": "Math"},
            {"name": "English"},
            {"name": "Science"}
        ]

        result = assign_course_colors(schedule)

        self.assertEqual(result["Math"], COLOR_PALETTE[0])
        self.assertEqual(result["English"], COLOR_PALETTE[1])
        self.assertEqual(result["Science"], COLOR_PALETTE[2])

    # -----------------------------
    # 빈 시간표 테스트
    # -----------------------------

    def test_assign_course_colors_empty_schedule(self):
        schedule = []

        result = assign_course_colors(schedule)

        self.assertEqual(result, {})

    # -----------------------------
    # 색상 순환 테스트
    # -----------------------------

    def test_assign_course_colors_palette_cycle(self):
        schedule = []

        for i in range(len(COLOR_PALETTE) + 2):
            schedule.append({"name": f"Course{i}"})

        result = assign_course_colors(schedule)

        self.assertEqual(
            result["Course0"],
            COLOR_PALETTE[0]
        )

        self.assertEqual(
            result[f"Course{len(COLOR_PALETTE)}"],
            COLOR_PALETTE[0]
        )

        self.assertEqual(
            result[f"Course{len(COLOR_PALETTE) + 1}"],
            COLOR_PALETTE[1]
        )

    # -----------------------------
    # 과목 이름 중복 테스트
    # -----------------------------

    def test_assign_course_colors_duplicate_names(self):
        schedule = [
            {"name": "Math"},
            {"name": "Math"}
        ]

        result = assign_course_colors(schedule)

        # 동일한 key 이므로 마지막 색상으로 덮어씀
        self.assertEqual(result["Math"], COLOR_PALETTE[1])

    # -----------------------------
    # 반환 타입 테스트
    # -----------------------------

    def test_assign_course_colors_return_type(self):
        schedule = [
            {"name": "Math"}
        ]

        result = assign_course_colors(schedule)

        self.assertIsInstance(result, dict)

    # -----------------------------
    # 색상 구조 테스트
    # -----------------------------

    def test_color_palette_structure(self):

        for color in COLOR_PALETTE:
            self.assertIn("background", color)
            self.assertIn("text", color)

            self.assertTrue(color["background"].startswith("#"))
            self.assertTrue(color["text"].startswith("#"))


if __name__ == "__main__":
    unittest.main()