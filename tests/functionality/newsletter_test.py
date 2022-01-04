"""
Tests for SendPartyNewsletter functionality
"""

from unittest.mock import call

import pytest

from habot.functionality.newsletter import SendPartyNewsletter
from habot.io.messages import PrivateMessage

from tests.conftest import SIMPLE_USER, ALL_USERS


@pytest.mark.usefixtures("db_connection_fx", "no_db_update",
                         "configure_test_admin")
def test_party_newsletter(mock_send_private_message_fx,
                          purge_and_init_memberdata_fx):
    """
    Test that party newsletters are sent out for all party members and a report
    is given to the requestor.
    """
    purge_and_init_memberdata_fx()
    mock_send = mock_send_private_message_fx

    message = ("This is some content for the newsletter!\n\n"
               "It might contain **more than one paragraph**, wow.")
    command = (f"send-party-newsletter\n \n{message}\n ")
    test_message = PrivateMessage(ALL_USERS[-1]["id"],
                                  "to_id",
                                  content=command)

    newsletter_functionality = SendPartyNewsletter()
    response = newsletter_functionality.act(test_message)

    expected_message = (
                   f"{message}"
                   "\n\n---\n\n"
                   "This is a party newsletter written by "
                   f"@{ALL_USERS[-1]['loginname']} and "
                   "brought you by the party bot. If you suspect you should "
                   "not have received this message, please contact "
                   "@testuser."
                   )

    expected_calls = [call(userdata["id"], expected_message)
                      for userdata in ALL_USERS]
    mock_send.assert_has_calls(expected_calls, any_order=True)

    assert "Sent the given newsletter to the following users:" in response
    for user in ALL_USERS[:-1]:
        assert f"\n- @{user['loginname']}" in response


@pytest.mark.usefixtures("db_connection_fx", "no_db_update",
                         "configure_test_admin")
def test_newsletter_not_sent_to_self(mocker, purge_and_init_memberdata_fx,
                                     mock_send_private_message_fx):
    """
    Test that the bot doesn't send the newsletter to itself.
    """
    purge_and_init_memberdata_fx()

    mock_send = mock_send_private_message_fx
    message = ("This is some content for the newsletter!\n\n"
               "It might contain **more than one paragraph**, wow.")
    command = f"send-party-newsletter\n \n{message} \n "
    test_message = PrivateMessage(ALL_USERS[2]["id"], "to_id", content=command)

    newsletter_functionality = SendPartyNewsletter()

    mocker.patch.dict("conf.header.HEADER",
                      {"x-api-user": SIMPLE_USER["id"]})
    newsletter_functionality.act(test_message)

    recipients = list(ALL_USERS)
    recipients.remove(SIMPLE_USER)

    expected_message = (
                   f"{message}"
                   "\n\n---\n\n"
                   "This is a party newsletter written by "
                   f"@{ALL_USERS[2]['loginname']} and brought you by the "
                   "party bot. If you suspect you should not have received "
                   "this message, please contact @testuser."
                   )

    expected_calls = [call(userdata["id"], expected_message)
                      for userdata in recipients]
    mock_send.assert_has_calls(expected_calls, any_order=True)


@pytest.mark.usefixtures("db_connection_fx", "configure_test_admin")
def test_newsletter_anti_spam(mock_send_private_message_fx,
                              purge_and_init_memberdata_fx):
    """
    Test that requesting a newsletter is only possible from within the party.
    """
    purge_and_init_memberdata_fx()

    mock_send = mock_send_private_message_fx()
    command = "send-party-newsletter some content"
    test_message = PrivateMessage("not_in_party_id", "to_id", content=command)

    newsletter_functionality = SendPartyNewsletter()
    response = newsletter_functionality.act(test_message)

    mock_send.assert_not_called()
    assert "No messages sent." in response
