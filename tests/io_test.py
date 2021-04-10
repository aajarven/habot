"""
Test `habot.io` module.
"""

import datetime
from unittest import mock

import pytest

from habitica_helper.habiticatool import PartyTool
from habitica_helper.member import Member

from habot.db import DBOperator
from habot.io import HabiticaMessager, DBSyncer, DBTool


@pytest.fixture()
def test_messager(header_fx):
    """
    Create a HabiticaMessager for testing purposes.
    """
    return HabiticaMessager(header_fx)


# pylint doesn't understand fixtures
# pylint: disable=redefined-outer-name

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
    # on some machines, @mark.usefixtures wasn't sufficient to prevent errors
    # pylint: disable=unused-argument
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
        # pylint: disable=unused-argument
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
    "ownerId": "own-uuid",
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
    "id": "inbox-unique-id",
    "text": "Hi, I got something to say to you",
    "unformattedText": "Hi, I got something to say to you",
    "timestamp": "2020-12-31T16:56:49.258Z",
    "uuid": "sender-uuid",
    "user": "OtherPerson",
    "username": "Other Person",
}

RESPONSE_PM = {
    "sent": True,
    "_id": "third-unique-id",
    "ownerId": "own-uuid",
    "uuid": "own-uuid",
    "id": "response-unique-id",
    "text": "Got it!",
    "unformattedText": "Got it!",
    "timestamp": "2020-12-31T16:57:19.278Z",
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
    cursor.execute("DELETE FROM private_messages")
    db_connection_fx.commit()
    cursor.close()


@pytest.mark.usefixtures("purge_message_data")
def test_get_single_sent_pm(test_messager, db_operator_fx,
                            patch_get_dict_response):
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


@pytest.mark.usefixtures("purge_message_data")
def test_get_single_received_pm(test_messager, db_operator_fx,
                                patch_get_dict_response):
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


@pytest.mark.usefixtures("purge_message_data")
def test_get_multiple_pms(test_messager, db_operator_fx,
                          patch_get_dict_response):
    """
    Test that the correct number of PMs are found in the db after fetching.
    """
    patch_get_dict_response([SENT_PM_1, RECEIVED_PM, SENT_PM_2])
    test_messager.get_private_messages()
    private_messages = db_operator_fx.query_table("private_messages")
    assert len(private_messages) == 3


@pytest.mark.usefixtures("purge_message_data")
def test_get_already_answered_pm(test_messager, db_operator_fx,
                                 patch_get_dict_response, monkeypatch):
    """
    Test that when a message has been replied to, response isn't pending
    """
    # pylint: disable=protected-access
    monkeypatch.setitem(test_messager._header, "x-api-user",
                        RESPONSE_PM["ownerId"])
    patch_get_dict_response([RECEIVED_PM, RESPONSE_PM])
    test_messager.get_private_messages()
    private_messages = db_operator_fx.query_table("private_messages")
    assert len(private_messages) == 2
    for message in private_messages:
        if message["id"] == "inbox-unique-id":
            assert message["reaction_pending"]
        elif message["id"] == "response-unique-id":
            assert not message["reaction_pending"]
        else:
            assert False, "Unexpected message found in database"


@pytest.fixture
def test_syncer(header_fx):
    """
    Return a DBSyncer using a test header.
    """
    return DBSyncer(header_fx)


@pytest.fixture
def patch_partytool_members(monkeypatch):
    """
    Allow returning an arbitrary list of members "from the API".
    """
    def _patch(members):
        # pylint: disable=unused-argument
        def _static_members(*args, **kwargs):
            return members
        monkeypatch.setattr(PartyTool, "party_members", _static_members)
    return _patch


MEMBER_ALREADY_IN_DB_1 = Member(
        "member-already-in-db-1-id",
        profile_data={"id": "member-already-in-db-1-id",
                      "displayname": "member 1",
                      "loginname": "member1",
                      "birthday": datetime.date(2020, 1, 15),
                      })
MEMBER_ALREADY_IN_DB_2 = Member(
        "member-already-in-db-2-id",
        profile_data={"id": "member-already-in-db-2-id",
                      "displayname": "member 2",
                      "loginname": "member2",
                      "birthday": datetime.date(2019, 6, 30),
                      })
NEW_MEMBER = Member(
        "new-member-id",
        profile_data={"id": "new-member-id",
                      "displayname": "New member =3",
                      "loginname": "newmember",
                      "birthday": datetime.date(2020, 12, 13),
                      })


@pytest.fixture
def purge_and_set_memberdata_fx(db_connection_fx, db_operator_fx):
    """
    Remove all pre-existing member table rows and insert new test data.

    This data contains two pretty ordinary partymembers.
    """
    cursor = db_connection_fx.cursor()
    cursor.execute("DELETE FROM members")
    db_connection_fx.commit()

    for member in [MEMBER_ALREADY_IN_DB_1, MEMBER_ALREADY_IN_DB_2]:
        data = {
            "id": member.id,
            "displayname": member.displayname,
            "loginname": member.login_name,
            "birthday": member.habitica_birthday,
            }
        db_operator_fx.insert_data("members", data)


@pytest.mark.usefixtures("purge_and_set_memberdata_fx")
def test_update_new_partymembers(test_syncer, db_operator_fx,
                                 patch_partytool_members):
    """
    Ensure that a new record is added to the member table when members join.
    """
    patch_partytool_members([MEMBER_ALREADY_IN_DB_1,
                             MEMBER_ALREADY_IN_DB_2,
                             NEW_MEMBER])
    test_syncer.update_partymember_data()
    members = db_operator_fx.query_table("members")
    assert len(members) == 3


@pytest.mark.usefixtures("purge_and_set_memberdata_fx")
def test_remove_old_partymembers(test_syncer, db_operator_fx,
                                 patch_partytool_members):
    """
    Ensure that a row is removed from the member table when member leaves party
    """
    patch_partytool_members([MEMBER_ALREADY_IN_DB_1])
    test_syncer.update_partymember_data()
    members = db_operator_fx.query_table("members")
    assert len(members) == 1


@pytest.fixture
def db_tool_fx(db_connection_fx):
    """
    Yield an operator for a test database.
    """
    # on some machines, @mark.usefixtures wasn't sufficient to prevent errors
    # pylint: disable=unused-argument
    yield DBTool()


@pytest.mark.usefixtures("purge_and_set_memberdata_fx")
def test_get_user_id(db_tool_fx):
    """
    Test that user ID can be fetched from the database based on login name
    """
    assert db_tool_fx.get_user_id("member1") == "member-already-in-db-1-id"


@pytest.mark.usefixtures("purge_and_set_memberdata_fx")
def test_get_non_existent_user_id(db_tool_fx):
    """
    Test that an exception is raised when a matching user is not found.
    """
    with pytest.raises(ValueError) as err:
        db_tool_fx.get_user_id("nonexistent-member")
    assert ("User with login name nonexistent-member not found"
            in str(err.value))


@pytest.mark.usefixtures("purge_and_set_memberdata_fx")
def test_get_party_user_ids(db_tool_fx):
    """
    Test that all user IDs for all party members are returned.
    """
    ids = db_tool_fx.get_party_user_ids()
    assert len(ids) == 2
    assert set(ids) == set(["member-already-in-db-1-id",
                            "member-already-in-db-2-id"])


@pytest.mark.usefixtures("purge_and_set_memberdata_fx")
def test_get_login_name(db_tool_fx):
    """
    Test that user ID can be fetched from the database based on login name
    """
    assert db_tool_fx.get_loginname("member-already-in-db-1-id") == "member1"


@pytest.mark.usefixtures("purge_and_set_memberdata_fx")
def test_get_non_existent_login_name(db_tool_fx):
    """
    Test that an exception is raised when a matching user is not found.
    """
    with pytest.raises(ValueError) as err:
        db_tool_fx.get_loginname("nonexistent-member-uid")
    assert ("User with user ID nonexistent-member-uid not found"
            in str(err.value))
