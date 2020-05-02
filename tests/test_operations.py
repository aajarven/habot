"""
Test HabiticaOperator class
"""

import pytest

from conf.header import HEADER
from habot.habitica_operations import (HabiticaOperator, NotFoundException,
                                       AmbiguousOperationException)
from tests.data.test_tasks import TEST_TASKS


@pytest.fixture()
def test_operator(requests_mock):
    """
    Create a HabiticaOperator for tests and mock responses for it.
    """
    requests_mock.get("https://habitica.com/api/v3/tasks/user",
                      json={"success": True, "data": TEST_TASKS})
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
def test_task_finder_exception(test_operator, task_name, exception):
    """
    Test that NotFoundException is raised when task is not found.
    """
    with pytest.raises(exception):
        test_operator.find_task(task_name)


def test_tick(requests_mock, test_operator):
    """
    Test that tick_task sends the correct request.
    """
    tick_url = ("https://habitica.com/api/v3/tasks/{}/score/up"
                "".format("963e2ced-fa22-4b18-a22b-c423764e26f3"))
    requests_mock.post(tick_url)
    test_operator.tick_task("Test habit")

    assert len(requests_mock.request_history) == 2
    tick_request = requests_mock.request_history[1]
    assert tick_url in tick_request.url
