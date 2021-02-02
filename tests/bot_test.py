"""
Tests for the bot functionalities
"""

from unittest.mock import call

import pytest

from habot.bot import QuestReminders
from habot.message import PrivateMessage

from tests.conftest import SIMPLE_USER


@pytest.fixture
def no_db_update(mocker):
    """
    Prevent DBSyncer.update_partymember_data from doing anything.

    This way the database can be set up with an arbitrary data.
    """
    update = mocker.patch("habot.io.DBSyncer.update_partymember_data")
    yield
    update.assert_called()

@pytest.mark.usefixtures("db_connection_fx", "no_db_update")
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


@pytest.mark.usefixtures("db_connection_fx", "no_db_update")
def test_sending_single_message(mocker, purge_and_init_memberdata_fx):
    """
    Ensure that the correct message is sent out for a single quest.

    The format of the messages is thoroughly tested in when testing the
    _message function, so here the only thing to do is to test that a matching
    message is really sent to the correct recipient.
    """
    purge_and_init_memberdata_fx()
    mock_messager = mocker.patch(
            "habot.io.HabiticaMessager.send_private_message")

    command = ("quest-reminders\n"
               "```\n"
               "FirstQuest; @thisdoesntmatter\n"
               "quest; {}\n"
               "```"
               "".format(SIMPLE_USER["loginname"]))
    expected_message = ("You have a quest coming up in the queue: "
                        "quest! It comes after FirstQuest, so when "
                        "you notice that FirstQuest has ended, please "
                        "send out the invite for quest.")
    test_command_msg = PrivateMessage("from_id", "to_id", content=command)

    reminder = QuestReminders()
    reminder.act(test_command_msg)

    mock_messager.assert_called_with(SIMPLE_USER["id"], expected_message)
