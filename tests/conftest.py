"""
Shared test stuff
"""

import datetime
import re
import unittest.mock

import mysql.connector
import pytest
from surrogate import surrogate
import testing.mysqld

from habot.db import DBOperator
from tests.data.test_tasks import TEST_TASKS

# pylint doesn't handle fixtures well
# pylint: disable=redefined-outer-name


@pytest.fixture(autouse=True)
@surrogate("conf.secrets.habitica_credentials")
def test_credentials():
    """
    Set the configuration values of PLAYER_USER_ID and PLAYER_API_TOKEN.

    Returns them as a dict for use in other tests.

    This is done using different patching mechanic (surrogate + unittest.mock
    instead of monkeypatch) than most other mocking/patching due to this being
    required in order to patch a possibly non-existent module.
    """
    credentials = {"PLAYER_USER_ID": "totally-not-a-real-user-id",
                   "PLAYER_API_TOKEN": "totally-not-a-real-apikey"}
    unittest.mock.patch("conf.secrets.habitica_credentials",
                        "PLAYER_USER_ID", credentials["PLAYER_USER_ID"])
    unittest.mock.patch("conf.secrets.habitica_credentials",
                        "PLAYER_API_TOKEN", credentials["PLAYER_API_TOKEN"])
    return credentials


@pytest.fixture(autouse=True)
def prevent_online_requests(monkeypatch):
    """
    Patch urlopen so that all non-patched requests raise an error.
    """
    def urlopen_error(self, method, url, *args, **kwargs):
        raise RuntimeError(
                "Requests are not allowed, but a test attempted a {} request "
                "to {}://{}{}".format(method, self.scheme, self.host, url))

    monkeypatch.setattr(
        "urllib3.connectionpool.HTTPConnectionPool.urlopen", urlopen_error
    )


@pytest.fixture(scope="session")
def sessionmonkey():
    """
    Session-scoped monkeypatch class for slow database test setup.
    """
    # pylint: disable=import-outside-toplevel
    from _pytest.monkeypatch import MonkeyPatch
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope="session")
def db_connection_fx(sessionmonkey):
    """
    Patch mysql connector to return a test database connection.

    Yield that database connection.
    """
    with testing.mysqld.Mysqld() as mysqld:
        conn = mysql.connector.connect(**mysqld.dsn())

        def _connection_factory(**kwargs):
            # pylint: disable=unused-argument
            return conn
        sessionmonkey.setattr(mysql.connector, "connect", _connection_factory)

        yield conn


@pytest.fixture()
def mock_task_ticking(mock_task_finding, requests_mock):
    """
    Fake a successful response for ticking any task
    """
    # pylint: disable=unused-argument
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
def header_fx(test_credentials):
    """
    Return a header dict for testing.
    """
    return {
        "x-client":
            "f687a6c7-860a-4c7c-8a07-9d0dcbb7c831-habot_testing",
        "x-api-user": test_credentials["PLAYER_USER_ID"],
        "x-api-key": test_credentials["PLAYER_API_TOKEN"],
    }


@pytest.fixture(scope="module")
def testdata_db_operator(purge_and_init_memberdata_fx):
    """
    Yield monkeypatched DBOperator that uses test database.

    The same database connection is used for all tests, but the databases and
    tables in it are regenerated for each test.
    """
    purge_and_init_memberdata_fx()
    operator = DBOperator()
    yield operator


# A simple user: one with identical diplay and loginnames
SIMPLE_USER = {"id": "9cb40345-720f-4c9e-974d-18e016d9564d",
               "displayname": "testuser",
               "loginname": "testuser",
               "birthday": datetime.date(2016, 12, 4)}

# User wth different display and login names
NAMEDIFF_USER = {"id": "a431b1a5-d287-4c34-93c4-7d607905a947",
                 "displayname": "habitician",
                 "loginname": "habiticianlogin",
                 "birthday": datetime.date(2019, 5, 31)}

# User with non-ascii characters in displayname
CHARSET_USER = {"id": "7319d61c-1940-460d-8dc8-007f7e9537f0",
                "displayname": "somedüde",
                "loginname": "somedude",
                "birthday": datetime.date(2019, 5, 31)}

# User sharing a birthday with another user
SHAREBDAY_USER = {"id": "b5845235-a344-4f52-a08b-02084cab00c4",
                  "displayname": "showingYaMyBDAY",
                  "loginname": "birthdayfella",
                  "birthday": datetime.date(2019, 5, 31)}

ALL_USERS = [SIMPLE_USER, NAMEDIFF_USER, CHARSET_USER, SHAREBDAY_USER]


@pytest.fixture(scope="module")
def purge_and_init_memberdata_fx(db_connection_fx):
    """
    Remove all data from the database and reinitialize with test member data.
    """
    def _reset():
        cursor = db_connection_fx.cursor()
        cursor.execute("DROP DATABASE IF EXISTS habdb")
        cursor.execute("CREATE DATABASE habdb")
        db_connection_fx.commit()

        operator = DBOperator()
        operator._ensure_tables()  # pylint: disable=protected-access
        cursor.execute("USE habdb")
        cursor.execute("INSERT INTO members "
                       "(id, displayname, loginname, birthday) "
                       "values "
                       "{}, {}, {}, {}".format(
                           _member_dict_to_values(SIMPLE_USER),
                           _member_dict_to_values(NAMEDIFF_USER),
                           _member_dict_to_values(CHARSET_USER),
                           _member_dict_to_values(SHAREBDAY_USER),
                           ))
        db_connection_fx.commit()
        cursor.close()
    return _reset


def _member_dict_to_values(member_dict):
    """
    Return a string that represents the given member dict for INSERT statement
    """
    return "('{}', '{}', '{}', '{}')".format(member_dict["id"],
                                             member_dict["displayname"],
                                             member_dict["loginname"],
                                             member_dict["birthday"])


@pytest.fixture
def configure_test_admin(monkeypatch):
    """
    Set one of the test data users as admin.
    """
    monkeypatch.setattr("conf.conf.ADMIN_UID", SIMPLE_USER["id"])
