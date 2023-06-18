"""
Test question reading and writing functionality
"""

import pytest

from habot.io.yaml import YAMLFileIO


@pytest.fixture
def basic_test_questions():
    """
    Return a basic set of test questions read from a file
    """
    return YAMLFileIO.read_question_list("tests/data/questions.yml")

# Pylint does not understand fixtures and well-named tests don't necessarily
# need docstrings.
# pylint: disable=missing-function-docstring,redefined-outer-name


def test_right_number_of_questions(basic_test_questions):
    assert len(basic_test_questions) == 5


def test_right_number_of_used_questions(basic_test_questions):
    assert sum(basic_test_questions.values()) == 1


def test_read_write_read_produces_original_questions(
        basic_test_questions, tmp_path):
    """
    Check questions don't change on writing to file and reading back.

    The questions themselves, as well as whether they have been used, must not
    be altered. Neither must questions be added or removed.
    """
    question_output_path = tmp_path / "questions.yml"
    YAMLFileIO.write_question_list(basic_test_questions, question_output_path)
    read_questions = YAMLFileIO.read_question_list(question_output_path)

    for question in read_questions:
        assert question in basic_test_questions.keys()
        assert read_questions[question] == basic_test_questions[question]

    assert len(read_questions) == len(basic_test_questions)
