"""
Basic bot functionality initiated via a private message
"""

from habot.io.db import DBTool
import habot.logger

from conf import conf


def requires_party_membership(act_function):
    """
    Wrapper for `act` functions that can only be used by party members.

    If a non-member tries to use a command with this decorator, they
    get an error message instead.
    """
    def wrapper(self, message):
        partymember_uids = DBTool().get_party_user_ids()

        if (
                message.from_id not in partymember_uids
                and message.from_id != conf.ADMIN_UID
                ):
            # pylint: disable=protected-access
            self._logger.debug("Unauthorized %s request from %s",
                               message.content.strip().split()[0],
                               message.from_id)
            return ("This command is usable only by people within the "
                    "party. No messages sent.")
        return act_function(self, message)
    return wrapper


def requires_admin_status(act_function):
    """
    Wrapper for `act` functions that can only be used by administrators.

    If a non-adinistrator tries to use a command with this decorator, they
    get an error message instead.
    """
    def wrapper(self, message):
        if message.from_id != conf.ADMIN_UID:
            # pylint: disable=protected-access
            self._logger.debug("Unauthorized %s request from %s",
                               message.content.strip().split()[0],
                               message.from_id)
            return ("This command is usable only administrators. No messages "
                    "sent.")
        return act_function(self, message)
    return wrapper


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

    def _command_body(self, message):
        """
        Return the body of the command sent as a message.

        This means the message content without the first word, e.g. for command
        "add-task todo: do something neat" this would be "todo: do something
        neat".

        If the message contains only the command, e.g. it is just "ping", an
        empty string is returned.
        """
        # pylint: disable=no-self-use
        parts = message.content.split(None, 1)
        if len(parts) > 1:
            return parts[1]
        return ""


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
