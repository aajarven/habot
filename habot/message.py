"""
Representations for Habitica messages.
"""

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
