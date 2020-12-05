"""
CLI for performing bot actions
"""

import datetime
import sys

import click

from habitica_helper import habiticatool
from habitica_helper.challenge import Challenge

from conf.header import HEADER
from conf.tasks import WINNER_PICKED
from conf import conf
from habot.birthdays import BirthdayReminder
from habot.io import HabiticaMessager, DBSyncer
from habot.habitica_operations import HabiticaOperator
import habot.logger
from habot.sharing_weekend import SharingChallengeOperator


@click.group()
@click.pass_context
def cli(ctx):
    """
    Command line interface for activating the bot.
    """
    ctx.ensure_object(dict)
    if "logger" not in ctx.obj:
        ctx.obj["logger"] = habot.logger.get_logger()


@cli.command()
@click.pass_context
@click.option("--dry-run", default=False, is_flag=True)
def send_winner_message(ctx, dry_run):
    """
    Pick the challenge winner using habitica-helper and PM Antonbury.

    No actual actions related to the challenge (e.g. actually picking the
    winner) are performed: just picking the name of the winner.
    """
    log = ctx.obj["logger"]
    log.debug("send-winner-message (dry-run={})".format(dry_run))
    partytool = habiticatool.PartyTool(HEADER)
    challenge_id = partytool.current_sharing_weekend()["id"]
    challenge = Challenge(HEADER, challenge_id)

    completer_str = challenge.completer_str()

    try:
        today = datetime.date.today()
        last_tuesday = today - datetime.timedelta(today.weekday() - 1)
        winner_str = challenge.winner_str(last_tuesday, "^AEX")

        message = completer_str + "\n\n" + winner_str
    except IndexError:
        message = (completer_str + "\n\nNobody completed the challenge, so "
                   "winner cannot be chosen.")
    if dry_run:
        logger.info("Message was not sent due to --dry-run. The message would "
                    "have been:\n%s", message)
    else:
        recipient = conf.ADMIN_UID
        message_sender = HabiticaMessager(HEADER)
        message_sender.send_private_message(recipient, message)
        logger.info("Following message sent to %s:\n%s", recipient, message)

    habitica_operator = HabiticaOperator(HEADER)
    habitica_operator.tick_task(WINNER_PICKED, task_type="habit")


@cli.command()
@click.pass_context
@click.option("--tasks", "-t",
              default="data/sharing_weekend_static_tasks.yml",
              type=click.Path(exists=True),
              help="Path to file that contains YAML description of the "
                   "tasks that stay the same every week.")
@click.option("--questions", "-q",
              default="data/weekly_questions.yml",
              type=click.Path(exists=True),
              help="Path to file that contains YAML descriptions of the "
                   "weekly questions. One of these is used.")
def create_next_sharing_weekend(ctx, tasks, questions, test):
    """
    Create a new sharing weekend challenge for the next weekend.

    If the challenge creation fails, a PM is sent to the party member with a
    traceback from the problematic function call

    If the challenge creation fails, a PM is sent to the party member with a
    traceback from the problematic function call.
    """
    log = ctx.obj["logger"]
    log.debug("create-next-sharing-weekend: tasks from %s, weekly question "
              "from %s, --test=%s", tasks, questions, test)
    operator = SharingChallengeOperator(HEADER)
    message_sender = HabiticaMessager(HEADER)

    try:
        challenge = operator.create_new()
        operator.add_tasks(challenge.id, tasks, questions,
                           update_questions=update_questions)
    except:  # noqa: E722  pylint: disable=bare-except
        report = "New challenge creation failed. Contact @Antonbury for help."
        message_sender.send_private_message(conf.ADMIN_UID, report)
        log.error("A problem was encountered during sharing weekend challenge "
                  "creation. See stack trace.", exc_info=True)
        sys.exit(1)

    report = ("Created a new sharing weekend challenge: "
              "https://habitica.com/challenges/{}".format(challenge.id))
    message_sender.send_private_message(conf.ADMIN_UID, report)
    log.info(report)


@cli.command()
@click.pass_context
@click.argument("message", type=str)
@click.option("--recipient_uid", type=str, default=conf.ADMIN_UID,
              help=("Habitica user ID of the recipient. Default "
                    "is Antonbury's"))
def send_pm(ctx, message, recipient_uid):
    """
    Send a private message.
    """
    log = ctx.obj["logger"]
    log.debug("Sending a PM to %s with the following content:\n%s",
              recipient_uid, message)
    message_sender = HabiticaMessager(HEADER)
    message_sender.send_private_message(recipient_uid, message)


@cli.command()
@click.pass_context
@click.option("--recipient_uid", type=str, default=conf.ADMIN_UID,
              help=("Habitica user ID of the recipient. Default "
                    "is Antonbury's"))
@click.option("--no-sync", is_flag=True,
              help=("Don't update the database using the fresh data from the "
                    "API, but use old database data instead. This makes the "
                    "command run somewhat faster but risks using outdated "
                    "data."))
@click.option("--test", is_flag=True,
              help="Don't send the message, just print it")
def send_birthday_reminder(ctx, recipient_uid, no_sync, test):
    """
    Send a private message listing everyone who is having their birthday.
    """
    log = ctx.obj["logger"]
    log.debug("Birthday reminder: recipient=%s, no_sync=%s, test=%s",
              recipient_uid, no_sync, test)
    if not no_sync:
        db_syncer = DBSyncer(HEADER)
        db_syncer.update_partymember_data()
        log.debug("Birthdays synced to database.")
    reminder = BirthdayReminder(HEADER)
    if test:
        log.info("Message not sent. Content would have been:\n%s",
                 reminder.birthday_reminder_message())
    else:
        reminder.send_birthday_reminder(recipient_uid)
        log.info("Message sent to {}".format(recipient_uid))


if __name__ == "__main__":
    logger = habot.logger.get_logger()
    try:
        # pylint: disable=no-value-for-parameter, unexpected-keyword-arg
        cli(obj={"logger": logger})
    except Exception:  # pylint: disable=broad-except
        logger.exception("A problem was encountered. See track trace for "
                         "details.", exc_info=True)
