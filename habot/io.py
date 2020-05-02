"""
Communications with non-API external entities.

Currently this means interacting via private messages in Habitica.
"""

import requests

from conf.tasks import PM_SENT
from habot.exceptions import CommunicationFailedException
from habot.habitica_operations import HabiticaOperator


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
        self._habitica_operator = HabiticaOperator(header)

    def send_private_message(self, to_uid, message):
        """
        Send a private message with the given content to the given user.

        After a message has been successfully sent, the bot ticks its PM
        sending habit.

        :to_uid: Habitica user ID of the recipient
        :message: The contents of the message
        """
        api_url = "https://habitica.com/api/v3/members/send-private-message"
        response = requests.post(api_url, headers=self._header,
                                 data={"message": message, "toUserId": to_uid})
        if response.status_code != 200:
            raise CommunicationFailedException(response)

        self._habitica_operator.tick_task(PM_SENT, task_type="habit")
