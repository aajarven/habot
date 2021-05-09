"""
Reacting to PMs by initiating the correct functionality.
"""

import re

from habot.functionality.base import Ping
from habot.functionality.birthdays import ListBirthdays
from habot.functionality.newsletter import SendPartyNewsletter
from habot.functionality.party_description import UpdatePartyDescription
from habot.functionality.quests import ListOwnedQuests, SendQuestReminders
from habot.functionality.sharing_weekend_challenge import (
        SendWinnerMessage, CreateNextSharingWeekend, AwardWinner)
from habot.functionality.tasks import AddTask
from habot.io.messages import HabiticaMessager
import habot.logger
from habot.message import PrivateMessage

from conf.header import HEADER


def handle_PMs():
    """
    React to commands given via private messages.
    """
    # pylint: disable=invalid-name
    new_messages = PrivateMessage.messages_awaiting_reaction()
    for message in new_messages:
        react_to_message(message)


def ignorable(message_content):
    """
    Return True if message should be ignored.

    Currently only gem gifting messages are ignored.
    """
    return re.match(r"`Hello \S*, \S* has sent you \d* gems!`",
                    message_content)


def react_to_message(message):
    """
    Perform whatever actions the given Message requires and send a response
    """
    logger = habot.logger.get_logger()

    if ignorable(message.content):
        HabiticaMessager.set_reaction_pending(message, False)
        logger.debug("Message %s doesn' need a reaction", message.content)
        return

    commands = {
        "list-birthdays": ListBirthdays,
        "send-winner-message": SendWinnerMessage,
        "create-next-sharing-weekend": CreateNextSharingWeekend,
        "award-latest-winner": AwardWinner,
        "ping": Ping,
        "add-task": AddTask,
        "quest-reminders": SendQuestReminders,
        "party-newsletter": SendPartyNewsletter,
        "owned-quests": ListOwnedQuests,
        "update-party-description": UpdatePartyDescription,
        }
    first_word = message.content.strip().split()[0]
    logger.debug("Got message starting with %s", first_word)
    if first_word in commands:
        try:
            functionality = commands[first_word]()
            response = functionality.act(message)
        except:  # noqa: E722  pylint: disable=bare-except
            logger.error("A problem was encountered during reacting to "
                         "message. See stack trace.", exc_info=True)
            response = ("Something unexpected happened while handling command "
                        "`{}`. Contact @Antonbury for "
                        "help.".format(first_word))
    else:
        command_list = ["`{}`: {}".format(command,
                                          commands[command]().help())
                        for command in commands]
        response = ("Command `{}` not recognized.\n\n".format(first_word) +
                    "I am a bot: not a real human user. If I am misbehaving " +
                    "or you need assistance, please contact @Antonbury.\n\n" +
                    "Available commands:\n\n" +
                    "\n\n".join(command_list))

    HabiticaMessager(HEADER).send_private_message(message.from_id, response)
    HabiticaMessager.set_reaction_pending(message, False)
