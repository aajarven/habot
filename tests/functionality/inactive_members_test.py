"""
Test functionality related to inactive partymembers
"""

import re

from freezegun import freeze_time
import pytest
import requests_mock

from conf.conf import ADMIN_UID
from habot.functionality.inactive_members import (
    ListInactiveMembers,
    RemoveInactiveMembers,
    )
from habot.message import PrivateMessage
from tests.conftest import SIMPLE_USER


def inactive_members_message():
    """
    Run ListInactiveMembers and return the resulting message
    """
    test_message = PrivateMessage(SIMPLE_USER["id"], "to_id",
                                  content="list-inactive-members")
    lister = ListInactiveMembers()
    return lister.act(test_message)


@freeze_time("2021-01-06")
@pytest.mark.usefixtures("db_connection_fx", "no_db_update")
def test_list_inactive_members_single(purge_and_init_memberdata_fx):
    """
    Test listing inactive members when there's one inactive member
    """
    purge_and_init_memberdata_fx()
    response = inactive_members_message()

    assert response == ("The following party members are inactive:\n"
                        "- @habiticianlogin (last login 2019-06-03)")


@freeze_time("2018-01-01")
@pytest.mark.usefixtures("db_connection_fx", "no_db_update")
def test_list_inactive_members_none(purge_and_init_memberdata_fx):
    """
    Test listing inactive members when there are no inactive members
    """
    purge_and_init_memberdata_fx()
    response = inactive_members_message()

    assert response == "No inactive members found!"


@freeze_time("2022-01-01")
@pytest.mark.usefixtures("db_connection_fx", "no_db_update")
def test_list_inactive_members_many(purge_and_init_memberdata_fx):
    """
    Test listing inactive members when all members are inactive
    """
    purge_and_init_memberdata_fx()
    response = inactive_members_message()

    assert len(response.split("\n")) == 5  # 4 members + header
    assert "- @testuser (last login 2021-01-04)" in response


@freeze_time("2022-01-01")
@pytest.mark.usefixtures("db_connection_fx", "no_db_update")
def test_list_inactive_members_allowlist(purge_and_init_memberdata_fx,
                                         monkeypatch):
    """
    Test listing inactive members when all members are inactive
    """
    monkeypatch.setattr(ListInactiveMembers, "allowed_inactive_members",
                        ["habiticianlogin", "testuser"])

    purge_and_init_memberdata_fx()
    response = inactive_members_message()

    assert len(response.split("\n")) == 3  # 2 members + header
    assert "@habiticianlogin" not in response
    assert "@testuser" not in response


@pytest.fixture
def mock_delete_member():
    """
    Return a pre-defined member data as a response to API call
    """
    removal_urls = re.compile(
            r"https://habitica\.com/api/v3/groups/party/removeMember/.*"
        )
    with requests_mock.Mocker() as mock:
        mock.register_uri(
            "POST",
            removal_urls,
            )
        yield mock


@freeze_time("2021-03-01")
@pytest.mark.usefixtures("db_connection_fx", "no_db_update")
def test_remove_inactive_members_allowlist(purge_and_init_memberdata_fx,
                                           monkeypatch, mock_delete_member):
    """
    Test removing inactive members
    """
    # pylint: disable=redefined-outer-name
    monkeypatch.setattr(ListInactiveMembers, "allowed_inactive_members",
                        ["testuser"])

    purge_and_init_memberdata_fx()

    test_message = PrivateMessage(ADMIN_UID, "to_id",
                                  content="list-inactive-members")
    remover = RemoveInactiveMembers()
    response = remover.act(test_message)

    assert len(response.split("\n")) == 2  # 1 member + header
    assert "@habiticianlogin" in response
    assert "@testuser" not in response

    assert mock_delete_member.call_count == 1
