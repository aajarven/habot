"""
Test functionality related to sharing weekend challenges
"""

import mock

from habot.functionality.sharing_weekend_challenge import CountUnusedQuestions
from habot.message import PrivateMessage
from tests.conftest import SIMPLE_USER


@mock.patch("habot.functionality.sharing_weekend_challenge.QUESTIONS_PATH",
            "tests/data/questions.yml")
def test_count_unused_questions():
    """
    Check that the correct number of unused questions is reported
    """
    test_message = PrivateMessage(SIMPLE_USER["id"], "to_id",
                                  content="count-unused-questions")
    counter = CountUnusedQuestions()
    assert "There are 4 unused" in counter.act(test_message)
