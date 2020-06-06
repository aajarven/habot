"""
Tests for database operations.
"""

import mysql.connector

import pytest
import testing.mysqld

from habot.db import DBOperator


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
                   " 'testuser', 'testuserlogin', '2016-12-04'), "
                   "('a431b1a5-d287-4c34-93c4-7d607905a947',"
                   " 'habtician', 'habitician', '2019-05-31'), "
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
