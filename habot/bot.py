"""
Bot functionality
"""

import traceback

import datetime

from habitica_helper import habiticatool
from habitica_helper.challenge import Challenge
from habot.habitica_operations import HabiticaOperator
from habot.io import HabiticaMessager
from habot.message import PrivateMessage

from conf.header import HEADER, PARTYMEMBER_HEADER
from conf.tasks import WINNER_PICKED


def handle_PMs():
    """
    React to commands given via private messages.
    """
    new_messages = PrivateMessage.messages_awaiting_reaction()
    for message in new_messages:
        react_to_message(message)


def react_to_message(message):
    """
    Perform whatever actions the given Message requires and send a response
    """
    commands = {
        "send-winner-message": SendWinnerMessage,
        "create-next-sharing-weekend": CreateNextSharingWeekend,
        }
    first_word = message.content.strip().split()[0]
    if first_word in commands:
        try:
            functionality = commands[first_word]()
            response = functionality.act(message)
        except:  # noqa: E722  pylint: disable=bare-except
            response = ("Something unexpected happened while handling "
                        "command `{}`:\n\n"
                        "```\n{}\n```".format(first_word,
                                              traceback.format_exc()))
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


class Functionality():
    """
    Base class for implementing real functionality.
    """

    def act(self, message):
        """
        Perform whatever actions this functionality needs and return a response
        """
        raise NotImplementedError("This command does not work yet.")

    def help(self):
        """
        Return a help string
        """
        # pylint: disable=no-self-use
        return "No instructions available for this command"


class SendWinnerMessage(Functionality):
    """
    Functionality for announcing sharing weekend challenge winner.
    """

    def __init__(self):
        self.partytool = habiticatool.PartyTool(PARTYMEMBER_HEADER)
        self.habitica_operator = HabiticaOperator(HEADER)
        super(SendWinnerMessage, self).__init__()

    def act(self, message):
        """
        Determine who should win this week's sharing weekend challenge.

        Returns a message listing the names of participants, the seed used for
        picking the winner, and the resulting winner. In case there are no
        participants, the message just states that.
        """
        challenge_id = self.partytool.current_sharing_weekend()["id"]
        challenge = Challenge(PARTYMEMBER_HEADER, challenge_id)
        completer_str = challenge.completer_str()
        try:
            today = datetime.date.today()
            last_tuesday = today - datetime.timedelta(today.weekday() - 1)
            winner_str = challenge.winner_str(last_tuesday, "^AEX")

            response = completer_str + "\n\n" + winner_str
        except IndexError:
            response = (completer_str + "\n\nNobody completed the challenge, "
                        "so winner cannot be chosen.")

        self.habitica_operator.tick_task(WINNER_PICKED, task_type="habit")
        return response

    def help(self):
        return ("List participants for the current sharing weekend challenge "
                "and declare a winner from amongst them. The winner is chosen "
                "using stock data as a source of randomness.")


class CreateNextSharingWeekend(Functionality):
    """
    A class for creating the next sharing weekend challenge.
    """
    # TODO implement me