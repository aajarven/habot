"""
CLI for performing bot actions
"""

import datetime
import click
from habitica_helper import habiticatool
from habitica_helper.challenge import Challenge

from conf.header import HEADER, PARTYMEMBER_HEADER
from habot.io import HabiticaMessager


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


if __name__ == "__main__":
    cli()
