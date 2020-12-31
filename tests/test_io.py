"""
Test `habot.io` module.
"""

import pytest
from unittest import mock

from habot.io import HabiticaMessager


@pytest.fixture()
def test_messager(header_fx):
    """
    Create a HabiticaMessager for testing purposes.
    """
    return HabiticaMessager(header_fx)


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
