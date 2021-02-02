"""
Tests for the bot functionalities
"""

from unittest.mock import call

import pytest

from habot.bot import QuestReminders
from habot.message import PrivateMessage


@pytest.mark.usefixtures("db_connection_fx")
def test_send_reminder_called_with_correct_params(mocker):
    """
    Ensure that the message content is parsed correctly by checking how
    _send_reminder gets called
    """
    mock_send = mocker.patch("habot.bot.QuestReminders._send_reminder")
    command = ("quest-reminders\n"
               "```\n"
               "FirstQuest; @thisdoesntmatter\n"
               "Quest1; @user1\n"
               "Quest number 2; @user2\n"
               "Quest 3; @user1, @user2\n"
               "```")
    test_message = PrivateMessage("from_id", "to_id", content=command)

    reminder = QuestReminders()
    reminder.act(test_message)

    expected_calls = [call("Quest1", "@user1", 1, "FirstQuest"),
                      call("Quest number 2", "@user2", 1, "Quest1"),
                      call("Quest 3", "@user1", 2, "Quest number 2"),
                      call("Quest 3", "@user2", 2, "Quest number 2"),
                      ]
    mock_send.assert_has_calls(expected_calls)


@pytest.mark.usefixtures("db_connection_fx")
def test_construct_reminder_single_user():
    """
    Test that the quest reminder for a single person looks as it should.
    """
    # pylint: disable=protected-access
    reminder = QuestReminders()
    message = reminder._message("Quest name", 1, "Previous quest")
    assert message == ("You have a quest coming up in the queue: "
                       "Quest name! It comes after Previous quest, so when "
                       "you notice that Previous quest has ended, please send "
                       "out the invite for Quest name.")


@pytest.mark.usefixtures("db_connection_fx")
def test_construct_reminder_two_users():
    """
    Test that the quest reminder for a single person looks as it should.
    """
    # pylint: disable=protected-access
    reminder = QuestReminders()
    message = reminder._message("Quest name", 2, "Previous quest")
    assert message == ("You (and one other partymember) have a quest coming "
                       "up in the queue: Quest name! It comes after Previous "
                       "quest, so when you notice that Previous quest has "
                       "ended, please send out the invite for Quest name.")


@pytest.mark.usefixtures("db_connection_fx")
def test_construct_reminder_multiple_users():
    """
    Test that the quest reminder for a single person looks as it should.
    """
    # pylint: disable=protected-access
    reminder = QuestReminders()
    message = reminder._message("Quest name", 3, "Previous quest")
    assert message == ("You (and 2 others) have a quest coming up in the "
                       "queue: Quest name! It comes after Previous quest, so "
                       "when you notice that Previous quest has ended, please "
                       "send out the invite for Quest name.")
