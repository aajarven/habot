"""
Functionality for sending birthday reminders
"""

from habot.birthdays import BirthdayReminder
from habot.functionality.base import Functionality

from conf.header import HEADER


class ListBirthdays(Functionality):
    """
    Respond with a list of Habitica birthdays.
    """

    def act(self, message):
        """
        Return a response with todays birthdays.
        """
        bday_reminder = BirthdayReminder(HEADER)
        return bday_reminder.birthday_reminder_message()

    def help(self):
        """
        Return a help message.
        """
        # pylint: disable=no-self-use
        return "List party members who are celebrating their birthday today."
