import unittest
from unittest.mock import patch, MagicMock
import os

from ui.make_timetable_image import draw_timetable_image


class TestMakeTimetableImage(unittest.TestCase):

    # -------------------------------------------------
    # 기본 이미지 생성 테스트
    # -------------------------------------------------
    @patch("ui.make_timetable_image.Image.Image.save")
    def test_draw_timetable_image_basic(
        self,
        mock_save
    ):

        alternative_data = {
            "timetable_title": "추천 시간표",
            "courses": [
                {
                    "course_name": "자료구조",
                    "classroom": "E8-101",
                    "color": {
                        "background": "#FFFFFF",
                        "text": "#000000"
                    },
                    "schedule": [
                        {
                            "day": "월",
                            "time": "09:00-11:00"
                        }
                    ]
                }
            ]
        }

        result = draw_timetable_image(
            alternative_data,
            student_id="20210001"
        )

        self.assertTrue(result.endswith(".png"))
        mock_save.assert_called_once()

    # -------------------------------------------------
    # 빈 과목 데이터 테스트
    # -------------------------------------------------

    @patch("ui.make_timetable_image.Image.Image.save")
    def test_draw_timetable_image_empty_courses(
        self,
        mock_save
    ):

        alternative_data = {
            "courses": []
        }

        result = draw_timetable_image(alternative_data)

        self.assertTrue(result.endswith(".png"))
        mock_save.assert_called_once()

    # -------------------------------------------------
    # 잘못된 시간 형식 테스트
    # -------------------------------------------------
    @patch("ui.make_timetable_image.Image.Image.save")
    def test_draw_timetable_image_invalid_time(
        self,
        mock_save
    ):
        alternative_data = {
            "courses": [
                {
                    "course_name": "운영체제",
                    "schedule": [
                        {
                            "day": "월",
                            "time": "invalid"
                        }
                    ]
                }
            ]
        }

        result = draw_timetable_image(alternative_data)

        self.assertTrue(result.endswith(".png"))

    # -------------------------------------------------
    # 긴 과목명 테스트
    # -------------------------------------------------

    @patch("ui.make_timetable_image.Image.Image.save")
    def test_draw_timetable_image_long_course_name(
        self,
        mock_save
    ):
        alternative_data = {
            "courses": [
                {
                    "course_name": "아주매우긴과목이름테스트데이터입니다",
                    "classroom": "N1-404",
                    "schedule": [
                        {
                            "day": "화",
                            "time": "10:00-13:00"
                        }
                    ]
                }
            ]
        }

        result = draw_timetable_image(alternative_data)

        self.assertTrue(result.endswith(".png"))

    # -------------------------------------------------
    # 여러 과목 테스트
    # -------------------------------------------------

    @patch("ui.make_timetable_image.Image.Image.save")
    def test_draw_timetable_image_multiple_courses(
        self,
        mock_save
    ):

        alternative_data = {
            "courses": [
                {
                    "course_name": "자료구조",
                    "schedule": [
                        {
                            "day": "월",
                            "time": "09:00-11:00"
                        }
                    ]
                },
                {
                    "course_name": "운영체제",
                    "schedule": [
                        {
                            "day": "수",
                            "time": "13:00-15:00"
                        }
                    ]
                }
            ]
        }

        result = draw_timetable_image(alternative_data)

        self.assertTrue(result.endswith(".png"))

    # -------------------------------------------------
    # 늦은 시간 수업 테스트
    # -------------------------------------------------
    @patch("ui.make_timetable_image.Image.Image.save")
    def test_draw_timetable_image_late_class(
        self,
        mock_save
    ):

        alternative_data = {
            "courses": [
                {
                    "course_name": "야간수업",
                    "schedule": [
                        {
                            "day": "금",
                            "time": "18:00-21:00"
                        }
                    ]
                }
            ]
        }

        result = draw_timetable_image(alternative_data)

        self.assertTrue(result.endswith(".png"))

    # -------------------------------------------------
    # 잘못된 요일 테스트
    # -------------------------------------------------

    @patch("ui.make_timetable_image.Image.Image.save")
    def test_draw_timetable_image_invalid_day(
        self,
        mock_save
    ):
        alternative_data = {
            "courses": [
                {
                    "course_name": "테스트",
                    "schedule": [
                        {
                            "day": "토",
                            "time": "09:00-10:00"
                        }
                    ]
                }
            ]
        }

        result = draw_timetable_image(alternative_data)

        self.assertTrue(result.endswith(".png"))

    # -------------------------------------------------
    # student_id 안전 처리 테스트
    # -------------------------------------------------

    @patch("ui.make_timetable_image.Image.Image.save")
    def test_draw_timetable_image_safe_student_id(
        self,
        mock_save
    ):

        alternative_data = {
            "courses": []
        }

        result = draw_timetable_image(
            alternative_data,
            student_id="../test"
        )

        self.assertNotIn("/", result)
        self.assertTrue(result.endswith(".png"))

    # -------------------------------------------------
    # timetable_title 기본값 테스트
    # -------------------------------------------------
    @patch("ui.make_timetable_image.Image.Image.save")
    def test_draw_timetable_image_default_title(
        self,
        mock_save
    ):

        alternative_data = {
            "courses": []
        }

        result = draw_timetable_image(alternative_data)

        self.assertTrue(result.endswith(".png"))


    @patch("ui.make_timetable_image.Image.Image.save")
    def test_draw_timetable_image_text_overflow(
        self,
        mock_save
        ):
        alternative_data = {
            "courses": [
                {
                    "course_name": (
                        "엄청엄청엄청엄청엄청긴과목이름"
                        "엄청엄청엄청엄청긴과목이름"
                    ),
                    "classroom": "E8-101",
                    "schedule": [
                        {
                            "day": "월",
                            "time": "09:00-10:00"
                        }
                    ]
                }
            ]
        }

        result = draw_timetable_image(alternative_data)

        self.assertTrue(result.endswith(".png"))

if __name__ == "__main__":
    unittest.main()