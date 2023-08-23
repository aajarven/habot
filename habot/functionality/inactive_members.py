"""
Functionality for handling inactive party members
"""

import datetime
import urllib.parse

from habitica_helper import habrequest

from conf.header import HEADER, PARTY_OWNER_HEADER
from conf.inactive_members import (ALLOW_INACTIVITY_FROM,
                                   INACTIVITY_THRESHOLD_DAYS)
from habot.functionality.base import (Functionality,
                                      requires_party_membership,
                                      requires_admin_status)
from habot.io.db import DBTool, DBSyncer
from habot.io.messages import HabiticaMessager


class ListInactiveMembers(Functionality):
    """
    Responds with a list of inactive party members.

    A member is considered inactive if they have not logged in within the last
    three months.
    """

    threshold = datetime.timedelta(days=INACTIVITY_THRESHOLD_DAYS)

    def __init__(self):
        """
        Initialize the class
        """
        self._db_syncer = DBSyncer(HEADER)
        self._db_tool = DBTool()
        self._messager = HabiticaMessager(HEADER)
        super().__init__()

    @property
    def allowed_inactive_members(self):
        """
        Return list of allowed inactive members from confs
        """
        return ALLOW_INACTIVITY_FROM

    def inactive_members(self, member_data):
        """
        Return a list of inactive members

        Members on the list of allowed inactive members are not included in the
        list.
        """
        now = datetime.date.today()

        inactive_members = []
        for member in member_data:
            if now - member["lastlogin"] > self.threshold:
                if member["loginname"] in self.allowed_inactive_members:
                    continue
                inactive_members.append(member)
        return inactive_members

    @requires_party_membership
    def act(self, message):
        self._db_syncer.update_partymember_data()
        member_data = self._db_tool.get_partymember_data()

        inactive_members = self.inactive_members(member_data)
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


class RemoveInactiveMembers(Functionality):
    """
    Removes members who have been inactive for a long time from a party
    """

    def __init__(self):
        """
        Initialize the class
        """
        self._db_syncer = DBSyncer(HEADER)
        self._db_tool = DBTool()
        self._messager = HabiticaMessager(HEADER)
        super().__init__()

    def _remove_from_party(self, member):
        """
        Remove the given member from the party.
        """
        # pylint: disable=no-self-use
        id_ = member['id']
        removal_message = (
            f"Hey {member['displayname']},\n"
            "We haven't seen you in a long time in the Party. We hope this "
            "means that you're doing well and have built a support system "
            "outside Habitica. As you probably know, there is a 30 member "
            "limit to Habitica Parties. We recently reached that Party limit, "
            "and would like to extend our support to others who may benefit "
            "from our support as we hope you've benefited.  To that end, and "
            "because you haven't logged into Habitica in over 3 months, we "
            "feel it appropriate to release you from the Party to make space "
            "for others.  This is not a punishment or admonishment in any "
            "way; please know that if you come back someday, and there is "
            "space, we will gladly invite you back.\n\n"
            "Much love and the best of wishes in your endeavors,\n"
            "Your Mental Health Warrior friends"
        )
        message = urllib.parse.quote(removal_message, safe='')

        self._logger.debug(
            "Attempting to remove inactive user %s from party",
            member['displayname']
        )

        response = habrequest.post(
            (
                f"https://habitica.com/api/v3/groups/party/removeMember/{id_}"
                f"?message={message}"
            ),
            PARTY_OWNER_HEADER,
            )

        self._logger.debug(
            "Response to removal of inactive user %s from party: %s",
            member['displayname'],
            response.status_code,
        )

        self._messager.send_private_message(id_, removal_message)

    @requires_admin_status
    def act(self, message):
        """
        Remove all inactive users from the party.
        """
        # pylint: disable=unused-argument
        self._db_syncer.update_partymember_data()
        member_data = self._db_tool.get_partymember_data()

        inactive_members = ListInactiveMembers().inactive_members(member_data)

        if not inactive_members:
            return "No inactive members found"

        response = ["Removed the following members from party:"]
        for member in inactive_members:
            self._remove_from_party(member)
            response.append(f"- @{member['loginname']}")

        return "\n".join(response)
