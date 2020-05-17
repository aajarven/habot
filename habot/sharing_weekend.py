"""
Bot functionality for running sharing weekend challenge
"""

from habitica_helper.challenge import ChallengeTool
from habitica_helper.utils import get_dict_from_api

from conf.sharing_weekend import SUMMARY, DESCRIPTION


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

    def create_new(self):
        """
        Create a new sharing weekend challenge.

        Name, summary, description and prize are set, but no tasks are added.

        :returns: Challenge object representing the challenge
        """
        ct = ChallengeTool(self._header)
        return ct.create_challenge({
            "group": self._party_id(),
            "name": "test name",  # TODO
            "shortName": "testName",  # TODO
            "summary": SUMMARY,
            "description": DESCRIPTION,
            "prize": 0,  # TODO
            })

    def _party_id(self):
        """
        Return the ID of the party user is currently in.
        """
        user_data = get_dict_from_api(self._header,
                                      "https://habitica.com/api/v3/user")
        return user_data["party"]["_id"]
