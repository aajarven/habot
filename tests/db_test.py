"""
Tests for database operations.
"""

import datetime
import mysql.connector
import pytest

from conf.db import TABLES
from tests.conftest import (SIMPLE_USER, NAMEDIFF_USER, CHARSET_USER,
                            SHAREBDAY_USER)


def test_db_operator(testdata_db_operator):
    """
    Test that the monkeypatched database operator has test data in its db
    """
    result = testdata_db_operator.query_table("members")
    assert len(result) == 4


@pytest.mark.parametrize(
    ["columns", "condition", "expected_result"],
    [
        (None, None,
         [SIMPLE_USER, NAMEDIFF_USER, CHARSET_USER, SHAREBDAY_USER]),
        (None, "displayname like 'habitician'", [NAMEDIFF_USER]),
        (None, "displayname like 'nobodyhere'", []),
        ("displayname, loginname", "displayname like 'habitician'",
         [{"displayname": "habitician", "loginname": "habiticianlogin"}]),
        (["displayname", "loginname"], "displayname like 'habitician'",
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


@pytest.mark.parametrize(
    ["condition_dict", "expected_result"],
    [
        ({"displayname": "habitician"}, [NAMEDIFF_USER]),
        ({"displayname": "nobodyhere"}, []),
    ]
)
def test_query_table_based_on_dict(testdata_db_operator, condition_dict,
                                   expected_result):
    """
    Test that querying a table works.

    The following cases are tested:
     - all data is fetched
     - single row is selected based on a condition
     - condition with zero matching rows passed, so no rows are returned
    """
    query_result = testdata_db_operator.query_table_based_on_dict(
        "members", condition_dict)
    assert len(query_result) == len(expected_result)
    for row in expected_result:
        assert _dict_in_list(row, query_result)


@pytest.mark.parametrize(
    ["columns", "expected_exception"],
    [
        (1, ValueError),
        ("nonexistent_column", mysql.connector.Error),
    ]
)
def test_query_table_exceptions(testdata_db_operator, columns,
                                expected_exception):
    """
    Test that an error is raised if there's a problem with the parameters.

    This is tested with wrong type of column identifier and with a non-existing
    column.
    """
    with pytest.raises(expected_exception):
        testdata_db_operator.query_table("members", columns=columns)


def test_insert_data(testdata_db_operator, purge_and_init_memberdata_fx):
    """
    Test that a row can be inserted into the database using DBOperator.

    Resets the state of the test database in the end.
    """
    new_member_data = {"id": "abc123", "loginname": "newguy",
                       "displayname": "newguy9004",
                       "birthday": datetime.date(2020, 5, 5)}
    testdata_db_operator.insert_data("members", new_member_data)

    cursor = testdata_db_operator.conn.cursor()
    cursor.execute("SELECT * FROM members where id='abc123'")
    result = cursor.fetchall()
    assert len(result) == 1
    data = result[0]
    for value in new_member_data.values():
        assert value in data
    cursor.close()
    purge_and_init_memberdata_fx()


@pytest.mark.parametrize("updated_id", [SIMPLE_USER["id"], "nonexistent_id"])
def test_update_data(testdata_db_operator, updated_id,
                     purge_and_init_memberdata_fx):
    """
    Test that updating based on primary key is possible
    """
    testdata_db_operator.update_row("members", updated_id,
                                    {"displayname": "cooler_name"})

    updated_data = SIMPLE_USER.copy()
    updated_data["displayname"] = "cooler_name"

    cursor = testdata_db_operator.conn.cursor()
    cursor.execute("SELECT * FROM members "
                   f"WHERE id='{updated_id}'")

    result = cursor.fetchall()
    if "nonexistent" in updated_id:
        # a new row is not inserted using update
        assert len(result) == 0
    else:
        # but existing values are updated
        data = result[0]
        for value in data:
            assert value in updated_data.values()
    cursor.close()
    purge_and_init_memberdata_fx()


def test_delete_row(testdata_db_operator, purge_and_init_memberdata_fx):
    """
    Test that a row can be removed using the primary key
    """
    testdata_db_operator.delete_row("members", "id", SIMPLE_USER["id"])
    query_result = testdata_db_operator.query_table(
        "members", condition=f"id='{SIMPLE_USER['id']}'")
    assert len(query_result) == 0
    purge_and_init_memberdata_fx()


def test_delete_illegal_row(testdata_db_operator):
    """
    Test that an exception is raised when not using primary key as condition.

    The row must also not be removed from the database.
    """
    with pytest.raises(ValueError):
        testdata_db_operator.delete_row("members", "loginname",
                                        SIMPLE_USER["loginname"])
    query_result = testdata_db_operator.query_table(
        "members",
        condition=f"id='{SIMPLE_USER['id']}'",
        )
    assert len(query_result) == 1


@pytest.mark.parametrize(
    ["method", "kwargs", "expected_value"],
    [
        ("databases", {},
         ["information_schema", "habdb", "mysql", "performance_schema",
          "sys", "test"]),
        ("tables", {}, TABLES.keys()),
        ("columns", {"table": "members"},
         {"id": {"Type": "varchar(50)", "Null": "NO", "Key": "PRI",
                 "Default": None, "Extra": ""},
          "displayname": {"Type": "varchar(255)", "Null": "YES", "Key": "",
                          "Default": None, "Extra": ""},
          "loginname": {"Type": "varchar(255)", "Null": "YES", "Key": "",
                        "Default": None, "Extra": ""},
          "birthday": {"Type": "date", "Null": "YES", "Key": "",
                       "Default": None, "Extra": ""},
          "lastlogin": {"Type": "date", "Null": "YES", "Key": "",
                        "Default": None, "Extra": ""},
          }),
    ]
)
def test_utils(testdata_db_operator, method, kwargs, expected_value):
    """
    Test that utility functions for the db work
    """
    result = getattr(testdata_db_operator, method)(**kwargs)
    if isinstance(result, list):
        assert set(result) == set(expected_value)
    else:
        assert result == expected_value


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
