"""
Shared test stuff
"""

import re
import mysql.connector
import pytest
import testing.mysqld

from tests.data.test_tasks import TEST_TASKS


@pytest.fixture(scope="module")
def db_connection_fx():
    """
    Return a database connection.
    """
    with testing.mysqld.Mysqld() as mysqld:
        conn = mysql.connector.connect(**mysqld.dsn())
        yield conn


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


@pytest.fixture()
def header_fx():
    """
    Return a header dict for testing.
    """
    return {
        "x-client":
            "f687a6c7-860a-4c7c-8a07-9d0dcbb7c831-habot_testing",
        "x-api-user": "totally-not-a-real-userid",
        "x-api-key":  "totally-not-a-real-apikey",
    }
