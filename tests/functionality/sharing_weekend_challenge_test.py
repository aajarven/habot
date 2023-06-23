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
    assert ("There are 4 unused sharing weekend questions"
            in counter.act(test_message))


@mock.patch("habot.functionality.sharing_weekend_challenge.QUESTIONS_PATH",
            "tests/data/single_unused_question.yml")
def test_count_unused_singular():
    """
    Check that singular form is used in the response with only one question.
    """
    test_message = PrivateMessage(SIMPLE_USER["id"], "to_id",
                                  content="count-unused-questions")
    counter = CountUnusedQuestions()
    assert ("There is 1 unused sharing weekend question"
            in counter.act(test_message))
