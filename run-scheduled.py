"""
Automatically run scheduled tasks.
"""

import time
import traceback

import schedule

from conf.header import HEADER
from conf import conf
from habot.birthdays import BirthdayReminder
from habot.bot import (handle_PMs, SendWinnerMessage, AwardWinner,
                       CreateNextSharingWeekend, UpdatePartyDescription)
from habot.exceptions import CommunicationFailedException
from habot.io import HabiticaMessager
from habot.habitica_operations import HabiticaOperator
from habot.logger import get_logger


def update_party_description():
    """
    Update the quest queue in the party description to match the wiki page.

    This is done silently: if everything works as intended, nobody is notified.
    """
    result = UpdatePartyDescription().act("update-party-description")
    get_logger().info(result)


def bday():
    """
    Send birthday messages.

    A message is sent to the admin regardless of whether anyone is celebrating
    their birthday or not, but if someone is actually celebrating today, a
    message is sent to the party also.
    """
    bday_reminder = BirthdayReminder(HEADER)
    bday_reminder.send_birthday_reminder(conf.ADMIN_UID, sync=True)

    birthday_revellers = bday_reminder.birthdays_today()
    if not birthday_revellers:
        return
    message = bday_reminder.birthday_reminder_message()
    HabiticaMessager(HEADER).send_group_message("party", message)


def sharing_winner_message():
    """
    Send a message announcing the sharing weekend winner.
    """
    winner_message_creator = SendWinnerMessage()
    HabiticaMessager(HEADER).send_private_message(
        conf.ADMIN_UID,
        winner_message_creator.act("send scheduled sharing weekend winner msg")
        )


def handle_sharing_weekend():
    """
    Does the work of the weekly routine of ending and creating a challenge.
    """
    challenge_ender = AwardWinner()
    winner_message = challenge_ender.act("end challenge", scheduled_run=True)

    challenge_creator = CreateNextSharingWeekend()
    end_message = challenge_creator.act("create challenge", scheduled_run=True)

    HabiticaMessager(HEADER).send_group_message(
        "party", "\n\n".join([winner_message, end_message])
        )


def join_quest():
    """
    Join challenge if there is one to be joined.
    """
    operator = HabiticaOperator(HEADER)
    operator.join_quest()


def cron():
    """
    Run cron
    """
    operator = HabiticaOperator(HEADER)
    operator.cron()


def fetch_messages():
    """
    Fetch messages using Habitica API
    """
    messager = HabiticaMessager(HEADER)
    messager.get_private_messages()
    messager.get_party_messages()


def main():
    """
    Run the scheduled operations repeatedly.

    All exceptions raised from scheduled tasks are logged, and if possible,
    a report is sent to the admin. If there are too many consecutive errors,
    all operations are ceased.
    """
    consecutive_errors = 0

    while True:
        try:
            schedule.run_pending()
            consecutive_errors = 0
        except Exception:  # pylint: disable=broad-except
            get_logger().exception("A problem was encountered during a "
                                   "scheduled task. See stack trace. ",
                                   exc_info=True)
            consecutive_errors += 1
            report = ("A problem was encountered:\n"
                      "```{}```\n"
                      "Consecutive error count: {}"
                      "".format(traceback.format_exc(), consecutive_errors))
            try:
                HabiticaMessager(HEADER).send_private_message(
                    conf.ADMIN_UID,
                    report)
            except CommunicationFailedException:
                get_logger().exception("Could not send the error report. ",
                                       exc_info=True)
            if consecutive_errors > conf.MAX_CONSECUTIVE_FAILS:
                get_logger().info("Shutting down due to too many failures.")
                return
        time.sleep(2)


if __name__ == "__main__":
    schedule.every(1).minutes.do(fetch_messages)
    schedule.every(1).minutes.do(handle_PMs)
    schedule.every(4).hours.do(join_quest)
    schedule.every(6).hours.do(update_party_description)

    schedule.every().tuesday.at("18:00").do(sharing_winner_message)
    schedule.every().tuesday.at("18:10").do(handle_sharing_weekend)
    schedule.every().day.at("00:01").do(bday)
    schedule.every().day.at("01:00").do(cron)

    main()
