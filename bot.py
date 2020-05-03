"""
CLI for performing bot actions
"""

import datetime
import click
from habitica_helper import habiticatool, stockrandomizer

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
    challenge = partytool.current_sharing_weekend()
    participants = partytool.challenge_participants(challenge["id"])
    completers = sorted(partytool.eligible_winners(challenge["id"],
                                                   participants))

    today = datetime.date.today()
    last_tuesday = today - datetime.timedelta(today.weekday() - 1)

    rand = stockrandomizer.StockRandomizer("^AEX", last_tuesday)
    winner_index = rand.pick_integer(0, len(completers))

    message_start = ("Eligible winners for challenge \"{}\" are:\n"
                     "".format(challenge["name"]))
    names = "".join(["- {}\n".format(member) for member in completers])
    rand_info = "Using stock data from {}\n\n".format(last_tuesday)
    winner = "{} wins the challenge!".format(completers[winner_index])

    message = message_start + names + "\n" + rand_info + winner

    if dry_run:
        print(message)
    else:
        message_sender = HabiticaMessager(HEADER)
        message_sender.send_private_message(
            "f687a6c7-860a-4c7c-8a07-9d0dcbb7c831", message)


if __name__ == "__main__":
    cli()
