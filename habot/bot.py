"""
Bot functionality
"""

import datetime
import re

from habitica_helper import habiticatool
from habitica_helper.challenge import Challenge

from habot.birthdays import BirthdayReminder
from habot.habitica_operations import HabiticaOperator
from habot.io import HabiticaMessager
import habot.logger
from habot.message import PrivateMessage
from habot.sharing_weekend import SharingChallengeOperator
from habot import utils

from conf.header import HEADER
from conf.tasks import WINNER_PICKED
from conf.sharing_weekend import STOCK_DAY_NUMBER, STOCK_NAME
from conf import conf


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


class Functionality():
    """
    Base class for implementing real functionality.
    """

    def __init__(self):
        """
        Initialize the functionality. Does nothing but add a logger.
        """
        self._logger = habot.logger.get_logger()

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

    def _sender_is_admin(self, message):
        """
        Return True if given message is sent by an admin user.

        Currently only @Antonbury is an admin.
        """
        # pylint: disable=no-self-use
        return message.from_id == conf.ADMIN_UID


class Ping(Functionality):
    """
    Respond with "pong".
    """

    def act(self, message):
        """
        Do nothing, respond with "pong".
        """
        return "Pong"

    def help(self):
        return "Does nothing but sends a response."

class ListBirthdays(Functionality):
    """
    Respond with a list of Habitica birthdays.
    """

    def act(self, message):
        """
        Return a response with todays birthdays.
        """
        bday_reminder = BirthdayReminder(HEADER)
        return bday_reminder.birthday_reminder_message()

    def help(self):
        """
        Return a help message.
        """
        # pylint: disable=no-self-use
        return "List party members who are celebrating their birthday today."


class SendWinnerMessage(Functionality):
    """
    Functionality for announcing sharing weekend challenge winner.
    """

    def __init__(self):
        self.partytool = habiticatool.PartyTool(HEADER)
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
        challenge = Challenge(HEADER, challenge_id)
        completer_str = challenge.completer_str()
        try:
            stock_day = utils.last_weekday_date(STOCK_DAY_NUMBER)
            winner_str = challenge.winner_str(stock_day, STOCK_NAME)

            response = completer_str + "\n\n" + winner_str
        except ValueError:
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

    def act(self, message, scheduled_run=False):
        """
        Create a new sharing weekend challenge and return a report.
        """
        # pylint: disable=arguments-differ

        if not scheduled_run and not self._sender_is_admin(message):
            return "Only administrators are allowed to create new challenges."

        tasks_path = "data/sharing_weekend_static_tasks.yml"
        questions_path = "data/weekly_questions.yml"
        self._logger.debug("create-next-sharing-weekend: tasks from %s, "
                           "weekly question from %s",
                           tasks_path, questions_path)

        operator = SharingChallengeOperator(HEADER)
        update_questions = True

        try:
            challenge = operator.create_new()
            operator.add_tasks(challenge.id, tasks_path, questions_path,
                               update_questions=update_questions)
        except:  # noqa: E722  pylint: disable=bare-except
            self._logger.error("Challenge creation failed", exc_info=True)
            return ("New challenge creation failed. Contact @Antonbury for "
                    "help.")

        challenge_url = (
                "https://habitica.com/challenges/{}".format(challenge.id))
        return ("A new sharing weekend challenge as available for joining: "
                "[{url}]({url})".format(url=challenge_url))

    def help(self):
        return ("Create a new sharing weekend challenge. No customization is "
                "currently available: the challenge is created with default "
                "parameters to the party the bot is currently in.")


class AwardWinner(Functionality):
    """
    A class for awarding a winner for a sharing weekend challenge.
    """

    def __init__(self):
        self.partytool = habiticatool.PartyTool(HEADER)
        self.habitica_operator = HabiticaOperator(HEADER)
        super().__init__()

    def act(self, message, scheduled_run=False):
        """
        Award a winner for the newest sharing weekend challenge.

        This operation is allowed only for administrators.

        :scheduled_run: Boolean: when True, message sender is not checked.
        """
        # pylint: disable=arguments-differ

        if not scheduled_run and not self._sender_is_admin(message):
            return "Only administrators are allowed to end challenges."

        challenge_id = self.partytool.current_sharing_weekend()["id"]
        challenge = Challenge(HEADER, challenge_id)
        today = datetime.date.today()
        stock_date = (today
                      - datetime.timedelta(today.weekday() - STOCK_DAY_NUMBER))
        winner = challenge.random_winner(stock_date, STOCK_NAME)
        challenge.award_winner(winner.id)
        return ("Congratulations are in order for {}, the lucky winner of {}!"
                "".format(winner, challenge.name))

    def help(self):
        return ("Award a stock data determined winner for the newest sharing "
                "weekend challenge.")
