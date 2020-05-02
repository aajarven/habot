"""
Shared test stuff
"""

import re

import pytest

from tests.data.test_tasks import TEST_TASKS


@pytest.fixture()
def mock_task_ticking(mock_task_finding, requests_mock):
    """
    Fake a successful response for ticking any task
    """
    tick_matcher = re.compile("https://habitica.com/api/v3/tasks/.*/score/")
    requests_mock.post(tick_matcher)


@pytest.fixture()
def mock_task_finding(requests_mock):
    """
    Return the standard test data tasks for task finding
    """
    requests_mock.get("https://habitica.com/api/v3/tasks/user",
                      json={"success": True, "data": TEST_TASKS})
