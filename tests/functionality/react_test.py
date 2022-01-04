"""
Test reacting to private messages
"""

from unittest.mock import call

import pytest

from habot.functionality.react import handle_PMs
from habot.message import PrivateMessage


@pytest.fixture
def mock_messages_awaiting_reaction_fx(mocker):
    """
    A factory that returns a function for mocking `messages_awaiting_reaction`

    After the test using this fixture has been run, it is ensured that the
    mocking was done exactly once and that the mocked function was called
    exactly once.
    """
    mocked_functions = []

    def _mock(returned_messages):
        """
        Mocks `habot.message.PrivateMessage.messages_awaiting_reaction`.

        :returned_messages: A list of `PrivateMessage`s that the mocked
                            `messaged_awaiting_reaction` should return.
        """
        mocked_function = mocker.patch(
                "habot.message.PrivateMessage.messages_awaiting_reaction")
        mocked_function.return_value = returned_messages
        mocked_functions.append(mocked_function)
        return mocked_function

    yield _mock

    assert len(mocked_functions) == 1
    mocked_functions[0].assert_called_once()


@pytest.fixture
def mock_set_reaction_pending_fx(mocker):
    """
    Mock `set_reaction_pending` method so that database is not actually used.
    """
    # pylint: disable=invalid-name
    p = mocker.patch("habot.io.messages.HabiticaMessager.set_reaction_pending")
    return p


# Pylint doesn't handle fixtures well
# pylint: disable=redefined-outer-name


@pytest.mark.usefixtures("mock_set_reaction_pending_fx")
def test_handle_single_PM(  # pylint: disable=invalid-name
        mock_messages_awaiting_reaction_fx,
        mock_send_private_message_fx):
    """
    Test running `handle_PMs` with a single message awaiting reaction.

    Ensure that the correct response is "sent" using a mocked function.
    """
    pm_mock = mock_send_private_message_fx
    message = PrivateMessage("from_id", "to_id", content="ping")
    mock_messages_awaiting_reaction_fx([message])

    handle_PMs()

    pm_mock.assert_has_calls([call("from_id", "Pong")])
