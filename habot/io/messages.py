"""
Handling for communications via Habitica messages.
"""

from datetime import datetime
import requests.exceptions

from habitica_helper.utils import get_dict_from_api, timestamp_to_datetime
from habitica_helper import habrequest

from conf.tasks import PM_SENT, GROUP_MSG_SENT
from habot.io.db import DBOperator
from habot.exceptions import CommunicationFailedException
from habot.habitica_operations import HabiticaOperator
import habot.logger
from habot.message import PrivateMessage, ChatMessage, SystemMessage


class HabiticaMessager():
    """
    A class for handling Habitica messages (private and party).
    """

    def __init__(self, header):
        """
        Initialize the class.

        Database operator is not created at init, because all operations don't
        need one.

        :header: Habitica requires specific fields to be present in all API
                 calls. This must be a dict containing them.
        """
        self._header = header
        self._habitica_operator = HabiticaOperator(header)
        self._logger = habot.logger.get_logger()
        self._db = None

    def _ensure_db(self):
        """
        Make sure that a database operator is available
        """
        if not self._db:
            self._db = DBOperator()

    def _split_long_message(self, message, max_length=3000):
        """
        If the given message is too long, split it into multiple messages.

        If the message is shorter than the given max_length, the returned list
        will just contain the original message. Otherwise the message is split
        into parts, each shorter than the given max_length. Splitting is only
        done at newlines.

        :message: String containing the message body
        :max_length: Maximum length for one message. Default 3000.
        :raises: `UnsplittableMessage` if the message contains a paragraph that
                 is longer than `max_length` and thus cannot be split at a
                 newline.
        :returns: A list of strings, each string containing one piece of the
                  given message.
        """
        # pylint: disable=no-self-use

        if len(message) < max_length:
            return [message]

        split_at = "\n"
        messages = []
        while len(message) > max_length:
            split_index = message.find(split_at)
            if split_index > max_length or split_index == -1:
                raise UnsplittableMessage("Cannot find a legal split "
                                          "location in the following part "
                                          "of an outgoing message:\n"
                                          "{}".format(message))
            while split_index != -1:
                next_split_candidate = message.find(split_at, split_index + 1)
                if (next_split_candidate > max_length
                        or next_split_candidate == -1):
                    break
                split_index = next_split_candidate
            messages.append(message[:split_index])
            message = message[split_index+1:]
        messages.append(message)
        return messages

    def send_private_message(self, to_uid, message):
        """
        Send a private message with the given content to the given user.

        After a message has been successfully sent, the bot ticks its PM
        sending habit.

        :to_uid: Habitica user ID of the recipient
        :message: The contents of the message
        """
        api_url = "https://habitica.com/api/v3/members/send-private-message"
        message_parts = self._split_long_message(message)
        if len(message_parts) > 3:
            raise SpamDetected("Sending {} messages at once is not supported."
                               "".format(len(message_parts)))
        for message_part in message_parts:
            try:
                habrequest.post(api_url, headers=self._header,
                                data={"message": message_part,
                                      "toUserId": to_uid})
            #  pylint: disable=invalid-name
            except requests.exceptions.HTTPError as e:
                #  pylint: disable=raise-missing-from
                raise CommunicationFailedException(str(e))

        self._habitica_operator.tick_task(PM_SENT, task_type="habit")

    def send_group_message(self, group_id, message):
        """
        Send a message with the given content to the given group.

        :group_id: UUID of the recipient group, or 'party' for current party of
                   the bot.
        :message: Contents of the message to be sent
        """
        api_url = "https://habitica.com/api/v3/groups/{}/chat".format(group_id)
        try:
            habrequest.post(api_url, headers=self._header,
                            data={"message": message})
        #  pylint: disable=invalid-name
        except requests.exceptions.HTTPError as e:
            #  pylint: disable=raise-missing-from
            raise CommunicationFailedException(str(e))
        self._habitica_operator.tick_task(GROUP_MSG_SENT, task_type="habit")

    def get_party_messages(self):
        """
        Fetches party messages and stores them into the database.

        Both system messages (e.g. boss damage) and chat messages (sent by
        habiticians) are stored.
        """
        message_data = get_dict_from_api(
            self._header, "https://habitica.com/api/v3/groups/party/chat")
        messages = [None] * len(message_data)
        for i, message_dict in zip(range(len(message_data)), message_data):
            if "user" in message_dict:
                messages[i] = ChatMessage(
                    message_dict["uuid"], message_dict["groupId"],
                    content=message_dict["text"],
                    message_id=message_dict["id"],
                    timestamp=datetime.utcfromtimestamp(
                        # Habitica saves party chat message times as unix time
                        # with three extra digits for milliseconds (no
                        # decimal separator)
                        message_dict["timestamp"]/1000),
                    likers=self._marker_list(message_dict["likes"]),
                    flags=self._marker_list(message_dict["flags"]))
            else:
                messages[i] = SystemMessage(
                    message_dict["groupId"],
                    datetime.utcfromtimestamp(
                        # Habitica saves party chat message times as unix time
                        # with three extra digits for milliseconds (no
                        # decimal separator)
                        message_dict["timestamp"]/1000),
                    content=message_dict["text"],
                    message_id=message_dict["id"],
                    likers=self._marker_list(message_dict["likes"]),
                    info=message_dict["info"]
                    )
        self._logger.debug("Fetched %d messages from Habitica API",
                           len(messages))

        new_messages = 0
        for message in messages:
            if isinstance(message, SystemMessage):
                new = self._write_system_message_to_db(message)
            elif isinstance(message, ChatMessage):
                new = self._write_chat_message_to_db(message)
            else:
                raise ValueError("Unexpected message type received from API")
            new_messages += 1 if new else 0
        self._logger.debug("%d new chat/system messages written to the "
                           "database", new_messages)

    def _write_system_message_to_db(self, system_message):
        """
        Add a system message to the database if not already there.

        In addition to writing the core message data, contents of the `info`
        dict are also written into their own table. All values within this
        dict, including e.g. nested dicts and integers, are coerced to strings.

        System messages can also be liked: these likes are written into `likes`
        table.

        :system_message: SystemMessage to be written to the database
        :returns: True if a new message was added to the database
        """
        self._ensure_db()
        existing_message = self._db.query_table(
            "system_messages",
            condition="id='{}'".format(system_message.message_id))
        if not existing_message:
            for key, value in system_message.info.items():
                info_data = {
                    "message_id": system_message.message_id,
                    "info_key": key,
                    "info_value": str(value),
                    }
                existing_info = self._db.query_table_based_on_dict(
                    "system_message_info", info_data)
                if not existing_info:
                    self._db.insert_data("system_message_info", info_data)
            for liker in system_message.likers:
                self._write_like(system_message.message_id, liker)
            message_data = {
                "id": system_message.message_id,
                "to_group": system_message.group_id,
                "timestamp": system_message.timestamp,
                "content": system_message.content,
                }
            self._db.insert_data("system_messages", message_data)
            return True
        return False

    def _write_chat_message_to_db(self, chat_message):
        """
        Add a chat message to the database if not already there.

        At this point, all chat messages are marked as not requiring a
        reaction.

        :chat_message: ChatMessage to be written to the database
        :returns: True if a new message was added to database, otherwise False
        """
        self._ensure_db()
        existing_message = self._db.query_table(
            "chat_messages",
            condition="id='{}'".format(chat_message.message_id))
        if not existing_message:
            for liker in chat_message.likers:
                self._write_like(chat_message.message_id, liker)
            for flagger in chat_message.flags:
                self._write_like(chat_message.message_id, flagger)
            db_data = {
                "id": chat_message.message_id,
                "from_id": chat_message.from_id,
                "to_group": chat_message.group_id,
                "content": chat_message.content,
                "timestamp": chat_message.timestamp,
                "reaction_pending": 0,
                }
            self._db.insert_data("chat_messages", db_data)
            return True
        return False

    def _marker_list(self, user_dict):
        """
        Return a list of users who have liked/flagged a message.

        This list is parsed from the given user_dict, which has UIDs as keys
        and True/False as the value depending on whether the given user has
        marked that message as liked/flagged. This is the format Habitica
        reports likes for party messages.
        """
        # pylint: disable=no-self-use
        return [uid for uid in user_dict if user_dict[uid]]

    def _write_like(self, message_id, user_id):
        """
        Add information about a person liking a message into the db.

        If the row already exists, it is not inserted again.

        :message_id: The liked message
        :user_id: The person who hit the like button
        """
        self._ensure_db()
        like_dict = {"message": message_id, "user": user_id}
        existing_like = self._db.query_table_based_on_dict("likes", like_dict)
        if not existing_like:
            self._db.insert_data("likes", like_dict)

    def _write_flag(self, message_id, user_id):
        """
        Add information about a person reporting a message into the db.

        If the row already exists, it is not inserted again.

        :message_id: The reported message
        :user_id: The person who reported the message
        """
        self._ensure_db()
        flag_dict = {"message": message_id, "user": user_id}
        existing_flag = self._db.query_table_based_on_dict("flags", flag_dict)
        if not existing_flag:
            self._db.insert_data("flags", flag_dict)

    def get_private_messages(self):
        """
        Fetch private messages using Habitica API.

        If there are new messages, they are written to the database and
        returned.

        No paging is implemented: all new messages are assumed to fit into the
        returned data from the API.
        """
        try:
            message_data = get_dict_from_api(
                self._header, "https://habitica.com/api/v3/inbox/messages")
        except requests.exceptions.HTTPError as err:
            raise CommunicationFailedException(err.response) from err

        messages = [None] * len(message_data)
        for i, message_dict in zip(range(len(message_data)), message_data):
            if message_dict["sent"]:
                recipient = message_dict["uuid"]
                sender = message_dict["ownerId"]
            else:
                recipient = message_dict["ownerId"]
                sender = message_dict["uuid"]
            messages[i] = PrivateMessage(
                sender, recipient,
                timestamp=timestamp_to_datetime(message_dict["timestamp"]),
                content=message_dict["text"],
                message_id=message_dict["id"])
        self._logger.debug("Fetched %d messages from Habitica API",
                           len(messages))
        self.add_PMs_to_db(messages)

    def add_PMs_to_db(self, messages):
        """
        Write all given private messages to the database.

        New messages not sent by this user are marked as
        reaction_pending=True if they have not already been responded to (i.e.
        a newer message sent to the same user is present in the database).
        If none of the given messages are present in the database, returns
        True to signal that fetching more messages might be necessary.
        Otherwise returns False.

        :messages: `PrivateMessage`s to be added to the database
        :returns: True if all of the messages were new (not already in the db),
                  otherwise False
        """
        # pylint: disable=invalid-name
        self._ensure_db()
        all_new = True
        for message in messages:
            existing_message = self._db.query_table(
                "private_messages",
                condition="id='{}'".format(message.message_id))
            if not existing_message:
                self._logger.debug("message.from_id = %s", message.from_id)
                self._logger.debug("id of x-api-user: %s",
                                   self._header["x-api-user"])
                if (message.from_id == self._header["x-api-user"] or
                        self._has_newer_sent_message_in_db(message.from_id,
                                                           message.timestamp)):
                    reaction_pending = 0
                else:
                    reaction_pending = 1
                self._logger.debug("Adding new message to the database: '%s', "
                                   "reaction_pending=%d", message.excerpt(),
                                   reaction_pending)
                db_data = {
                    "id": message.message_id,
                    "from_id": message.from_id,
                    "to_id": message.to_id,
                    "content": message.content,
                    "timestamp": message.timestamp,
                    "reaction_pending": reaction_pending,
                    }
                self._db.insert_data("private_messages", db_data)
            else:
                all_new = False
        return all_new

    @classmethod
    def set_reaction_pending(cls, message, reaction):
        """
        Set reaction_pending field in the DB for a given message.

        :message: A Message for which database is altered
        :reaction: True/False for reaction pending
        """
        db = DBOperator()
        db.update_row("private_messages", message.message_id,
                      {"reaction_pending": reaction})

    def _has_newer_sent_message_in_db(self, to_id, timestamp):
        """
        Return True if `to_id` has been sent a message after `timestamp`.

        This is checked from the database, so if a message has not yet been
        processed into the DB, it won't affect the result. However, if the
        messages are processed from newest to oldest, this function can be used
        to determine if a "new" message has already been responded to.

        :to_id: Habitica user UID
        :timestamp: datetime after which to look for messages
        """
        self._ensure_db()
        sent_messages = self._db.query_table(
            "private_messages",
            condition="timestamp>'{}' AND to_id='{}'".format(timestamp, to_id))
        if sent_messages:
            return True
        return False


class UnsplittableMessage(Exception):
    """
    Exception raised when splitting a too long message is not possible.
    """


class SpamDetected(Exception):
    """
    Exception for situations where the spot is being used for spamming.
    """
