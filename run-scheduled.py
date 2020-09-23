"""
Automatically run scheduled tasks.
"""

import time
import traceback

import schedule

from conf.header import HEADER
from conf import conf
from habot.birthdays import BirthdayReminder
from habot.bot import handle_PMs, SendWinnerMessage
from habot.exceptions import CommunicationFailedException
from habot.io import HabiticaMessager
from habot.habitica_operations import HabiticaOperator
from habot.logger import get_logger


def ignore_429(func):
    """
    Do nothing if Habitica responds with status 429.

    Habitica API limits the rate at which API calls can be made (30 calls / 60
    seconds), and if the limit is exceeded, the server responds with 429 Too
    Many Requests. This decorator simply logs the response but does not retry
    or take any other measures.
    """
    def _wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except CommunicationFailedException as exc:
            if exc.response.status_code != 429:
                raise
            text = ("Too many API calls were made. This call will not be "
                    "retried. Stack trace:")
            get_logger().exception(text, exc_info=True)
    return _wrapper


def retry_429(func):
    """
    Retry after "Retry-After" seconds if Habitica responds with status 429.

    The request itself is not resent, but instead the whole function is run
    again.
    """
    def _wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except CommunicationFailedException as exc:
            if exc.response.status_code != 429:
                raise
            logger = get_logger()
            logger.exception("Habitica request limit exceeded: %s",
                             exc.response.headers, exc_info=False)
            wait_time = float(exc.response.headers["Retry-After"])
            logger.exception("Retrying %s after %.2f seconds...",
                             func.__name__, wait_time, exc_info=False)
            time.sleep(wait_time)
            func(*args, **kwargs)
    return _wrapper


@retry_429
def bday():
    """
    Send birthday reminder to Antonbury
    """
    bday_reminder = BirthdayReminder(HEADER)
    bday_reminder.send_birthday_reminder(conf.ADMIN_UID)


@retry_429
def sharing_winner():
    """
    Send a message announcing the sharing weekend winner.
    """
    winner_message_creator = SendWinnerMessage()
    HabiticaMessager(HEADER).send_private_message(
        conf.ADMIN_UID,
        winner_message_creator.act("send scheduled sharing weekend winner msg")
        )


@retry_429
def join_quest():
    """
    Join challenge if there is one to be joined.
    """
    operator = HabiticaOperator(HEADER)
    operator.join_quest()


@retry_429
def cron():
    """
    Run cron
    """
    operator = HabiticaOperator(HEADER)
    operator.cron()


@ignore_429
def fetch_messages():
    """
    Fetch messages using Habitica API
    """
    messager = HabiticaMessager(HEADER)
    messager.get_private_messages()


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

    schedule.every().tuesday.at("18:00").do(sharing_winner)
    schedule.every().day.at("00:01").do(bday)
    schedule.every().day.at("01:00").do(cron)

    main()
