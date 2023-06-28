"""
Test functionality related to sharing weekend challenges
"""

import mock
import pytest

from habot.functionality.sharing_weekend_challenge import (
        CountUnusedQuestions,
        AddQuestion,
    )
from habot.message import PrivateMessage
from habot.io.yaml import YAMLFileIO
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


@pytest.fixture
def temporary_editable_question_file(tmpdir, monkeypatch):
    """
    Return a temporary file with a number of questions already present.

    The questions are the same as in tests/data/questions.yml.
    """
    question_file = tmpdir / "questions.yml"
    with open(
                "tests/data/single_unused_question.yml",
                "r",
                encoding="utf-8"
            ) as infile, \
            open(
                question_file,
                "w",
                encoding="utf-8"
                ) as outfile:
        outfile.write(infile.read())

    monkeypatch.setattr(
        "habot.functionality.sharing_weekend_challenge.QUESTIONS_PATH",
        question_file
        )

    return question_file


@pytest.fixture
def new_question_message():
    """
    Return a message requesting adding a new question.
    """
    content = (
        "add-new-question\n"
        "What is an interesting question?\n"
        "Then there's the description too, which can be long too. Many "
        "sentences maybe. No newlines though."
        )
    return PrivateMessage(SIMPLE_USER["id"], "to_id",
                          content=content)


# pylint: disable=redefined-outer-name

def test_add_single_question(temporary_editable_question_file,
                             new_question_message):
    """
    Check that a single question is added to the question list without
    editing the existing questions.
    """
    initial_all_questions = len(
        YAMLFileIO.read_question_list(
            temporary_editable_question_file,
            unused_only=False
            )
        )
    initial_unused_questions = len(
        YAMLFileIO.read_question_list(
            temporary_editable_question_file,
            unused_only=True
            )
        )

    adder = AddQuestion()
    response = adder.act(new_question_message)

    all_questions = len(
        YAMLFileIO.read_question_list(
            temporary_editable_question_file,
            unused_only=False
            )
        )
    unused_questions = len(
        YAMLFileIO.read_question_list(
            temporary_editable_question_file,
            unused_only=True
            )
        )

    assert all_questions == initial_all_questions + 1
    assert unused_questions == initial_unused_questions + 1

    assert "Added the following question" in response
    assert "What is an interesting question?" in response
    assert "Then there's the description too" in response
