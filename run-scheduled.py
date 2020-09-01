"""
Automatically run scheduled tasks.
"""

import time

import schedule

from conf.header import HEADER
from habot.birthdays import BirthdayReminder
from habot.bot import handle_PMs, SendWinnerMessage
from habot.io import HabiticaMessager
from habot.habitica_operations import HabiticaOperator


ANTONBURY_UID = "f687a6c7-860a-4c7c-8a07-9d0dcbb7c831"


def bday():
    """
    Send birthday reminder to Antonbury
    """
    bday_reminder = BirthdayReminder(HEADER)
    bday_reminder.send_birthday_reminder(ANTONBURY_UID)


def sharing_winner():
    """
    Send a message announcing the sharing weekend winner.
    """
    winner_message_creator = SendWinnerMessage()
    HabiticaMessager(HEADER).send_private_message(
        ANTONBURY_UID,
        winner_message_creator.act("send scheduled sharing weekend winner msg")
        )


def join_quest():
    """
    Join challenge if there is one to be joined.
    """
    operator = HabiticaOperator(HEADER)
    operator.join_quest()


if __name__ == "__main__":
    messager = HabiticaMessager(HEADER)
    schedule.every(10).minutes.do(messager.get_private_messages)
    schedule.every(10).minutes.do(handle_PMs)
    schedule.every(4).hours.do(join_quest)

    schedule.every().tuesday.at("18:00").do(sharing_winner)
    schedule.every().day.at("00:01").do(bday)

    while True:
        schedule.run_pending()
        time.sleep(10)
