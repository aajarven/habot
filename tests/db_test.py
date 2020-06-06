"""
Tests for database operations.
"""

import mysql.connector

import pytest
import testing.mysqld


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
def testdata_db_fx(connection_fx):
    """
    Populate the test database with proper test data.
    """
    cursor = connection_fx.cursor()
    cursor.execute("DROP DATABASE IF EXISTS test_members")
    cursor.execute("CREATE DATABASE habdb")
    cursor.execute("USE habdb")
    cursor.execute("CREATE TABLE `members` ( "
                   "`id` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL, "
                   "`displayname` varchar(255) COLLATE utf8mb4_unicode_ci"
                   " DEFAULT NULL, "
                   "`loginname` varchar(255) COLLATE utf8mb4_unicode_ci"
                   " DEFAULT NULL, "
                   "`birthday` date DEFAULT NULL, "
                   "PRIMARY KEY (`id`) "
                   ") DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci")
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
    yield connection_fx


def test_data_init(testdata_db_fx):
    """
    Test that the test data fixture works.
    """
    cursor = testdata_db_fx.cursor()
    cursor.execute("SELECT * FROM members")
    result = cursor.fetchall()
    assert len(result) == 3
