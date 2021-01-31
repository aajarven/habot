"""
Tests for the bot functionalities
"""

from unittest.mock import call

from habot.bot import QuestReminders
from habot.message import PrivateMessage


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
