"""
Test IO via Habitica private messages
"""

from unittest import mock
import pytest

from habot.io.messages import CommunicationFailedException


# pylint: disable=redefined-outer-name


@pytest.mark.usefixtures("mock_task_ticking")
def test_send_pm(requests_mock, test_messager):
    """
    Test that a request corresponding to the given UID and message is made.
    """
    requests_mock.post(
        "https://habitica.com/api/v3/members/send-private-message")

    test_messager.send_private_message("test_uid", "test_message")

    # one request for sending the message, two for ticking the habit
    assert len(requests_mock.request_history) == 3

    response_data = requests_mock.request_history[0].text
    assert "message=test_message" in response_data
    assert "toUserId=test_uid" in response_data


@pytest.mark.usefixtures("mock_task_ticking")
def test_pm_failure_exception(requests_mock, test_messager):
    """
    Test that a CommunicationFailedException is raised when sending fails
    """
    requests_mock.post(
        "https://habitica.com/api/v3/members/send-private-message",
        status_code=500)
    with pytest.raises(CommunicationFailedException):
        test_messager.send_private_message("test_uid", "test_message")


@mock.patch("habitica_helper.habrequest.post")
@mock.patch("habot.habitica_operations.HabiticaOperator.tick_task")
def test_group_message(mock_tick, mock_post, test_messager, header_fx):
    """
    Test group message sending.

    Ensure that a correct API call is made to send a group message with the
    message in its payload, and that a task is ticked afterwards.
    """
    test_messager.send_group_message("group-id", "some message")
    mock_post.assert_called_with(
            "https://habitica.com/api/v3/groups/group-id/chat",
            headers=header_fx,
            data={"message": "some message"})
    mock_tick.assert_called()
