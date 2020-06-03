"""
CLI for performing bot actions
"""

import datetime
import click

from habitica_helper import habiticatool
from habitica_helper.challenge import Challenge

from conf.header import HEADER, PARTYMEMBER_HEADER
from conf.tasks import WINNER_PICKED
from habot.birthdays import BirthdayReminder
from habot.io import HabiticaMessager
from habot.habitica_operations import HabiticaOperator
from habot.sharing_weekend import SharingChallengeOperator


@click.group()
def cli():
    """
    Command line interface for activating the bot.
    """
    pass


@cli.command()
@click.option("--dry-run", default=False, is_flag=True)
def send_winner_message(dry_run):
    """
    Pick the challenge winner using habitica-helper and PM Antonbury.

    No actual actions related to the challenge (e.g. actually picking the
    winner) are performed: just picking the name of the winner.
    """
    partytool = habiticatool.PartyTool(PARTYMEMBER_HEADER)
    challenge_id = partytool.current_sharing_weekend()["id"]
    challenge = Challenge(PARTYMEMBER_HEADER, challenge_id)

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
        print(message)
    else:
        message_sender = HabiticaMessager(HEADER)
        message_sender.send_private_message(
            "f687a6c7-860a-4c7c-8a07-9d0dcbb7c831", message)

    habitica_operator = HabiticaOperator(HEADER)
    habitica_operator.tick_task(WINNER_PICKED, task_type="habit")


@cli.command()
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
@click.option("--test/--no-test",
              is_flag=True, default=True,
              help="If --test is set, the challenge is created for the bot, "
                   "not for the actual party member account, and no new "
                   "weekly questions are marked as used.")
def create_next_sharing_weekend(tasks, questions, test):
    """
    Create a new sharing weekend challenge for the next weekend.

    If the challenge creation fails, a PM is sent to the party member with a
    traceback from the problematic function call

    If the challenge creation fails, a PM is sent to the party member with a
    traceback from the problematic function call.
    """
    if test:
        header = HEADER
        update_questions = False
    else:
        header = PARTYMEMBER_HEADER
        update_questions = True

    operator = SharingChallengeOperator(header)
    message_sender = HabiticaMessager(HEADER)

    try:
        challenge = operator.create_new()
        operator.add_tasks(challenge.id, tasks, questions,
                           update_questions=update_questions)
    except:  # noqa: E722  pylint: disable=bare-except
        report = ("There was a problem during sharing weekend challenge "
                  "creation:\n\n```{}```".format(traceback.format_exc()))
        message_sender.send_private_message(PARTYMEMBER_HEADER["x-api-user"],
                                            report)
        raise

    report = ("Created a new sharing weekend challenge: "
              "https://habitica.com/challenges/{}".format(challenge.id))
    message_sender.send_private_message(PARTYMEMBER_HEADER["x-api-user"],
                                        report)


@cli.command()
@click.argument("message", type=str)
@click.option("--recipient_uid", type=str,
              default="f687a6c7-860a-4c7c-8a07-9d0dcbb7c831",
              help=("Habitica user ID of the recipient. Default "
                    "is Antonbury's"))
def send_pm(message, recipient_uid):
    """
    Send a private message.
    """
    message_sender = HabiticaMessager(HEADER)
    message_sender.send_private_message(recipient_uid, message)


@cli.command()
@click.option("--recipient_uid", type=str,
              default="f687a6c7-860a-4c7c-8a07-9d0dcbb7c831",
              help=("Habitica user ID of the recipient. Default "
                    "is Antonbury's"))
def send_birthday_reminder(recipient_uid):
    """
    Send a private message listing everyone who is having their birthday.
    """
    reminder = BirthdayReminder(HEADER)
    reminder.send_birthday_reminder(recipient_uid)


if __name__ == "__main__":
    cli()
