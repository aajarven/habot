"""
Bot functionality for running sharing weekend challenge
"""

from habitica_helper.challenge import ChallengeTool
from habitica_helper.utils import get_dict_from_api, get_next_weekday

from conf.sharing_weekend import SUMMARY, DESCRIPTION, GEM_PRIZE
from conf.tasks import CHALLENGE_CREATED
from habot.habitica_operations import HabiticaOperator, NotFoundException
from habot.io.yaml import YAMLFileIO


class SharingChallengeOperator():
    """
    Sharing Weekend challenge creator and operator.
    """

    def __init__(self, header):
        """
        Create a new operator

        :header: Header required by Habitica API
        """
        self._header = header
        self._operator = HabiticaOperator(header)

    def create_new(self):
        """
        Create a new sharing weekend challenge.

        Name, summary, description and prize are set, but no tasks are added.

        :returns: Challenge object representing the challenge
        """
        challenge_tool = ChallengeTool(self._header)
        challenge = challenge_tool.create_challenge({
            "group": self._party_id(),
            "name": self._next_weekend_name(),
            "shortName": self._next_weekend_shortname(),
            "summary": SUMMARY,
            "description": DESCRIPTION,
            "prize": GEM_PRIZE,
            })
        try:
            self._operator.tick_task(CHALLENGE_CREATED)
        except NotFoundException:
            # It's ok to run this task without having a habit to tick
            pass
        return challenge

    def add_tasks(self, challenge, static_task_file, question_file,
                  update_questions=True):
        """
        Add sharing weekend tasks to the challenge.

        :challenge: ID of the challenge
        :questionfile: path to the file from which the weekly question is read
        :update_questions: If set to False, the used weekly question isn't
                           marked as used.
        """
        static_tasks = YAMLFileIO.read_tasks(static_task_file)

        # The challenge starts on the next Saturday, so the due date will be
        # the following Monday
        deadline = get_next_weekday("mon", from_date=get_next_weekday("sat"))

        for task in static_tasks:
            task.date = deadline
            task.create_to_challenge(challenge, self._header)

        self._add_weekly_question(challenge, question_file, deadline,
                                  update_questions)

    def _add_weekly_question(self, challenge, question_file, deadline,
                             update_questions):
        """
        Get a question, add task to the challenge, and update the question file

        :challenge: ID of the challenge to which the question is to be added.
        :question_file: A file containing question data in YAMLFileIO compliant
                        YAML format.
        :deadline: Date to be used as the due date for the task.
        :update_questions: A boolean that determines if the question file is to
                           be updated.
        """
        all_questions = YAMLFileIO.read_question_list(question_file,
                                                      unused_only=False)
        unused_questions = YAMLFileIO.read_question_list(question_file,
                                                         unused_only=True)

        selected_question = None
        try:
            selected_question = unused_questions.popitem(last=False)[0]
        except KeyError:
            pass
        if not selected_question:
            raise IndexError("There are no more unused weekly questions "
                             f"in file '{question_file}'.")

        selected_question.difficulty = "hard"
        selected_question.date = deadline
        selected_question.create_to_challenge(challenge, self._header)

        if update_questions:
            del all_questions[selected_question]
            all_questions[selected_question] = True
            YAMLFileIO.write_question_list(all_questions, question_file)

    def _next_weekend_name(self):
        """
        Return the name of the challenge for the next weekend.
        """
        # pylint: disable=no-self-use
        sat = get_next_weekday("saturday")
        mon = get_next_weekday("monday", from_date=sat)

        if sat.month == mon.month:
            name = (f"Sharing Weekend {sat.strftime('%b')[:3]} "
                    f"{sat.strftime('%-d')}−{mon.strftime('%-d')}")
        else:
            name = ("Sharing Weekend "
                    f"{sat.strftime('%b')[:3]} {sat.strftime('%-d')} "
                    "− "
                    f"{mon.strftime('%b')[:3]} {mon.strftime('%-d')}")
        return name

    def _next_weekend_shortname(self):
        """
        Return a short name for the next challenge.

        The name is always "sharing weekend [year]-[weeknumber]".
        """
        # pylint: disable=no-self-use
        next_saturday = get_next_weekday("saturday")
        year = next_saturday.strftime("%Y")
        week = next_saturday.isocalendar()[1]
        return f"sharing weekend {year}-{week:02d}"

    def _party_id(self):
        """
        Return the ID of the party user is currently in.
        """
        user_data = get_dict_from_api(self._header,
                                      "https://habitica.com/api/v3/user")
        return user_data["party"]["_id"]
