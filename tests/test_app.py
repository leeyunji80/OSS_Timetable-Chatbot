import unittest
from unittest.mock import patch, mock_open
import json
import os

from ui.app import app, get_user_data_path


class TestFlaskApp(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    # -------------------------------------------------
    # index 테스트
    # -------------------------------------------------

    def test_index_page(self):

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)

    # -------------------------------------------------
    # get_user_data_path 테스트
    # -------------------------------------------------

    def test_get_user_data_path(self):

        student_id = "20210001"

        path = get_user_data_path(student_id)

        self.assertIn(
            f"chat_sessions_{student_id}.json",
            path
        )

    # -------------------------------------------------
    # save_chat 테스트
    # -------------------------------------------------

    @patch("builtins.open", new_callable=mock_open)
    def test_save_chat_success(self, mock_file):

        response = self.client.post(
            '/save_chat',
            json={
                "student_id": "20210001",
                "chat_sessions": []
            }
        )

        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])

    def test_save_chat_no_student_id(self):

        response = self.client.post(
            '/save_chat',
            json={
                "chat_sessions": []
            }
        )

        self.assertEqual(response.status_code, 400)

    # -------------------------------------------------
    # get_chats 테스트
    # -------------------------------------------------

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open,
           read_data='[{"id":1}]')
    def test_get_chats_success(
        self,
        mock_file,
        mock_exists
    ):

        mock_exists.return_value = True

        response = self.client.get(
            '/get_chats?student_id=20210001'
        )

        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        self.assertEqual(len(data["chat_sessions"]), 1)

    def test_get_chats_no_student_id(self):

        response = self.client.get('/get_chats')

        self.assertEqual(response.status_code, 400)

    # -------------------------------------------------
    # delete_chat 테스트
    # -------------------------------------------------

    @patch("os.path.exists")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='[{"id":1},{"id":2}]'
    )
    def test_delete_chat_success(
        self,
        mock_file,
        mock_exists
    ):

        mock_exists.return_value = True

        response = self.client.post(
            '/delete_chat',
            json={
                "student_id": "20210001",
                "session_id": 1
            }
        )

        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])

    def test_delete_chat_missing_param(self):

        response = self.client.post(
            '/delete_chat',
            json={}
        )

        self.assertEqual(response.status_code, 400)

    @patch("os.path.exists")
    def test_delete_chat_file_not_found(
        self,
        mock_exists
    ):

        mock_exists.return_value = False

        response = self.client.post(
            '/delete_chat',
            json={
                "student_id": "20210001",
                "session_id": 1
            }
        )

        self.assertEqual(response.status_code, 404)

    # -------------------------------------------------
    # login 테스트
    # -------------------------------------------------

    @patch(
        "ui.app.students",
        [
            {
                "student_id": "20210001",
                "name": "홍길동"
            }
        ]
    )
    @patch("os.path.exists")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='[]'
    )
    def test_login_success(
        self,
        mock_file,
        mock_exists
    ):

        mock_exists.return_value = True

        response = self.client.post(
            '/login',
            json={
                "student_id": "20210001",
                "name": "홍길동"
            }
        )

        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])

    @patch("ui.app.students", [])
    def test_login_fail(self):

        response = self.client.post(
            '/login',
            json={
                "student_id": "99999999",
                "name": "테스트"
            }
        )

        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(data["success"])

    # -------------------------------------------------
    # chat API 테스트
    # -------------------------------------------------

    @patch("ui.app.draw_timetable_image")
    @patch("ui.app.generate_timetable_response")
    @patch("ui.app.parse_schedule_text_with_history")
    def test_chat_success(
        self,
        mock_parse,
        mock_generate,
        mock_draw
    ):

        mock_parse.return_value = json.dumps({
            "alternatives": [
                {
                    "timetable_title": "추천 시간표",
                    "recommendation_reason": "추천 완료"
                }
            ]
        })

        mock_generate.return_value = {
            "status": "success",
            "alternatives": [
                {
                    "timetable_title": "추천 시간표",
                    "recommendation_reason": "추천 완료"
                }
            ]
        }

        mock_draw.return_value = "test.png"

        response = self.client.post(
            '/chat',
            json={
                "message": "월공강",
                "student_id": "20210001"
            }
        )

        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("results", data)

    @patch("ui.app.parse_schedule_text_with_history")
    def test_chat_llm_fail(
        self,
        mock_parse
    ):

        mock_parse.side_effect = Exception("LLM Error")

        response = self.client.post(
            '/chat',
            json={
                "message": "테스트"
            }
        )

        self.assertEqual(response.status_code, 500)

    @patch("ui.app.parse_schedule_text_with_history")
    @patch("ui.app.generate_timetable_response")
    def test_chat_scheduler_fail(
        self,
        mock_generate,
        mock_parse
    ):

        mock_parse.return_value = json.dumps({})

        mock_generate.return_value = {
            "status": "fail",
            "message": "시간표 생성 실패"
        }

        response = self.client.post(
            '/chat',
            json={
                "message": "테스트"
            }
        )

        self.assertEqual(response.status_code, 400)
   
    def test_chat_empty_message(self):

        response = self.client.post(
            "/chat",
            json={}
        )

        self.assertEqual(response.status_code, 500)

    def test_chat_invalid_json(self):

        response = self.client.post(
            "/chat",
            data="invalid",
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

    @patch("os.path.exists")
    @patch(
    "builtins.open",
    new_callable=mock_open,
    read_data="invalid json"
    )
    def test_get_chats_json_decode_error(
        self,
        mock_file,
        mock_exists
        ):
        mock_exists.return_value = True

        response = self.client.get(
            "/get_chats?student_id=20210001"
        )

        self.assertEqual(response.status_code, 200)
        

    @patch("os.path.exists")
    @patch(
    "builtins.open",
    new_callable=mock_open,
    read_data="invalid json"
)
    def test_delete_chat_json_decode_error(
        self,
        mock_file,
        mock_exists
        ):

        mock_exists.return_value = True

        response = self.client.post(
            "/delete_chat",
            json={
                "student_id": "20210001",
                "session_id": 1
            }
        )

        self.assertEqual(response.status_code, 200)

    @patch(
    "ui.app.students",
    [
    {
    "student_id": "20210001",
    "name": "홍길동"
    }
    ]
    )
    @patch("os.path.exists")
    def test_login_without_saved_file(
        self,
        mock_exists
        ):
        mock_exists.return_value = False

        response = self.client.post(
            "/login",
            json={
                "student_id": "20210001",
                "name": "홍길동"
            }
        )

        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])

if __name__ == "__main__":
    unittest.main()