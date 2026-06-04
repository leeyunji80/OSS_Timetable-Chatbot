import unittest
from scheduler.timetable_parser import parse_day_and_period


class TestTimetableParser(unittest.TestCase):

    # -----------------------------
    # 단일 요일 + 범위 교시 테스트
    # -----------------------------
    

    def test_single_day_range_period(self):

        result = parse_day_and_period("Mon", "1~3")

        expected = [
            {
                "day": "Mon",
                "start_period": 1,
                "end_period": 3,
                "time_range": "09:00-12:00"
            }
        ]

        self.assertEqual(result, expected)

    # -----------------------------
    # 단일 요일 + 쉼표 교시 테스트
    # -----------------------------

    def test_single_day_comma_period(self):

        result = parse_day_and_period("Tue", "1,2,3")

        expected = [
            {
                "day": "Tue",
                "start_period": 1,
                "end_period": 3,
                "time_range": "09:00-12:00"
            }
        ]

        self.assertEqual(result, expected)

    # -----------------------------
    # 다중 요일 테스트
    # -----------------------------

    def test_multiple_days(self):

        result = parse_day_and_period(
            "Mon|Wed",
            "1~2|5~6"
        )

        expected = [
            {
                "day": "Mon",
                "start_period": 1,
                "end_period": 2,
                "time_range": "09:00-11:00"
            },
            {
                "day": "Wed",
                "start_period": 5,
                "end_period": 6,
                "time_range": "13:00-15:00"
            }
        ]

        self.assertEqual(result, expected)

    # -----------------------------
    # 공백 포함 테스트
    # -----------------------------

    def test_whitespace_handling(self):

        result = parse_day_and_period(
            " Mon | Fri ",
            " 2~3 | 7~8 "
        )

        expected = [
            {
                "day": "Mon",
                "start_period": 2,
                "end_period": 3,
                "time_range": "10:00-12:00"
            },
            {
                "day": "Fri",
                "start_period": 7,
                "end_period": 8,
                "time_range": "15:00-17:00"
            }
        ]

        self.assertEqual(result, expected)

    # -----------------------------
    # 빈 값 테스트
    # -----------------------------

    def test_none_input(self):

        result = parse_day_and_period(None, "1~3")

        self.assertEqual(result, [])

    def test_none_period(self):

        result = parse_day_and_period("Mon", None)

        self.assertEqual(result, [])

    # -----------------------------
    # 잘못된 교시 테스트
    # -----------------------------

    def test_invalid_period(self):

        result = parse_day_and_period("Mon", "abc")

        self.assertEqual(result, [])

    # -----------------------------
    # 숫자 혼합 문자열 테스트
    # -----------------------------

    def test_mixed_invalid_period(self):

        result = parse_day_and_period("Tue", "1,a,3")

        expected = [
            {
                "day": "Tue",
                "start_period": 1,
                "end_period": 3,
                "time_range": "09:00-12:00"
            }
        ]

        self.assertEqual(result, expected)

    # -----------------------------
    # 큰 교시 번호 테스트
    # -----------------------------

    def test_late_period(self):

        result = parse_day_and_period("Fri", "10~12")

        expected = [
            {
                "day": "Fri",
                "start_period": 10,
                "end_period": 12,
                "time_range": "18:00-21:00"
            }
        ]

        self.assertEqual(result, expected)

    # -----------------------------
    # 따옴표 제거 테스트
    # -----------------------------

    def test_quote_removal(self):

        result = parse_day_and_period(
            'Mon|Tue',
            '"1~2|3~4"'
        )

        expected = [
            {
                "day": "Mon",
                "start_period": 1,
                "end_period": 2,
                "time_range": "09:00-11:00"
            },
            {
                "day": "Tue",
                "start_period": 3,
                "end_period": 4,
                "time_range": "11:00-13:00"
            }
        ]

        self.assertEqual(result, expected)
        


if __name__ == "__main__":
    unittest.main()