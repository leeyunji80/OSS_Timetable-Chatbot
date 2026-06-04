import unittest
from unittest.mock import patch, mock_open
import pandas as pd

from scheduler.course_recommender import (
    load_students_data,
    load_graduation_rules,
    load_curriculum_model,
    load_major_courses,
    load_completed_courses,
    get_graduation_rule,
    normalize_subarea,
    analyze_graduation_status,
    filter_completed_courses,
    get_recommended_courses,
    get_missing_previous_required_courses,
    calculate_remaining_requirements,
    get_final_recommendations
)


class TestCourseRecommender(unittest.TestCase):

    # -------------------------------------------------
    # normalize_subarea 테스트
    # -------------------------------------------------

    def test_normalize_subarea_mapping(self):

        self.assertEqual(
            normalize_subarea("확대"),
            "확대교양"
        )

        self.assertEqual(
            normalize_subarea("대학글쓰기"),
            "의사소통"
        )

    def test_normalize_subarea_default(self):

        self.assertEqual(
            normalize_subarea("기타영역"),
            "기타영역"
        )

    # -------------------------------------------------
    # analyze_graduation_status 테스트
    # -------------------------------------------------

    def test_analyze_graduation_status(self):

        completed_courses = [
            {
                "name": "자료구조",
                "credit": 3,
                "subcategory": "전공필수",
                "area": "전공",
                "subarea": "전공"
            },
            {
                "name": "영어회화",
                "credit": 2,
                "subcategory": "교양",
                "area": "영어",
                "subarea": "영어"
            }
        ]

        result = analyze_graduation_status(completed_courses)

        self.assertEqual(result["total_credits"], 5)
        self.assertEqual(result["major_required"], 3)
        self.assertEqual(result["major_elective"], 0)

        self.assertIn("자료구조", result["completed_course_names"])

    # -------------------------------------------------
    # filter_completed_courses 테스트
    # -------------------------------------------------

    def test_filter_completed_courses(self):

        recommended = [
            "자료구조",
            "운영체제",
            "컴퓨터네트워크"
        ]

        completed = {
            "자료구조"
        }

        result = filter_completed_courses(
            recommended,
            completed
        )

        self.assertEqual(
            result,
            ["운영체제", "컴퓨터네트워크"]
        )

    # -------------------------------------------------
    # get_graduation_rule 테스트
    # -------------------------------------------------

    def test_get_graduation_rule(self):

        rules_data = {
            "rule_sets": {
                "2021": {
                    "applies_to": {
                        "admission_year_from": 2021,
                        "admission_year_to": 2023
                    }
                }
            }
        }

        result = get_graduation_rule(
            rules_data,
            2022
        )

        self.assertIsNotNone(result)

    def test_get_graduation_rule_none(self):

        rules_data = {
            "rule_sets": {}
        }

        result = get_graduation_rule(
            rules_data,
            2025
        )

        self.assertIsNone(result)

    # -------------------------------------------------
    # get_recommended_courses 테스트
    # -------------------------------------------------

    def test_get_recommended_courses(self):

        df = pd.DataFrame({
            "년도": [2021, 2021],
            "학년": [2, 2],
            "학기": [1, 1],
            "과목명": ["자료구조", "일반교양영역"]
        })

        result = get_recommended_courses(
            curriculum_df=df,
            curriculum_year=2021,
            current_grade=2,
            current_semester=1
        )

        self.assertIn("자료구조", result["major"])
        self.assertIn("일반교양영역", result["general"])

    # -------------------------------------------------
    # get_missing_previous_required_courses 테스트
    # -------------------------------------------------

    def test_get_missing_previous_required_courses(self):

        major_df = pd.DataFrame({
            "이수구분": ["전공필수", "전공필수"],
            "수강 대상": ["1학년", "2학년"],
            "교과목명": ["자료구조", "운영체제"]
        })

        completed_set = {
            "자료구조"
        }

        result = get_missing_previous_required_courses(
            major_df=major_df,
            current_grade=3,
            completed_set=completed_set
        )

        self.assertEqual(result, ["운영체제"])

    # -------------------------------------------------
    # calculate_remaining_requirements 테스트
    # -------------------------------------------------

    def test_calculate_remaining_requirements(self):

        graduation_rule = {
            "requirements": {
                "major": {
                    "types": {
                        "major_required": {
                            "min_credits": 15
                        },
                        "major_elective": {
                            "min_credits": 20
                        }
                    }
                },
                "general_education": {
                    "areas": {}
                }
            }
        }

        graduation_status = {
            "major_required": 9,
            "major_elective": 10,
            "areas": {},
            "subareas": {}
        }

        result = calculate_remaining_requirements(
            graduation_rule,
            graduation_status
        )

        self.assertEqual(
            result["major_required"],
            6
        )

        self.assertEqual(
            result["major_elective"],
            10
        )

    # -------------------------------------------------
    # load 함수 테스트
    # -------------------------------------------------

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"test": 123}'
    )
    def test_load_students_data(self, mock_file):

        result = load_students_data("dummy.json")

        self.assertEqual(result["test"], 123)

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"rule_sets": {}}'
    )
    def test_load_graduation_rules(self, mock_file):

        result = load_graduation_rules("dummy.json")

        self.assertIn("rule_sets", result)

    @patch("pandas.read_csv")
    def test_load_curriculum_model(self, mock_csv):

        mock_csv.return_value = pd.DataFrame()

        result = load_curriculum_model("dummy.csv")

        self.assertIsInstance(result, pd.DataFrame)

    @patch("pandas.read_csv")
    def test_load_major_courses(self, mock_csv):

        mock_csv.return_value = pd.DataFrame()

        result = load_major_courses("dummy.csv")

        self.assertIsInstance(result, pd.DataFrame)

    @patch("scheduler.course_recommender.pd.read_csv")
    def test_load_completed_courses_filters_student(self, mock_read_csv):

        mock_read_csv.return_value = pd.DataFrame([
            {
                "student_id": "20210001",
                "교과목명": "A",
                "학점": 3,
                "이수구분": "major",
                "영역": "area1",
                "세부영역": "sub1"
            },
            {
                "student_id": "20210002",
                "교과목명": "B",
                "학점": 2,
                "이수구분": "general",
                "영역": "area2",
                "세부영역": "sub2"
            }
        ])

        result = load_completed_courses(
            csv_path="dummy.csv",
            student_id="20210001"
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "A")
        self.assertEqual(result[0]["credit"], 3)

    def test_calculate_remaining_requirements_with_subarea_min(self):

        graduation_rule = {
            "requirements": {
                "major": {
                    "types": {
                        "major_required": {
                            "min_credits": 15
                        },
                        "major_elective": {
                            "min_credits": 20
                        }
                    }
                },
                "general_education": {
                    "areas": {
                        "area1": {
                            "name": "GeneralA",
                            "min_credits": None,
                            "subareas": {
                                "sub1": {
                                    "name": "SubA",
                                    "min_credits": 3
                                }
                            }
                        }
                    }
                }
            }
        }

        graduation_status = {
            "major_required": 15,
            "major_elective": 20,
            "areas": {},
            "subareas": {
                "SubA": 1
            }
        }

        result = calculate_remaining_requirements(
            graduation_rule,
            graduation_status
        )

        self.assertEqual(result["areas"]["GeneralA"]["SubA"], 2)

    def test_calculate_remaining_requirements_with_total_area_credit(self):

        graduation_rule = {
            "requirements": {
                "major": {
                    "types": {
                        "major_required": {
                            "min_credits": 15
                        },
                        "major_elective": {
                            "min_credits": 20
                        }
                    }
                },
                "general_education": {
                    "areas": {
                        "area1": {
                            "name": "GeneralTotal",
                            "min_credits": 6,
                            "subareas": {
                                "sub1": {
                                    "name": "SubA"
                                },
                                "sub2": {
                                    "name": "SubB"
                                }
                            }
                        }
                    }
                }
            }
        }

        graduation_status = {
            "major_required": 15,
            "major_elective": 20,
            "areas": {},
            "subareas": {
                "SubA": 3
            }
        }

        result = calculate_remaining_requirements(
            graduation_rule,
            graduation_status
        )

        self.assertEqual(
            result["areas"]["GeneralTotal"]["총필요학점"],
            3
        )
        self.assertEqual(
            result["areas"]["GeneralTotal"]["선택가능영역"],
            ["SubB"]
        )

    def test_calculate_remaining_requirements_with_expanded_general_area(self):

        graduation_rule = {
            "requirements": {
                "major": {
                    "types": {
                        "major_required": {
                            "min_credits": 15
                        },
                        "major_elective": {
                            "min_credits": 20
                        }
                    }
                },
                "general_education": {
                    "areas": {
                        "area1": {
                            "name": "확대교양",
                            "min_credits": 6,
                            "subareas": {
                                "sub1": {
                                    "name": "SubA"
                                }
                            }
                        }
                    }
                }
            }
        }

        graduation_status = {
            "major_required": 15,
            "major_elective": 20,
            "areas": {
                "확대교양": 2
            },
            "subareas": {}
        }

        result = calculate_remaining_requirements(
            graduation_rule,
            graduation_status
        )

        self.assertEqual(
            result["areas"]["확대교양"]["총필요학점"],
            4
        )

    # -------------------------------------------------
    # get_final_recommendations 테스트
    # -------------------------------------------------

    @patch("scheduler.course_recommender.load_completed_courses")
    @patch("scheduler.course_recommender.get_missing_previous_required_courses")
    @patch("scheduler.course_recommender.get_recommended_courses")
    @patch("scheduler.course_recommender.calculate_remaining_requirements")
    @patch("scheduler.course_recommender.analyze_graduation_status")
    @patch("scheduler.course_recommender.get_graduation_rule")
    def test_get_final_recommendations(
        self,
        mock_rule,
        mock_status,
        mock_remaining,
        mock_recommended,
        mock_missing,
        mock_completed
    ):

        mock_rule.return_value = {
            "requirements": {}
        }

        mock_completed.return_value = []

        mock_status.return_value = {
            "completed_course_names": set()
        }

        mock_remaining.return_value = {
            "areas": {}
        }

        mock_recommended.return_value = {
            "major": ["운영체제"],
            "general": ["영어"]
        }

        mock_missing.return_value = ["자료구조"]

        students = [
            {
                "student_id": "20210001",
                "curriculum_year": 2021,
                "grade": 2
            }
        ]

        result = get_final_recommendations(
            student_id="20210001",
            target_semester=1,
            students_json_data=students
        )

        self.assertIn(
            "recommended_major_courses",
            result
        )

        self.assertIn(
            "missing_required_major_courses",
            result
        )

    def test_get_final_recommendations_invalid_student(self):

        result = get_final_recommendations(
            student_id="99999999",
            target_semester=1,
            students_json_data=[]
        )

        self.assertIn("error", result)
    
    @patch("scheduler.course_recommender.get_graduation_rule")
    def test_get_final_recommendations_no_rule(
    self,
    mock_rule
    ):

     mock_rule.return_value = None

     students = [
         {
             "student_id": "20210001",
             "curriculum_year": 2021,
             "grade": 2
         }
     ]

     result = get_final_recommendations(
         student_id="20210001",
         target_semester=1,
         students_json_data=students
     )

     self.assertIn("error", result)

    @patch("scheduler.course_recommender.load_completed_courses")
    @patch("scheduler.course_recommender.get_missing_previous_required_courses")
    @patch("scheduler.course_recommender.get_recommended_courses")
    @patch("scheduler.course_recommender.calculate_remaining_requirements")
    @patch("scheduler.course_recommender.analyze_graduation_status")
    @patch("scheduler.course_recommender.get_graduation_rule")
    def test_get_final_recommendations_completed_course_case(
    self,
    mock_rule,
    mock_status,
    mock_remaining,
    mock_recommended,
    mock_missing,
    mock_completed
    ):

     mock_rule.return_value = {
         "requirements": {}
     }

     mock_completed.return_value = [
         {
            "name": "자료구조"
         }
     ]

     mock_status.return_value = {
         "completed_course_names": {"자료구조"}
     }

     mock_remaining.return_value = {
         "areas": {}
     }

     mock_recommended.return_value = {
         "major": [],
         "general": []
     }

     mock_missing.return_value = []

     students = [
         {
             "student_id": "20210001",
             "curriculum_year": 2021,
            "grade": 2
         }
     ]

     result = get_final_recommendations(
         student_id="20210001",
         target_semester=1,
         students_json_data=students
     )

     self.assertIsInstance(result, dict)

    @patch("scheduler.course_recommender.load_completed_courses")
    @patch("scheduler.course_recommender.get_missing_previous_required_courses")
    @patch("scheduler.course_recommender.get_recommended_courses")
    @patch("scheduler.course_recommender.calculate_remaining_requirements")
    @patch("scheduler.course_recommender.analyze_graduation_status")
    @patch("scheduler.course_recommender.get_graduation_rule")
    def test_get_final_recommendations_filters_needed_general_areas(
    self,
    mock_rule,
    mock_status,
    mock_remaining,
    mock_recommended,
    mock_missing,
    mock_completed
    ):

     mock_rule.return_value = {
         "requirements": {}
     }

     mock_completed.return_value = []

     mock_status.return_value = {
         "completed_course_names": set()
     }

     mock_remaining.return_value = {
         "areas": {
             "AreaTotal": {
                 "총필요학점": 3,
                 "선택가능영역": ["SubA"]
             },
             "AreaSub": {
                 "SubB": 2,
                 "SubC": 0
             }
         }
     }

     mock_recommended.return_value = {
         "major": ["MajorA"],
         "general": ["GeneralA"]
     }

     mock_missing.return_value = []

     students = [
         {
             "student_id": "20210001",
             "curriculum_year": 2021,
             "grade": 2
         }
     ]

     result = get_final_recommendations(
         student_id="20210001",
         target_semester=1,
         students_json_data=students
     )

     self.assertEqual(
         result["needed_general_areas"]["AreaTotal"]["총필요학점"],
         3
     )
     self.assertEqual(
         result["needed_general_areas"]["AreaSub"],
         {"SubB": 2}
     )

if __name__ == "__main__":
    unittest.main()
