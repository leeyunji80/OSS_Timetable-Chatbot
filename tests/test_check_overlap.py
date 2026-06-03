import unittest
import scheduler.check_overlap
from scheduler.check_overlap import is_conflict, is_valid_combination
class TestCheckOverlap(unittest.TestCase):

    # -----------------------------
    # is_conflict 테스트
    # -----------------------------

    def test_conflict_same_day_overlap(self):
        course1 = {
            "time_slots": [
                {"day": "Mon", "start_period": 1, "end_period": 3}
            ]
        }

        course2 = {
            "time_slots": [
                {"day": "Mon", "start_period": 2, "end_period": 4}
            ]
        }

        self.assertTrue(is_conflict(course1, course2))

    def test_no_conflict_different_day(self):
        course1 = {
            "time_slots": [
                {"day": "Mon", "start_period": 1, "end_period": 3}
            ]
        }

        course2 = {
            "time_slots": [
                {"day": "Tue", "start_period": 1, "end_period": 3}
            ]
        }

        self.assertFalse(is_conflict(course1, course2))

    def test_no_conflict_same_day(self):
        course1 = {
            "time_slots": [
                {"day": "Mon", "start_period": 1, "end_period": 2}
            ]
        }

        course2 = {
            "time_slots": [
                {"day": "Mon", "start_period": 3, "end_period": 4}
            ]
        }

        self.assertFalse(is_conflict(course1, course2))

    def test_conflict_boundary_time(self):
        course1 = {
            "time_slots": [
                {"day": "Wed", "start_period": 2, "end_period": 4}
            ]
        }

        course2 = {
            "time_slots": [
                {"day": "Wed", "start_period": 4, "end_period": 6}
            ]
        }

        self.assertTrue(is_conflict(course1, course2))

    def test_multiple_time_slots(self):
        course1 = {
            "time_slots": [
                {"day": "Mon", "start_period": 1, "end_period": 2},
                {"day": "Wed", "start_period": 3, "end_period": 4}
            ]
        }

        course2 = {
            "time_slots": [
                {"day": "Fri", "start_period": 1, "end_period": 2},
                {"day": "Wed", "start_period": 4, "end_period": 5}
            ]
        }

        self.assertTrue(is_conflict(course1, course2))

    # -----------------------------
    # is_valid_combination 테스트
    # -----------------------------

    def test_valid_combination(self):
        schedule = [
            {
                "name": "Math",
                "time_slots": [
                    {"day": "Mon", "start_period": 1, "end_period": 2}
                ]
            },
            {
                "name": "English",
                "time_slots": [
                    {"day": "Tue", "start_period": 1, "end_period": 2}
                ]
            }
        ]

        self.assertTrue(is_valid_combination(schedule))

    def test_invalid_combination_same_name(self):
        schedule = [
            {
                "name": "Math",
                "time_slots": [
                    {"day": "Mon", "start_period": 1, "end_period": 2}
                ]
            },
            {
                "name": "Math",
                "time_slots": [
                    {"day": "Tue", "start_period": 3, "end_period": 4}
                ]
            }
        ]

        self.assertFalse(is_valid_combination(schedule))

    def test_invalid_combination_time_conflict(self):
        schedule = [
            {
                "name": "Math",
                "time_slots": [
                    {"day": "Mon", "start_period": 1, "end_period": 3}
                ]
            },
            {
                "name": "Science",
                "time_slots": [
                    {"day": "Mon", "start_period": 2, "end_period": 4}
                ]
            }
        ]

        self.assertFalse(is_valid_combination(schedule))

    def test_empty_schedule(self):
        schedule = []

        self.assertTrue(is_valid_combination(schedule))

    def test_single_course_schedule(self):
        schedule = [
            {
                "name": "Math",
                "time_slots": [
                    {"day": "Fri", "start_period": 1, "end_period": 2}
                ]
            }
        ]

        self.assertTrue(is_valid_combination(schedule))


if __name__ == "__main__":
    unittest.main()