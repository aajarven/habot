"""
Test HabiticaOperator class
"""

import pytest
from unittest import mock

from conf.header import HEADER
from habot.habitica_operations import (HabiticaOperator, NotFoundException,
                                       AmbiguousOperationException)


@pytest.fixture()
def test_operator():
    """
    Create a HabiticaOperator for tests and mock responses for it.
    """
    return HabiticaOperator(HEADER)

# pylint: disable=redefined-outer-name


@pytest.mark.parametrize(
    ["task_name", "task_type"],
    [
        ("Test TODO 1", None),
        ("Test TODO 1", "todo"),
        ("Test", "daily"),
        ("Test", "habit"),
    ]
)
@pytest.mark.usefixtures("mock_task_finding")
def test_task_finder(test_operator, task_name, task_type):
    """
    Test that task finder is able to find a matching task when one exists.
    """
    found_task = test_operator.find_task(task_name, task_type=task_type)
    assert found_task


@pytest.mark.parametrize(
    ["task_name", "exception"],
    [
        ("nonexistent task", NotFoundException),
        ("Test", AmbiguousOperationException),
    ]
)
@pytest.mark.usefixtures("mock_task_finding")
def test_task_finder_exception(test_operator, task_name, exception):
    """
    Test that NotFoundException is raised when task is not found.
    """
    with pytest.raises(exception):
        test_operator.find_task(task_name)


@pytest.mark.usefixtures("mock_task_ticking")
def test_tick(requests_mock, test_operator):
    """
    Test that tick_task sends the correct request.
    """
    tick_url = ("https://habitica.com/api/v3/tasks/{}/score/up"
                "".format("963e2ced-fa22-4b18-a22b-c423764e26f3"))
    test_operator.tick_task("Test habit")

    assert len(requests_mock.request_history) == 2
    tick_request = requests_mock.request_history[1]
    assert tick_url in tick_request.url


@mock.patch("habitica_helper.task.Task.add_to_user")
@pytest.mark.parametrize(
    ("name", "note", "type_"),
    [
        ("test task", "test note", "todo"),
        ("test task", None, "todo"),
        ("test task", "", "todo"),
        ("test habit", "do domething cool", "habit"),
        ("test daily", "drink water", "daily"),
    ]
)
def test_add_task_successfully(mock_add, name, note, type_, test_operator):
    """
    Ensure that `add_task` method call works in happy cases.

    Tasks classes with and without notes must be created successfully with the
    correct text, notes and type and `add_to_user` must be called.
    """
    task = test_operator.add_task(name, note, type_)
    mock_add.assert_called_with(HEADER)

    assert task.text == name

    if note:
        assert task.notes == note
    else:
        assert not task.notes

    if type_:
        assert task.tasktype == type_
    else:
        assert task.tasktype == "todo"
