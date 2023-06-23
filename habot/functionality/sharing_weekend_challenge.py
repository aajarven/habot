"""
Functionality for taking care of weekly Sharing Weekend challenges.

This includes:
    - Creating a new challenge
    - Listing participants of a challenge and drawing a winner
    - Ending the challenge and awarding a winner
    - Reporting the number of unused questions
"""

import datetime

from habitica_helper import habiticatool
from habitica_helper.challenge import Challenge

from habot.functionality.base import Functionality
from habot.habitica_operations import HabiticaOperator
from habot.io.yaml import YAMLFileIO
from habot.sharing_weekend import SharingChallengeOperator
from habot import utils

from conf.header import HEADER
from conf.tasks import WINNER_PICKED
from conf.sharing_weekend import STOCK_DAY_NUMBER, STOCK_NAME, QUESTIONS_PATH


class SendWinnerMessage(Functionality):
    """
    Functionality for announcing sharing weekend challenge winner.
    """

    def __init__(self):
        self.partytool = habiticatool.PartyTool(HEADER)
        self.habitica_operator = HabiticaOperator(HEADER)
        super().__init__()

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
        self._logger.debug("create-next-sharing-weekend: tasks from %s, "
                           "weekly question from %s",
                           tasks_path, QUESTIONS_PATH)

        operator = SharingChallengeOperator(HEADER)
        update_questions = True

        try:
            challenge = operator.create_new()
            operator.add_tasks(challenge.id, tasks_path, QUESTIONS_PATH,
                               update_questions=update_questions)
        except:  # noqa: E722  pylint: disable=bare-except
            self._logger.error("Challenge creation failed", exc_info=True)
            return ("New challenge creation failed. Contact @Antonbury for "
                    "help.")

        challenge_url = f"https://habitica.com/challenges/{challenge.id}"
        return ("A new sharing weekend challenge is available for joining: "
                f"[{challenge_url}]({challenge_url})")

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
        return (f"Congratulations are in order for {winner}, the lucky winner "
                f"of {challenge.name}!")

    def help(self):
        return ("Award a stock data determined winner for the newest sharing "
                "weekend challenge.")


class CountUnusedQuestions(Functionality):
    """
    A class for reporting the number of unused questions left.
    """

    def act(self, message):
        """
        Respond with the number of unused questions. No changes made.
        """
        questions = YAMLFileIO.read_question_list(
                QUESTIONS_PATH,
                unused_only=True
                )
        n_questions = len(questions.values())
        if n_questions == 1:
            return "There is 1 unused sharing weekend question"

        return f"There are {n_questions} unused sharing weekend questions"
