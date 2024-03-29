"""
Test SendQuestReminders functionality
"""

from unittest.mock import call

import pytest

from habot.functionality.quests import SendQuestReminders
from habot.message import PrivateMessage

from tests.conftest import SIMPLE_USER


@pytest.mark.usefixtures("db_connection_fx", "no_db_update")
def test_send_reminder_called_with_correct_params(
        mocker, purge_and_init_memberdata_fx):
    """
    Ensure that the message content is parsed correctly by checking how
    _send_reminder gets called
    """
    purge_and_init_memberdata_fx()

    # these users are the ones added in database init
    user1 = "@testuser"
    user2 = "@somedude"

    mock_send = mocker.patch("habot.functionality.quests."
                             "SendQuestReminders._send_reminder")
    command = ("quest-reminders\n"
               "```\n"
               "FirstQuest; @thisdoesntmatter\n"
               f"Quest1; {user1}\n"
               f"Quest number 2; {user2}\n"
               f"Quest 3; {user1}, {user2}\n"
               "```")
    test_message = PrivateMessage("from_id", "to_id", content=command)

    reminder = SendQuestReminders()
    reminder.act(test_message)

    expected_calls = [call("Quest1", "testuser", 1, "FirstQuest"),
                      call("Quest number 2", "somedude", 1, "Quest1"),
                      call("Quest 3", "testuser", 2, "Quest number 2"),
                      call("Quest 3", "somedude", 2, "Quest number 2"),
                      ]
    mock_send.assert_has_calls(expected_calls)


@pytest.mark.usefixtures("db_connection_fx")
def test_construct_reminder_single_user():
    """
    Test that the quest reminder for a single person looks as it should.
    """
    # pylint: disable=protected-access
    reminder = SendQuestReminders()
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
    reminder = SendQuestReminders()
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
    reminder = SendQuestReminders()
    message = reminder._message("Quest name", 3, "Previous quest")
    assert message == ("You (and 2 others) have a quest coming up in the "
                       "queue: Quest name! It comes after Previous quest, so "
                       "when you notice that Previous quest has ended, please "
                       "send out the invite for Quest name.")


@pytest.mark.usefixtures("db_connection_fx", "no_db_update")
def test_sending_single_message(purge_and_init_memberdata_fx,
                                mock_send_private_message_fx):
    """
    Ensure that the correct message is sent out for a single quest.

    The format of the messages is thoroughly tested in when testing the
    _message function, so here the only thing to do is to test that a matching
    message is really sent to the correct recipient.
    """
    purge_and_init_memberdata_fx()
    mock_messager = mock_send_private_message_fx

    command = ("quest-reminders\n"
               "```\n"
               "FirstQuest; @thisdoesntmatter\n"
               f"quest; {SIMPLE_USER['loginname']}\n"
               "```")
    expected_message = ("You have a quest coming up in the queue: "
                        "quest! It comes after FirstQuest, so when "
                        "you notice that FirstQuest has ended, please "
                        "send out the invite for quest.")
    test_command_msg = PrivateMessage("from_id", "to_id", content=command)

    reminder = SendQuestReminders()
    reminder.act(test_command_msg)

    mock_messager.assert_called_with(SIMPLE_USER["id"], expected_message)


@pytest.mark.usefixtures("no_db_update")
@pytest.mark.parametrize(
        ["quests", "expected_message_part"],
        [
            (["q1;@anyuser", "q2;"],
             "No quest owners listed"),
            (["q1;@anyuser", "q2 @testuser"],
             "Each line in the quest queue must be divided into two parts"),
            (["q1;@anyuser", "   ;@testuser"],
             "quest name cannot be empty"),
            (["q1;@anyuser", "q2; @testuser, ,@testuser"],
             "Malformed quest owner list"),
            (["q1;@anyuser", "q2; @noSuchUser"],
             "User @noSuchUser not found in the party"),
        ]
)
def test_faulty_quest_queue(quests, expected_message_part,
                            purge_and_init_memberdata_fx,
                            mock_send_private_message_fx):
    """
    Test that no messages are sent when given quest queue is faulty.

    The user @testuser found in the test data is inserted into the database
    during test database initialization. Note that the owner of the first
    quest doesn't have to be in the database: that information is not used by
    the bot.
    """
    purge_and_init_memberdata_fx()
    mock_messager = mock_send_private_message_fx

    quest_list_str = "\n".join(quests)
    command = ("quest-reminders\n"
               "```\n"
               f"{quest_list_str}\n"
               "```")
    test_command_msg = PrivateMessage("from_id", "to_id", content=command)

    reminder = SendQuestReminders()

    response = reminder.act(test_command_msg)
    assert expected_message_part in response

    mock_messager.assert_not_called()


@pytest.mark.usefixtures("no_db_update")
def test_quest_queue_outside_code(mock_send_private_message_fx):
    """
    Test that a well-formed quest queue is not accepted if outside a code block
    """
    mock_messager = mock_send_private_message_fx

    command = ("quest-reminders\n"
               "q1;@user1\n"
               "q2;@user2\n"
               )
    test_command_msg = PrivateMessage("from_id", "to_id", content=command)

    reminder = SendQuestReminders()

    response = reminder.act(test_command_msg)
    assert "code block was not found" in response

    mock_messager.assert_not_called()


@pytest.mark.usefixtures("db_connection_fx", "no_db_update")
def test_complex_quest_reminder(mocker,
                                purge_and_init_memberdata_fx):
    """
    Test that difficult but legal quest queue is parsed correctly.
    """
    purge_and_init_memberdata_fx()

    # these users are the ones added in database init
    user1 = "testuser"
    user2 = "somedude"

    mock_send = mocker.patch("habot.functionality.quests."
                             "SendQuestReminders._send_reminder")
    command = ("quest-reminders\n\n"
               "there's some weird content here\n"
               "but it shouldn't matter\n\n"
               "```\n"
               "FirstQuest;\n"
               f"Quest1; @{user1}\n"
               "\n"
               f"    Quest number 2 ; {user2}\n"
               f"  Quest 3;{user1},{user2}\n"
               f"Quest 3;{user1}    ,    {user2}\n"
               "```")
    test_message = PrivateMessage("from_id", "to_id", content=command)

    reminder = SendQuestReminders()
    reminder.act(test_message)

    expected_calls = [call("Quest1", "testuser", 1, "FirstQuest"),
                      call("Quest number 2", "somedude", 1, "Quest1"),
                      call("Quest 3", "testuser", 2, "Quest number 2"),
                      call("Quest 3", "somedude", 2, "Quest number 2"),
                      ]
    mock_send.assert_has_calls(expected_calls)
