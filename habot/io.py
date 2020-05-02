"""
Communications with non-API external entities.

Currently this means interacting via private messages in Habitica.
"""

import requests

from habot.exceptions import CommunicationFailedException


class HabiticaMessager(object):
    """
    A class for handling Habitica private messages.
    """

    def __init__(self, header):
        """
        Initialize the class.

        :header: Habitica requires specific fields to be present in all API
                 calls. This must be a dict containing them.
        """
        self._header = header

    def send_private_message(self, to_uid, message):
        """
        Send a private message with the given content to the given user.

        :to_uid: Habitica user ID of the recipient
        :message: The contents of the message
        """
        api_url = "https://habitica.com/api/v3/members/send-private-message"
        response = requests.post(api_url, headers=self._header,
                                 data={"message": message, "toUserId": to_uid})
        if response.status_code != 200:
            raise CommunicationFailedException(response)


