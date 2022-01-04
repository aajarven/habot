"""
Functionality for sending a PM to everyone in the party
"""

from habot.functionality.base import Functionality, requires_party_membership
from habot.io.db import DBTool, DBSyncer
from habot.io.messages import HabiticaMessager

from conf.header import HEADER
from conf import conf


class SendPartyNewsletter(Functionality):
    """
    Send a message to all party members.
    """

    def __init__(self):
        """
        Initialize the class
        """
        self._db_syncer = DBSyncer(HEADER)
        self._db_tool = DBTool()
        self._messager = HabiticaMessager(HEADER)
        super().__init__()

    def help(self):
        """
        Return a help string.
        """
        example_content = (
                "# Important News!\n"
                "There's something very interesting going on and you should "
                "know about it. That's why you are receiving this newsletter. "
                "Please read it carefully :blush:\n\n"
                "Another paragraph with something **real** important here!"
                )
        example_result = self._format_newsletter(example_content,
                                                 "YourUsername")
        return ("Send an identical message to all party members."
                "\n\n"
                "For example the following command:\n"
                "```\n"
                "party-newsletter"
                "\n\n"
                f"{example_content}\n"
                "```\n"
                "will send the following message to all party members:\n"
                f"{example_result}"
                )

    @requires_party_membership
    def act(self, message):
        """
        Send out a newsletter to all party members.

        The bot does not send the message to itself. The command is only usable
        from within the party: if an external user requests sending a
        newsletter, they get an error message instead.

        The requestor gets a list of users to whom the newsletter was sent.
        """
        self._db_syncer.update_partymember_data()
        content = self._command_body(message).strip()
        partymember_uids = self._db_tool.get_party_user_ids()

        if message.from_id not in partymember_uids:
            self._logger.debug("Unauthorized newsletter request from %s",
                               message.from_id)
            return ("This command is usable only by people within the "
                    "party. No messages sent.")

        message = self._format_newsletter(
                content, self._db_tool.get_loginname(message.from_id))

        self._logger.debug("Going to send out the following party newsletter:"
                           "\n%s", message)
        recipients = []
        for uid in partymember_uids:
            if uid == HEADER["x-api-user"]:
                continue
            self._messager.send_private_message(uid, message)
            recipients.append(self._db_tool.get_loginname(uid))
            self._logger.debug("Sent out a newsletter to %s", recipients[-1])

        recipient_list_str = "\n".join([f"- @{name}"
                                        for name in recipients])
        self._logger.debug("A newsletter sent to %d party members",
                           len(recipients))
        return ("Sent the given newsletter to the following users:\n"
                f"{recipient_list_str}")

    def _format_newsletter(self, message, sender_name):
        """
        Return the given message with a standard footer appended.

        The footer tells who originally sent the newsletter and urges people to
        contact the admin if the bot is misbehaving.
        """
        # pylint: disable=no-self-use
        return (f"{message}"
                "\n\n---\n\n"
                f"This is a party newsletter written by @{sender_name} and "
                "brought you by the party bot. If you suspect you should "
                "not have received this message, please contact "
                f"@{self._db_tool.get_loginname(conf.ADMIN_UID)}."
                )
