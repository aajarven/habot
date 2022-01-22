"""
Functionality for handling inactive party members
"""

import datetime

from conf.header import HEADER
from habot.functionality.base import Functionality, requires_party_membership
from habot.io.db import DBTool, DBSyncer
from habot.io.messages import HabiticaMessager


class ListInactiveMembers(Functionality):
    """
    Responds with a list of inactive party members.

    A member is considered inactive if they have not logged in within the last
    three months.
    """

    threshold = datetime.timedelta(days=30*3)

    def __init__(self):
        """
        Initialize the class
        """
        self._db_syncer = DBSyncer(HEADER)
        self._db_tool = DBTool()
        self._messager = HabiticaMessager(HEADER)
        super().__init__()

    @requires_party_membership
    def act(self, message):
        self._db_syncer.update_partymember_data()
        member_data = self._db_tool.get_partymember_data()
        now = datetime.date.today()

        inactive_members = []
        for member in member_data:
            if now - member["lastlogin"] > self.threshold:
                inactive_members.append(member)

        return self._construct_message(inactive_members)

    def _construct_message(self, inactive_users):
        """
        Construct a report of inactive users
        """
        # pylint: disable=no-self-use
        if not inactive_users:
            return "No inactive members found!"

        header = "The following party members are inactive:\n"
        user_list = "\n".join(
                [
                    f"- @{user['loginname']} "
                    f"(last login {str(user['lastlogin'])})"
                    for user in inactive_users
                    ]
                )

        return header + user_list
