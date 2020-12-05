"""
Functionality for sending Habitica birthday reminders
"""

import datetime

from habot.db import DBOperator
from habot.io import HabiticaMessager, DBSyncer


class BirthdayReminder():
    """
    A class for creating and sending Habitica Birthday reminders.
    """

    def __init__(self, header):
        """
        Create a new BirthdayHandler.

        :header: Habitica API header for the habitician who is to send the
                 birthday reminders based on the member database.
        """
        self._header = header

    @classmethod
    def birthdays_today(cls):
        """
        Return a list of partymembers who have their Habitica birthday today.

        The result is based on the "members" table in the database.
        """
        db = DBOperator()
        members = db.query_table("members")

        today = datetime.date.today()

        revellers = [member for member in members
                     if (member["birthday"].month == today.month and
                         member["birthday"].day == today.day)]
        return revellers

    def send_birthday_reminder(self, recipient_uid, sync=True):
        """
        Send a message telling whether any party member is having a birthday.

        :recipient_uid: The UID of the Habitician to whom the PM is sent
        :sync: True if database should be synced before sending message
        """
        if sync:
            db_syncer = DBSyncer(self._header)
            db_syncer.update_partymember_data()
        message = self.birthday_reminder_message()
        messager = HabiticaMessager(self._header)
        messager.send_private_message(recipient_uid, message)

    def birthday_reminder_message(self):
        """
        Return a string representing today's birthday reminder
        """
        revellers = self.birthdays_today()
        if not revellers:
            message = ("Nobody from the party is celebrating their Habitica "
                       "birthday today.")
        else:
            reveller_names = [reveller["displayname"] for reveller in
                              revellers]
            reveller_str = "- " + "\n- ".join(reveller_names)
            message = ("The following habiticians are celebrating their "
                       "Habitica birthdays today:\n"
                       "{}\n\nHappy birthday!".format(reveller_str))
        return message
