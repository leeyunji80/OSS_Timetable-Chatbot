import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

from scheduler.timetable_generator import (
    matches_specific_period,
    evaluate_load,
    evaluate_team_project,
    normalize_specific_time,
    make_timetable_title,
    build_timetable_json,
    generate_timetable_response,
    generate_timetable_combinations,
    exceeds_needed_general_credits
)


class TestTimetableGenerator(unittest.TestCase):

    # -------------------------------------------------
    # matches_specific_period 테스트
    # -------------------------------------------------
    def test_generate_timetable_with_conflict(self):

     df = pd.DataFrame([
         {
             "교과목명": "자료구조",
             "교수명": "홍길동",
             "학점": 3,
             "이수구분": "전공선택",
             "수업시간": "월 1~2",
             "강의실": "E8-101",
             "요일": "월",
             "교시": "1~2",
             "평가_과제(%)": 10,
             "방법_토의토론(%)": 0,
             "교양대분류": "",
             "교양소분류": ""
         },
         {
             "교과목명": "운영체제",
             "교수명": "김교수",
             "학점": 3,
             "이수구분": "전공선택",
             "수업시간": "월 1~2",
             "강의실": "E8-102",
             "요일": "월",
             "교시": "1~2",
             "평가_과제(%)": 20,
             "방법_토의토론(%)": 10,
             "교양대분류": "",
             "교양소분류": ""
         },
         {
             "교과목명": "알고리즘",
             "교수명": "이교수",
             "학점": 3,
             "이수구분": "전공선택",
             "수업시간": "화 3~4",
             "강의실": "E8-103",
             "요일": "화",
             "교시": "3~4",
             "평가_과제(%)": 30,
             "방법_토의토론(%)": 20,
             "교양대분류": "",
             "교양소분류": ""
         }
     ])

     result = generate_timetable_combinations(
         recommended_major_courses=[
             "자료구조",
             "운영체제",
             "알고리즘"
         ],
         needed_general_areas={},
         missing_required_major_courses=[],
         filtered_df=df,
         target_credits=6,
         empty_days=[],
         avoid_time_slots=[],
         preferred_time_slots=[],
         user_preferences={},
         mode="balanced"
     )

     self.assertIsInstance(result, list)
     self.assertTrue(len(result) >= 1)
    
    def test_generate_timetable_with_empty_day(self):

     df = pd.DataFrame([
         {
             "교과목명": "자료구조",
             "교수명": "홍길동",
             "학점": 3,
             "이수구분": "전공선택",
             "수업시간": "월 1~2",
             "강의실": "E8-101",
             "요일": "월",
             "교시": "1~2",
             "평가_과제(%)": 10,
             "방법_토의토론(%)": 0,
             "교양대분류": "",
             "교양소분류": ""
         },
         {
             "교과목명": "데이터통신",
             "교수명": "박교수",
             "학점": 3,
             "이수구분": "전공선택",
             "수업시간": "수 5~6",
             "강의실": "E8-104",
             "요일": "수",
             "교시": "5~6",
             "평가_과제(%)": 5,
             "방법_토의토론(%)": 0,
             "교양대분류": "",
             "교양소분류": ""
         }
     ])

     result = generate_timetable_combinations(
         recommended_major_courses=[
             "자료구조",
             "데이터통신"
         ],
         needed_general_areas={},
         missing_required_major_courses=[],
         filtered_df=df,
         target_credits=6,
         empty_days=["화"],
         avoid_time_slots=[],
         preferred_time_slots=[],
         user_preferences={},
         mode="balanced"
     )

     self.assertIsInstance(result, list)

    def test_generate_timetable_with_avoid_slots(self):

     df = pd.DataFrame([
         {
             "교과목명": "자료구조",
             "교수명": "홍길동",
             "학점": 3,
             "이수구분": "전공선택",
             "수업시간": "월 1~2",
             "강의실": "E8-101",
             "요일": "월",
             "교시": "1~2",
             "평가_과제(%)": 10,
             "방법_토의토론(%)": 0,
             "교양대분류": "",
             "교양소분류": ""
         },
         {
             "교과목명": "알고리즘",
             "교수명": "이교수",
             "학점": 3,
             "이수구분": "전공선택",
             "수업시간": "화 3~4",
             "강의실": "E8-103",
             "요일": "화",
             "교시": "3~4",
             "평가_과제(%)": 30,
             "방법_토의토론(%)": 20,
             "교양대분류": "",
             "교양소분류": ""
         }
     ])

     avoid_slots = [
         {
             "day": "월요일",
             "specific_time_slot": [1],
             "condition": "피함"
         }
     ]

     result = generate_timetable_combinations(
         recommended_major_courses=[
             "자료구조",
             "알고리즘"
         ],
         needed_general_areas={},
         missing_required_major_courses=[],
         filtered_df=df,
         target_credits=6,
         empty_days=[],
         avoid_time_slots=avoid_slots,
         preferred_time_slots=[],
         user_preferences={},
         mode="balanced"
     )

     self.assertIsInstance(result, list)
    

    def test_assignment_preference_many(self):

        df = pd.DataFrame([
            {
                "교과목명": "알고리즘",
                "교수명": "이교수",
                "학점": 3,
                "이수구분": "전공선택",
                "수업시간": "월 1~2",
                "강의실": "E8-101",
                "요일": "월",
                "교시": "1~2",
                "평가_과제(%)": 40,
                "방법_토의토론(%)": 0,
                "교양대분류": "",
                "교양소분류": ""
            }
        ])

        result = generate_timetable_combinations(
            recommended_major_courses=["알고리즘"],
            needed_general_areas={},
            missing_required_major_courses=[],
            filtered_df=df,
            target_credits=3,
            empty_days=[],
            avoid_time_slots=[],
            preferred_time_slots=[],
            user_preferences={
                "assignment_preference": "과제많음"
            },
            mode="user_priority"
        )

        self.assertTrue(len(result) >= 1)


    def test_team_project_preference(self):

        df = pd.DataFrame([
            {
                "교과목명": "운영체제",
                "교수명": "김교수",
                "학점": 3,
                "이수구분": "전공선택",
                "수업시간": "화 3~4",
                "강의실": "E8-102",
                "요일": "화",
                "교시": "3~4",
                "평가_과제(%)": 10,
                "방법_토의토론(%)": 30,
                "교양대분류": "",
                "교양소분류": ""
            }
        ])

        result = generate_timetable_combinations(
            recommended_major_courses=["운영체제"],
            needed_general_areas={},
            missing_required_major_courses=[],
            filtered_df=df,
            target_credits=3,
            empty_days=[],
            avoid_time_slots=[],
            preferred_time_slots=[],
            user_preferences={
                "team_preference": "팀플없음"
            },
            mode="user_priority"
        )

        self.assertEqual(result, [])

    def test_selected_course_priority(self):

        df = pd.DataFrame([
            {
                "교과목명": "자료구조",
                "교수명": "홍길동",
                "학점": 3,
                "이수구분": "전공선택",
                "수업시간": "수 1~2",
                "강의실": "E8-103",
                "요일": "수",
                "교시": "1~2",
                "평가_과제(%)": 10,
                "방법_토의토론(%)": 0,
                "교양대분류": "",
                "교양소분류": ""
            }
        ])

        result = generate_timetable_combinations(
            recommended_major_courses=["자료구조"],
            needed_general_areas={},
            missing_required_major_courses=[],
            filtered_df=df,
            target_credits=3,
            empty_days=[],
            avoid_time_slots=[],
            preferred_time_slots=[],
            user_preferences={
                "selected_courses": ["자료구조"]
            },
            mode="user_priority"
        )

        self.assertTrue(len(result) >= 1)

    def test_matches_specific_period_true(self):

        course_slot = {
            "day": "월",
            "start_period": 2,
            "end_period": 4
        }

        condition_slot = {
            "day": "월",
            "specific_time_slot": [3]
        }

        result = matches_specific_period(
            course_slot,
            condition_slot
        )

        self.assertTrue(result)

    def test_matches_specific_period_false(self):

        course_slot = {
            "day": "화",
            "start_period": 1,
            "end_period": 2
        }

        condition_slot = {
            "day": "월",
            "specific_time_slot": [1]
        }

        result = matches_specific_period(
            course_slot,
            condition_slot
        )

        self.assertFalse(result)

    # -------------------------------------------------
    # evaluate_load 테스트
    # -------------------------------------------------

    def test_evaluate_load_many(self):

        row = {
            "평가_과제(%)": 40
        }

        result = evaluate_load(row)

        self.assertEqual(result, "많다")

    def test_evaluate_load_few(self):

        row = {
            "평가_과제(%)": 10
        }

        result = evaluate_load(row)

        self.assertEqual(result, "적다")

    # -------------------------------------------------
    # evaluate_team_project 테스트
    # -------------------------------------------------

    def test_evaluate_team_project_exists(self):

        row = {
            "방법_토의토론(%)": 30
        }

        result = evaluate_team_project(row)

        self.assertEqual(result, "있음")

    def test_evaluate_team_project_none(self):

        row = {
            "방법_토의토론(%)": 0
        }

        result = evaluate_team_project(row)

        self.assertEqual(result, "없음")

    # -------------------------------------------------
    # normalize_specific_time 테스트
    # -------------------------------------------------

    def test_normalize_specific_time_string(self):

        slot = {
            "specific_time_slot": "1,2,3교시"
        }

        result = normalize_specific_time(slot)

        self.assertEqual(result, [1, 2, 3])

    def test_normalize_specific_time_list(self):

        slot = {
            "specific_time_slot": [1, 2]
        }

        result = normalize_specific_time(slot)

        self.assertEqual(result, [1, 2])

    def test_normalize_specific_time_none(self):

        slot = {}

        result = normalize_specific_time(slot)

        self.assertIsNone(result)

    def test_normalize_specific_time_no_digits(self):

        slot = {
            "specific_time_slot": "abc"
        }

        result = normalize_specific_time(slot)

        self.assertIsNone(result)

    def test_exceeds_needed_general_credits_subarea_overflow(self):

        ge_courses = [
            {
                "is_needed_ge": True,
                "area": "A",
                "subarea": "B",
                "credit": 4
            }
        ]

        needed_general_areas = {
            "A": {
                "B": 3
            }
        }

        result = exceeds_needed_general_credits(
            ge_courses,
            needed_general_areas
        )

        self.assertTrue(result)

    def test_exceeds_needed_general_credits_false_cases(self):

        ge_courses = [
            {
                "is_needed_ge": False,
                "area": "A",
                "subarea": "B",
                "credit": 10
            },
            {
                "is_needed_ge": True,
                "area": "",
                "subarea": "B",
                "credit": 10
            },
            {
                "is_needed_ge": True,
                "area": "A",
                "subarea": "B",
                "credit": 2
            }
        ]

        needed_general_areas = {
            "A": {
                "B": 3
            }
        }

        result = exceeds_needed_general_credits(
            ge_courses,
            needed_general_areas
        )

        self.assertFalse(result)

    def test_generate_timetable_user_priority_balanced_rule_with_selected_ge(self):

        df = pd.DataFrame([
            {
                "교과목명": "MajorA",
                "교수명": "ProfA",
                "학점": 3,
                "이수구분": "전공선택",
                "수업시간": "월 1~2",
                "강의실": "R1(101)",
                "요일": "월",
                "교시": "1~2",
                "평가_과제(%)": 10,
                "방법_토의토론(%)": 0,
                "교양대분류": "",
                "교양소분류": "",
                "수강 대상": ""
            },
            {
                "교과목명": "OldRequired",
                "교수명": "ProfB",
                "학점": 3,
                "이수구분": "전공필수",
                "수업시간": "화 3~4",
                "강의실": "R2",
                "요일": "화",
                "교시": "3~4",
                "평가_과제(%)": 15,
                "방법_토의토론(%)": 0,
                "교양대분류": "",
                "교양소분류": "",
                "수강 대상": ""
            },
            {
                "교과목명": "SelectedGE",
                "교수명": "ProfC",
                "학점": 3,
                "이수구분": "교양",
                "수업시간": "목 7~8",
                "강의실": "R3",
                "요일": "목",
                "교시": "7~8",
                "평가_과제(%)": 5,
                "방법_토의토론(%)": 0,
                "교양대분류": "FreeArea",
                "교양소분류": "FreeSub",
                "수강 대상": ""
            }
        ])

        result = generate_timetable_combinations(
            recommended_major_courses=["MajorA"],
            needed_general_areas={},
            missing_required_major_courses=["OldRequired"],
            filtered_df=df,
            target_credits=9,
            empty_days=["화"],
            avoid_time_slots=[
                {
                    "day": "화",
                    "time_range": "오전",
                    "specific_time_slot": None
                }
            ],
            preferred_time_slots=[
                {
                    "day": "월",
                    "specific_time_slot": [1]
                },
                {
                    "day": "화",
                    "specific_time_slot": [1]
                },
                {
                    "day": "월",
                    "time_range": "오전"
                },
                {
                    "day": "목",
                    "time_range": "오후"
                }
            ],
            user_preferences={
                "selected_courses": ["MajorA", "SelectedGE"],
                "conflict_resolution_rule": "균형추천"
            },
            mode="user_priority"
        )

        self.assertTrue(result)
        names = {course["name"] for course in result[0]}
        self.assertIn("MajorA", names)
        self.assertIn("SelectedGE", names)

    def test_generate_timetable_graduation_priority_with_total_needed_ge(self):

        df = pd.DataFrame([
            {
                "교과목명": "MajorA",
                "교수명": "ProfA",
                "학점": 3,
                "이수구분": "전공선택",
                "수업시간": "월 1~2",
                "강의실": "R1",
                "요일": "월",
                "교시": "1~2",
                "평가_과제(%)": 10,
                "방법_토의토론(%)": 0,
                "교양대분류": "",
                "교양소분류": "",
                "수강 대상": ""
            },
            {
                "교과목명": "NeededGE",
                "교수명": "ProfB",
                "학점": 3,
                "이수구분": "교양",
                "수업시간": "수 5~6",
                "강의실": "R2",
                "요일": "수",
                "교시": "5~6",
                "평가_과제(%)": 10,
                "방법_토의토론(%)": 0,
                "교양대분류": "AreaA",
                "교양소분류": "SubA",
                "수강 대상": ""
            }
        ])

        result = generate_timetable_combinations(
            recommended_major_courses=["MajorA"],
            needed_general_areas={
                "AreaA": {
                    "총필요학점": 3,
                    "선택가능영역": ["SubA"]
                }
            },
            missing_required_major_courses=[],
            filtered_df=df,
            target_credits=6,
            empty_days=[],
            avoid_time_slots=[],
            preferred_time_slots=[],
            user_preferences={},
            mode="graduation_priority"
        )

        self.assertTrue(result)
        self.assertTrue(
            any(course["name"] == "NeededGE" for course in result[0])
        )

    def test_generate_timetable_skips_filtered_and_excluded_courses(self):

        df = pd.DataFrame([
            {
                "교과목명": "NightCourse",
                "교수명": "ProfA",
                "학점": 3,
                "이수구분": "전공선택",
                "수업시간": "월 1~2",
                "강의실": "R1",
                "요일": "월",
                "교시": "1~2",
                "평가_과제(%)": 10,
                "방법_토의토론(%)": 0,
                "교양대분류": "",
                "교양소분류": "",
                "수강 대상": "야간학생강좌"
            },
            {
                "교과목명": "ExcludedMajor",
                "교수명": "ProfB",
                "학점": 3,
                "이수구분": "전공선택",
                "수업시간": "화 1~2",
                "강의실": "R2",
                "요일": "화",
                "교시": "1~2",
                "평가_과제(%)": 10,
                "방법_토의토론(%)": 0,
                "교양대분류": "",
                "교양소분류": "",
                "수강 대상": ""
            },
            {
                "교과목명": "KeptMajor",
                "교수명": "ProfC",
                "학점": 3,
                "이수구분": "전공선택",
                "수업시간": "수 1~2",
                "강의실": "R3",
                "요일": "수",
                "교시": "1~2",
                "평가_과제(%)": 10,
                "방법_토의토론(%)": 0,
                "교양대분류": "",
                "교양소분류": "",
                "수강 대상": ""
            }
        ])

        result = generate_timetable_combinations(
            recommended_major_courses=[
                "NightCourse",
                "ExcludedMajor",
                "KeptMajor"
            ],
            needed_general_areas={},
            missing_required_major_courses=[],
            filtered_df=df,
            target_credits=3,
            empty_days=[],
            avoid_time_slots=[],
            preferred_time_slots=[],
            user_preferences={
                "excluded_courses": ["ExcludedMajor"]
            },
            mode="user_priority"
        )

        self.assertTrue(result)
        names = {course["name"] for course in result[0]}
        self.assertEqual(names, {"KeptMajor"})

    # -------------------------------------------------
    # make_timetable_title 테스트
    # -------------------------------------------------

    def test_make_timetable_title(self):

        selected_schedule = [
            {
                "name": "자료구조",
                "is_current_grade_major": True,
                "time_slots": [
                    {
                        "day": "월",
                        "start_period": 1,
                        "end_period": 2
                    }
                ]
            }
        ]

        result = make_timetable_title(
            selected_schedule=selected_schedule,
            selected_course_set={"자료구조"},
            exclude_days=["화"],
            avoid_time_slots=[]
        )

        self.assertIn("시간표", result)

    # -------------------------------------------------
    # build_timetable_json 테스트
    # -------------------------------------------------

    @patch("scheduler.timetable_generator.assign_course_colors")
    def test_build_timetable_json(
        self,
        mock_assign
    ):

        mock_assign.return_value = {
            "자료구조": {
                "background": "#FFFFFF",
                "text": "#000000"
            }
        }

        timetable_results = [
            [
                {
                    "name": "자료구조",
                    "room": "E8",
                    "is_required": True,
                    "is_current_grade_major": True,
                    "time_slots": [
                        {
                            "day": "월",
                            "time_range": "09:00-11:00",
                            "start_period": 1,
                            "end_period": 2
                        }
                    ]
                }
            ]
        ]

        parsed_data = {
            "selected_courses": ["자료구조"]
        }

        result = build_timetable_json(
            timetable_results=timetable_results,
            parsed_data=parsed_data,
            exclude_days=[],
            avoid_time_slots=[]
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(
            len(result["alternatives"]),
            1
        )

    def test_build_timetable_json_empty(self):

        result = build_timetable_json(
            timetable_results=[],
            parsed_data={},
            exclude_days=[],
            avoid_time_slots=[]
        )

        self.assertEqual(result["status"], "error")

    # -------------------------------------------------
    # generate_timetable_response 테스트
    # -------------------------------------------------

    @patch("scheduler.timetable_generator.build_timetable_json")
    @patch("scheduler.timetable_generator.get_final_recommendations")
    @patch("scheduler.timetable_generator.pd.read_csv")
    @patch("scheduler.timetable_generator.pd.concat")
    def test_generate_timetable_response_success(
        self,
        mock_concat,
        mock_read_csv,
        mock_recommend,
        mock_build
    ):

        mock_recommend.return_value = {
            "recommended_major_courses": [],
            "needed_general_areas": {},
            "missing_required_major_courses": []
        }

        mock_concat.return_value = pd.DataFrame([
            {
                "교과목명": "자료구조",
                "교수명": "홍길동",
                "학점": 3,
                "이수구분": "전공선택",
                "수업시간": "월 1~2",
                "강의실": "E8-101",
                "요일": "월",
                "교시": "1~2",
                "평가_과제(%)": 10,
                "방법_토의토론(%)": 0,
                "교양대분류": "",
                "교양소분류": ""
            }
        ])

        mock_build.return_value = {
            "status": "success"
        }

        parsed_data = {
            "slots": [],
            "target_credit": 3,
            "selected_courses": ["자료구조"]
        }

        result = generate_timetable_response(
            parsed_data=parsed_data,
            login_student_id="20210001"
        )

        self.assertEqual(result["status"], "success")

    @patch("scheduler.timetable_generator.get_final_recommendations")
    def test_generate_timetable_response_error(
        self,
        mock_recommend
    ):

        mock_recommend.return_value = {
            "error": "학생 정보 없음"
        }

        parsed_data = {
            "slots": []
        }

        result = generate_timetable_response(
            parsed_data=parsed_data,
            login_student_id="99999999"
        )

        self.assertEqual(result["status"], "error")

    @patch("scheduler.timetable_generator.build_timetable_json")
    @patch("scheduler.timetable_generator.get_final_recommendations")
    @patch("scheduler.timetable_generator.pd.concat")
    def test_generate_timetable_response_no_result(
        self,
        mock_concat,
        mock_recommend,
        mock_build
    ):

        mock_recommend.return_value = {
            "recommended_major_courses": [],
            "needed_general_areas": {},
            "missing_required_major_courses": []
        }

        mock_concat.return_value = pd.DataFrame()

        mock_build.return_value = {
            "status": "error"
        }

        parsed_data = {
            "slots": [],
            "selected_courses": ["자료구조"]
        }

        result = generate_timetable_response(
            parsed_data=parsed_data,
            login_student_id="20210001"
        )

        self.assertEqual(result["status"], "error")

    def test_generate_timetable_with_general_courses(self):

        df = pd.DataFrame([
            {
                "교과목명": "자료구조",
                "교수명": "홍길동",
                "학점": 3,
                "이수구분": "전공선택",
                "수업시간": "월 1~2",
                "강의실": "E8-101",
                "요일": "월",
                "교시": "1~2",
                "평가_과제(%)": 10,
                "방법_토의토론(%)": 0,
                "교양대분류": "",
                "교양소분류": ""
            },
            {
                "교과목명": "철학의이해",
                "교수명": "김교수",
                "학점": 3,
                "이수구분": "교양",
                "수업시간": "화 3~4",
                "강의실": "N1-201",
                "요일": "화",
                "교시": "3~4",
                "평가_과제(%)": 20,
                "방법_토의토론(%)": 0,
                "교양대분류": "인문사회",
                "교양소분류": "사회와역사"
            },
            {
                "교과목명": "공업법규와창업",
                "교수명": "박교수",
                "학점": 3,
                "이수구분": "교양",
                "수업시간": "수 5~6",
                "강의실": "N1-202",
                "요일": "수",
                "교시": "5~6",
                "평가_과제(%)": 15,
                "방법_토의토론(%)": 10,
                "교양대분류": "인문사회",
                "교양소분류": "사회와역사"
            }
        ])

        result = generate_timetable_combinations(
            recommended_major_courses=["자료구조"],
            needed_general_areas={
                "인문사회": {
                    "사회와역사": 3
                }
            },
            missing_required_major_courses=[],
            filtered_df=df,
            target_credits=6,
            empty_days=[],
            avoid_time_slots=[],
            preferred_time_slots=[],
            user_preferences={},
            mode="graduation_priority"
        )

        self.assertTrue(len(result) >= 1)

    def test_selected_course_mismatch(self):

        df = pd.DataFrame([
            {
                "교과목명": "알고리즘",
                "교수명": "이교수",
                "학점": 3,
                "이수구분": "전공선택",
                "수업시간": "월 1~2",
                "강의실": "E8-101",
                "요일": "월",
                "교시": "1~2",
                "평가_과제(%)": 20,
                "방법_토의토론(%)": 0,
                "교양대분류": "",
                "교양소분류": ""
            }
        ])

        result = generate_timetable_combinations(
            recommended_major_courses=["알고리즘"],
            needed_general_areas={},
            missing_required_major_courses=[],
            filtered_df=df,
            target_credits=3,
            empty_days=[],
            avoid_time_slots=[],
            preferred_time_slots=[],
            user_preferences={
                "selected_courses": ["자료구조"]
            },
            mode="user_priority"
        )

        self.assertEqual(result, [])

    def test_credit_overflow_continue(self):

        df = pd.DataFrame([
            {
                "교과목명": "자료구조",
                "교수명": "홍길동",
                "학점": 3,
                "이수구분": "전공선택",
                "수업시간": "월 1~2",
                "강의실": "E8-101",
                "요일": "월",
                "교시": "1~2",
                "평가_과제(%)": 10,
                "방법_토의토론(%)": 0,
                "교양대분류": "",
                "교양소분류": ""
            },
            {
                "교과목명": "운영체제",
                "교수명": "김교수",
                "학점": 3,
                "이수구분": "전공선택",
                "수업시간": "화 3~4",
                "강의실": "E8-102",
                "요일": "화",
                "교시": "3~4",
                "평가_과제(%)": 15,
                "방법_토의토론(%)": 0,
                "교양대분류": "",
                "교양소분류": ""
            }
        ])

        result = generate_timetable_combinations(
            recommended_major_courses=[
                "자료구조",
                "운영체제"
            ],
            needed_general_areas={},
            missing_required_major_courses=[],
            filtered_df=df,
            target_credits=1,
            empty_days=[],
            avoid_time_slots=[],
            preferred_time_slots=[],
            user_preferences={},
            mode="balanced"
        )

        self.assertEqual(result, [])

    def test_all_combinations_conflict(self):

        df = pd.DataFrame([
            {
                "교과목명": "자료구조",
                "교수명": "홍길동",
                "학점": 3,
                "이수구분": "전공선택",
                "수업시간": "월 1~3",
                "강의실": "E8-101",
                "요일": "월",
                "교시": "1~3",
                "평가_과제(%)": 10,
                "방법_토의토론(%)": 0,
                "교양대분류": "",
                "교양소분류": ""
            },
            {
                "교과목명": "알고리즘",
                "교수명": "김교수",
                "학점": 3,
                "이수구분": "전공선택",
                "수업시간": "월 2~4",
                "강의실": "E8-102",
                "요일": "월",
                "교시": "2~4",
                "평가_과제(%)": 20,
                "방법_토의토론(%)": 0,
                "교양대분류": "",
                "교양소분류": ""
            }
        ])

        result = generate_timetable_combinations(
            recommended_major_courses=[
                "자료구조",
                "알고리즘"
            ],
            needed_general_areas={},
            missing_required_major_courses=[],
            filtered_df=df,
            target_credits=6,
            empty_days=[],
            avoid_time_slots=[],
            preferred_time_slots=[],
            user_preferences={},
            mode="balanced"
        )

        self.assertEqual(result, [])
    def test_all_combinations_conflict(self):

        df = pd.DataFrame([
            {
                "교과목명": "자료구조",
                "교수명": "홍길동",
                "학점": 3,
                "이수구분": "전공선택",
                "수업시간": "월 1~3",
                "강의실": "E8-101",
                "요일": "월",
                "교시": "1~3",
                "평가_과제(%)": 10,
                "방법_토의토론(%)": 0,
                "교양대분류": "",
                "교양소분류": ""
            },
            {
                "교과목명": "알고리즘",
                "교수명": "김교수",
                "학점": 3,
                "이수구분": "전공선택",
                "수업시간": "월 2~4",
                "강의실": "E8-102",
                "요일": "월",
                "교시": "2~4",
                "평가_과제(%)": 20,
                "방법_토의토론(%)": 0,
                "교양대분류": "",
                "교양소분류": ""
            }
        ])

        result = generate_timetable_combinations(
            recommended_major_courses=[
                "자료구조",
                "알고리즘"
            ],
            needed_general_areas={},
            missing_required_major_courses=[],
            filtered_df=df,
            target_credits=6,
            empty_days=[],
            avoid_time_slots=[],
            preferred_time_slots=[],
            user_preferences={},
            mode="balanced"
        )

        self.assertEqual(result, [])

if __name__ == "__main__":
    unittest.main()
