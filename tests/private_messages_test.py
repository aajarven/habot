"""
Test IO via Habitica private messages
"""

import pytest

from habot.io import HabiticaMessager, CommunicationFailedException


@pytest.fixture()
def test_messager(header_fx):
    """
    Create a HabiticaMessager for tests.
    """
    return HabiticaMessager(header_fx)


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
