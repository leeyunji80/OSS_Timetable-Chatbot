import unittest
import os
import json
from unittest.mock import patch, MagicMock
from llm.llm_api import (
parse_schedule_text,
parse_schedule_text_with_history
)

from llm.llm_api import parse_schedule_text


class LLMApiTest(unittest.TestCase):

    def test_parse_schedule_text_returns_dict(self):

        api_key = os.environ.get("OPENAI_API_KEY")

        result = parse_schedule_text(
            "화요일 공강 만들고 오전 수업 제외",
            api_key
        )

        parsed_result = json.loads(result)

        self.assertIsInstance(parsed_result, dict)

    def test_parse_schedule_text_not_empty(self):

        api_key = os.environ.get("OPENAI_API_KEY")

        result = parse_schedule_text(
            "전공 위주 시간표 추천",
            api_key
        )

        parsed_result = json.loads(result)

        self.assertTrue(len(parsed_result) > 0)

    @patch("llm.llm_api.OpenAI")
    def test_parse_schedule_text_fail(self, mock_openai):

     mock_client = MagicMock()
     mock_openai.return_value = mock_client

     mock_response = MagicMock()
     mock_response.choices[0].message.parsed = None

     mock_client.beta.chat.completions.parse.return_value = mock_response

     result = parse_schedule_text(
         "시간표 추천해줘",
         "fake_api_key"
     )

     self.assertIn("error", result)
   
    @patch("llm.llm_api.OpenAI")
    def test_parse_schedule_text_with_history(self, mock_openai):

      mock_client = MagicMock()
      mock_openai.return_value = mock_client

      mock_parsed = MagicMock()

      mock_parsed.selected_courses = ["자료구조"]

      mock_parsed.model_dump_json.return_value = """
      {
          "selected_courses": ["자료구조"]
      }
      """

      mock_response = MagicMock()
      mock_response.choices[0].message.parsed = mock_parsed

      mock_client.beta.chat.completions.parse.return_value = mock_response

      result = parse_schedule_text_with_history(
          "session_1",
          "자료구조 넣어줘",
         "fake_api_key"
      )

      self.assertIn("자료구조", result)

    @patch("llm.llm_api.OpenAI")
    def test_selected_course_filtering(self, mock_openai):

       mock_client = MagicMock()
       mock_openai.return_value = mock_client

       mock_parsed = MagicMock()

       mock_parsed.selected_courses = [
           "자료구조",
           "운영체제"
       ]

       mock_parsed.model_dump_json.return_value = """
       {
           "selected_courses": ["자료구조"]
       }
       """

       mock_response = MagicMock()
       mock_response.choices[0].message.parsed = mock_parsed

       mock_client.beta.chat.completions.parse.return_value = mock_response

       result = parse_schedule_text(
           "자료구조 넣어줘",
           "fake_api_key"
       )

       self.assertIn("자료구조", result)
if __name__ == "__main__":
    unittest.main()