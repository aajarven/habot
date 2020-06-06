"""
Tests for database operations.
"""

import datetime

import mysql.connector

import pytest
import testing.mysqld

from habot.db import DBOperator

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


@pytest.fixture(scope="module")
def connection_fx():
    """
    Return a database connection.
    """
    with testing.mysqld.Mysqld() as mysqld:
        conn = mysql.connector.connect(**mysqld.dsn())
        yield conn

# pylint: disable=redefined-outer-name


@pytest.fixture()
def testdata_db_operator(connection_fx, monkeypatch):
    """
    Yield monkeypatched DBOperator that uses test database.

    The same database connection is used for all tests, but the databases and
    tables in it are regenerated for each test.
    """
    cursor = connection_fx.cursor()
    cursor.execute("DROP DATABASE IF EXISTS habdb")
    cursor.execute("CREATE DATABASE habdb")

    def _connection_factory(**kwargs):
        # pylint: disable=unused-argument
        return connection_fx
    monkeypatch.setattr(mysql.connector, "connect", _connection_factory)

    operator = DBOperator()

    cursor.execute("USE habdb")
    cursor.execute("INSERT INTO members "
                   "(id, displayname, loginname, birthday) "
                   "values "
                   "('9cb40345-720f-4c9e-974d-18e016d9564d',"
                   " 'testuser', 'testuser', '2016-12-04'), "
                   "('a431b1a5-d287-4c34-93c4-7d607905a947',"
                   " 'habitician', 'habiticianlogin', '2019-05-31'), "
                   "('7319d61c-1940-460d-8dc8-007f7e9537f0',"
                   " 'somedüde', 'somedude', '2019-05-31')"
                   )
    connection_fx.commit()
    cursor.close()
    yield operator


def test_db_operator(testdata_db_operator):
    """
    Test that the monkeypatched database operator has test data in its db
    """
    result = testdata_db_operator.query_table("members")
    assert len(result) == 3


@pytest.mark.parametrize(
    ["columns", "condition", "expected_result"],
    [
        (None, None, [SIMPLE_USER, NAMEDIFF_USER, CHARSET_USER]),
        (None, "displayname like 'habitician'", [NAMEDIFF_USER]),
        (None, "displayname like 'nobodyhere'", []),
        ("displayname, loginname", "displayname like 'habitician'",
         [{"displayname": "habitician", "loginname": "habiticianlogin"}]),
    ]
)
def test_query_table(testdata_db_operator, columns, condition,
                     expected_result):
    """
    Test that querying a table works.

    The following cases are tested:
     - all data is fetched
     - single row is selected based on a condition
     - condition with zero matching rows passed, so no rows are returned
     - only some fields are returned
    """
    query_result = testdata_db_operator.query_table("members", columns=columns,
                                                    condition=condition)
    assert len(query_result) == len(expected_result)
    for row in expected_result:
        assert _dict_in_list(row, query_result)


def _dict_in_list(dict_to_find, dict_list):
    """
    Return True if dict_to_find is present in the dict_list.
    """
    keys = dict_to_find.keys()
    for dict_ in dict_list:
        violations = False
        for key in keys:
            if key not in dict_ or dict_[key] != dict_to_find[key]:
                violations = True
                break
        if not violations:
            return True
    return False
