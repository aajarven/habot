"""
Bot functionality for running sharing weekend challenge
"""

from habitica_helper.challenge import ChallengeTool

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
            "group": "2ff2c55f-b894-46c4-a8bd-d86e47b872ff",  # TODO
            "name": "test name",  # TODO
            "shortName": "testName",  # TODO
            "summary": SUMMARY,
            "description": DESCRIPTION,
            "prize": 0,  # TODO
            })
