import unittest
from unittest.mock import patch

from llm.llm_input import main


class LLMInputTest(unittest.TestCase):

    @patch("builtins.print")
    def test_main_runs(self, mock_print):

        try:
            main()
            success = True

        except Exception:
            success = False

        self.assertTrue(success)


    @patch("llm.llm_input.parse_schedule_text")
    def test_main_exception(self, mock_parse):

     mock_parse.side_effect = Exception("LLM Error")

     main()
     
if __name__ == "__main__":
    unittest.main()