"""
Automatically run scheduled tasks.
"""

import time

import schedule

from conf.header import HEADER
from habot.birthdays import BirthdayReminder
from habot.bot import handle_PMs
from habot.io import HabiticaMessager


def bday():
    """
    Send birthday reminder to Antonbury
    """
    bday_reminder = BirthdayReminder(HEADER)
    bday_reminder.send_birthday_reminder(
        "f687a6c7-860a-4c7c-8a07-9d0dcbb7c831")


if __name__ == "__main__":
    messager = HabiticaMessager(HEADER)
#    schedule.every(10).seconds.do(messager.get_party_messages)
    schedule.every(10).seconds.do(messager.get_private_messages)
    schedule.every(10).seconds.do(handle_PMs)

    schedule.every().day.at("00:01").do(bday)

    while True:
        schedule.run_pending()
        time.sleep(1)
