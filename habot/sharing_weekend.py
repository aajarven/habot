"""
Bot functionality for running sharing weekend challenge
"""

from habitica_helper.challenge import ChallengeTool
from habitica_helper.utils import get_dict_from_api, get_next_weekday

from conf.sharing_weekend import SUMMARY, DESCRIPTION
from conf.tasks import CHALLENGE_CREATED
from habot.habitica_operations import HabiticaOperator


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
            "shortName": "testName",  # TODO
            "summary": SUMMARY,
            "description": DESCRIPTION,
            "prize": 0,  # TODO
            })
        self._operator.tick_task(CHALLENGE_CREATED)
        return challenge

    def _next_weekend_name(self):
        """
        Return the name of the challenge for the next weekend.
        """
        # pylint: disable=no-self-use
        sat = get_next_weekday("saturday")
        mon = get_next_weekday("monday", from_date=sat)

        if sat.month == mon.month:
            name = "Sharing Weekend {} {}−{}".format(
                sat.strftime("%b")[:3],
                sat.strftime("%-d"),
                mon.strftime("%-d"))
        else:
            name = "Sharing Weekend {} {} − {} {}".format(
                sat.strftime("%b")[:3],
                sat.strftime("%-d"),
                mon.strftime("%b")[:3],
                mon.strftime("%-d"))
        return name

    def _party_id(self):
        """
        Return the ID of the party user is currently in.
        """
        user_data = get_dict_from_api(self._header,
                                      "https://habitica.com/api/v3/user")
        return user_data["party"]["_id"]
