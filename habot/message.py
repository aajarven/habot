"""
Representations for Habitica messages.
"""

from habot.io.db import DBOperator


class Message():
    """
    Base message: e.g. private messages and party chat messages are these.
    """
    # pylint: disable=too-few-public-methods

    def __init__(self, from_id, timestamp=None, content="", message_id=None):
        """
        Create a new message

        :from_id: Habitica UID of the person who sen the message
        :timestamp: Datetime representing the send time of the message
        :content: Message text
        :message_id: Identifier for the message in Habitica API
        """
        self.from_id = from_id
        self.timestamp = timestamp
        self.content = content
        self.message_id = message_id

    def excerpt(self, max_chars=80, continuation_signal="..."):
        """
        Return the content of the message, truncated to fit to max_chars.

        If the message does not fit to max_chars, it is truncated so that the
        truncated message and appended continuation_signal are exactly
        max_chars long, and the resulting string is returned.
        """
        if len(self.content) <= 80:
            return self.content
        return (self.content[:max_chars-len(continuation_signal)] +
                continuation_signal)


class PrivateMessage(Message):
    """
    Representation of a Habitica private message.
    """

    def __init__(self, from_id, to_id, timestamp=None, content="",
                 message_id=None):
        """
        Create a new message

        :from_id: Habitica UID of the person who sen the message
        :timestamp: Datetime representing the send time of the message
        :content: Message text
        :message_id: Identifier for the message in Habitica API
        """
        # pylint: disable=too-many-arguments
        self.to_id = to_id
        super().__init__(from_id, timestamp, content,
                         message_id)

    def __str__(self):
        return (f"from: {self.from_id}\n"
                f"to: {self.to_id}\n"
                f"{self.timestamp} ({self.message_id})\n\n"
                f"{self.content}")

    @classmethod
    def messages_awaiting_reaction(cls):
        """
        Return a list of Messages which are marked as reaction pending.
        """
        db = DBOperator()
        message_data = db.query_table("private_messages",
                                      condition="reaction_pending=True")
        return [PrivateMessage(m["from_id"], m["to_id"],
                               timestamp=m["timestamp"],
                               content=m["content"], message_id=m["id"])
                for m in message_data]


class ChatMessage(Message):
    """
    A representation for messages sent to a group chat.
    """

    def __init__(self, from_id, group_id, timestamp, content="",
                 message_id=None, likers=None, flags=None):
        """
        Create a new message

        :from_id: Habitica UID of the person who sen the message
        :group_id: Group ID for the destination group
        :timestamp: Datetime representing the send time of the message
        :content: Message text
        :message_id: Identifier for the message in Habitica API
        :likers: UIDs of people who have liked a message
        :flags: UIDs of people who have reported the message
        """
        # pylint: disable=too-many-arguments
        self.group_id = group_id
        self.likers = likers if likers else []
        self.flags = flags if flags else []
        super().__init__(from_id, timestamp, content, message_id)

    def __str__(self):
        return (f"from: {self.from_id}\n"
                f"{self.timestamp} ({self.message_id})\n"
                f"likes: {len(self.likers)}\n\n"
                f"{self.content}")


class SystemMessage(Message):
    """
    A representation for system messages sent to a group chat.
    """

    def __init__(self, group_id, timestamp, content="",
                 message_id=None, likers=None, info=None):
        """
        Create a new message

        :group_id: Group ID for the destination group
        :timestamp: Datetime representing the send time of the message
        :content: Message text
        :message_id: Identifier for the message in Habitica API
        :likers: UIDs of people who have liked a message
        :info: Dictionary representing the information content machine-readably
        """
        # pylint: disable=too-many-arguments
        self.group_id = group_id
        self.likers = likers if likers else []
        self.info = info
        super().__init__(None, timestamp, content, message_id)

    def __str__(self):
        return (f"{self.timestamp} System message:\n\n"
                f"{self.content}")
