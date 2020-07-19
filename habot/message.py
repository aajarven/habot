"""
Representations for Habitica messages.
"""

from habot.db import DBOperator

class Message():
    """
    Base message: e.g. private messages and party chat messages are these.
    """

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
        self.to_id = to_id
        super(PrivateMessage, self).__init__(from_id, timestamp, content,
                                             message_id)

    def __str__(self):
        return ("from: {}\n"
                "to: {}\n"
                "{} ({})\n\n"
                "{}".format(self.from_id, self.to_id, self.timestamp,
                            self.message_id, self.content))

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
