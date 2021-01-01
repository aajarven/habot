"""
Test `habot.io` module.
"""

import datetime
import pytest
from unittest import mock

from habot.db import DBOperator
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


@pytest.fixture
def db_operator_fx(db_connection_fx):
    """
    Yield an operator for a test database.
    """
    yield DBOperator()


PARTY_CHAT_MSG_1 = {
        "flagCount": 0,
        "_id": "unique-message-id",
        "id": "unique-message-id",
        "user": "MessageSenderDisplayname",
        "username": "MessageSender Displayname",
        "uuid": "MessageSenderUserID",
        "groupId": "group-id",
        "text": "Some test message",
        "timestamp": 1609490392299,
        "likes": {},
        "flags": {},
}

PARTY_CHAT_MSG_2 = {
        "flagCount": 0,
        "_id": "different-id",
        "id": "different-id",
        "user": "AnotherSender",
        "username": "Another Sender",
        "uuid": "AnotherMessageSenderUserID",
        "groupId": "group-id",
        "text": ("I have a lot to say, all kinds of important stuff.\n\n"
                 "Many rows!"),
        "timestamp": 1609480474296,
        "likes": {"MessageSenderUserID": True},
        "flags": {},
}

SYSTEM_MESSAGE = {
    "flagCount": 0,
    "_id": "unique-system-message-id",
    "flags": {},
    "id": "unique-system-message-id",
    "text": "`Some Guy casts Earthquake for the party.`",
    "unformattedText": "Some Guy casts Earthquake for the party.",
    "info": {"type": "spell_cast_party",
             "user": "SomeGuy",
             "class": "wizard",
             "spell": "earth"},
    "timestamp": 1609486163423,
    "likes": {},
    "uuid": "system",
    "groupId": "group-id"
    }


@pytest.fixture
def patch_get_dict_response(monkeypatch):
    """
    Allow monkeypatching `get_dict_from_api` to return arbitrary data.
    """
    def _patch(messages):
        def _return_messages(*args, **kwargs):
            return messages
        monkeypatch.setattr("habot.io.get_dict_from_api",
                            _return_messages)
    return _patch


def test_get_party_messages(test_messager, db_operator_fx,
                            patch_get_dict_response):
    """
    Test that correct data is written to the database for messages.

    A single chat and system messages are tested.
    """
    patch_get_dict_response([PARTY_CHAT_MSG_1, SYSTEM_MESSAGE])
    test_messager.get_party_messages()
    chat_messages = db_operator_fx.query_table("chat_messages")
    system_messages = db_operator_fx.query_table("system_messages")
    assert len(chat_messages) == 1
    assert len(system_messages) == 1

    expected_chat_message = {
        "id": PARTY_CHAT_MSG_1["id"],
        "from_id": PARTY_CHAT_MSG_1["uuid"],
        "to_group": PARTY_CHAT_MSG_1["groupId"],
        "timestamp": datetime.datetime(2021, 1, 1, 8, 39, 52),
        "content": PARTY_CHAT_MSG_1["text"],
        }
    for key in expected_chat_message:
        assert chat_messages[0][key] == expected_chat_message[key]

    expected_system_message = {
        "id": SYSTEM_MESSAGE["id"],
        "to_group": SYSTEM_MESSAGE["groupId"],
        "timestamp": datetime.datetime(2021, 1, 1, 7, 29, 23),
        "content": SYSTEM_MESSAGE["text"],
        }
    for key in expected_system_message:
        assert system_messages[0][key] == expected_system_message[key]


def test_fetch_two_chat_messages(test_messager, db_operator_fx,
                                 patch_get_dict_response):
    """
    Ensure that when new two messages are read, two messages end up in the db.
    """
    patch_get_dict_response([PARTY_CHAT_MSG_1, PARTY_CHAT_MSG_2])
    test_messager.get_party_messages()
    assert len(db_operator_fx.query_table("chat_messages")) == 2


def test_old_messages(test_messager, db_operator_fx, patch_get_dict_response):
    """
    Read the same messages twice and make sure db only has one copy of each.
    """
    patch_get_dict_response([PARTY_CHAT_MSG_1, PARTY_CHAT_MSG_2,
                             SYSTEM_MESSAGE])
    test_messager.get_party_messages()
    test_messager.get_party_messages()
    assert len(db_operator_fx.query_table("chat_messages")) == 2
    assert len(db_operator_fx.query_table("system_messages")) == 1


SENT_PM_1 = {
    "sent": True,
    "_id": "unique-pm-id",
    "ownerId": "sender-uuid",
    "uuid": "own-uuid",
    "id": "unique-pm-id",
    "text": "Some private information.",
    "unformattedText": "Some private information.",
    "timestamp": "2020-12-31T22:01:07.979Z",
    "user": "OtherPerson",
    "username": "Other Person",
}

SENT_PM_2 = {
    "sent": True,
    "_id": "another-unique-id",
    "ownerId": "sender-uuid",
    "uuid": "own-uuid",
    "id": "another-unique-id",
    "text": "Whispers.",
    "unformattedText": "Whispers.",
    "timestamp": "2020-12-31T16:57:19.278Z",
    "user": "SomeGuy",
    "username": "Some Third Guy",
}


RECEIVED_PM = {
    "sent": False,
    "_id": "third-unique-id",
    "ownerId": "own-uuid",
    "id": "third-unique-id",
    "text": "Hi, I got something to say to you",
    "unformattedText": "Hi, I got something to say to you",
    "timestamp": "2020-12-31T16:56:49.258Z",
    "uuid": "sender-uuid",
    "user": "OtherPerson",
    "username": "Other Person",
}


@pytest.fixture
def purge_message_data(db_connection_fx):
    """
    Remove all data in private messages after test run
    """
    yield
    cursor = db_connection_fx.cursor()
    cursor.execute("USE habdb")
    cursor.execute("DROP TABLE private_messages")
    db_connection_fx.commit()
    cursor.close()


def test_get_single_sent_pm(test_messager, db_operator_fx,
                            patch_get_dict_response, purge_message_data):
    """
    Ensure that data for a single sent PM is written correctly to the db.
    """
    patch_get_dict_response([SENT_PM_1])
    test_messager.get_private_messages()
    private_messages = db_operator_fx.query_table("private_messages")
    assert len(private_messages) == 1

    expected_pm = {
        "id": SENT_PM_1["id"],
        "from_id": SENT_PM_1["ownerId"],
        "to_id": SENT_PM_1["uuid"],
        "timestamp": datetime.datetime(2020, 12, 31, 22, 1, 8),
        "content": SENT_PM_1["text"],
        }
    for key in expected_pm:
        assert private_messages[0][key] == expected_pm[key]


def test_get_single_received_pm(test_messager, db_operator_fx,
                                patch_get_dict_response, purge_message_data):
    """
    Ensure that data for a single sent PM is written correctly to the db.
    """
    patch_get_dict_response([RECEIVED_PM])
    test_messager.get_private_messages()
    private_messages = db_operator_fx.query_table("private_messages")
    assert len(private_messages) == 1

    expected_pm = {
        "id": RECEIVED_PM["id"],
        "from_id": RECEIVED_PM["uuid"],
        "to_id": RECEIVED_PM["ownerId"],
        "timestamp": datetime.datetime(2020, 12, 31, 16, 56, 49),
        "content": RECEIVED_PM["text"],
        }
    for key in expected_pm:
        assert private_messages[0][key] == expected_pm[key]


def test_get_multiple_pms(test_messager, db_operator_fx,
                          patch_get_dict_response, purge_message_data):
    """
    Test that the correct number of PMs are found in the db after fetching.
    """
    patch_get_dict_response([SENT_PM_1, RECEIVED_PM, SENT_PM_2])
    test_messager.get_private_messages()
    private_messages = db_operator_fx.query_table("private_messages")
    assert len(private_messages) == 3
