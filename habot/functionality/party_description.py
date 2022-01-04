"""
Functionality for updating party description.
"""

import datetime

from habitica_helper import habiticatool

from habot.functionality.base import Functionality, requires_party_membership
from habot.io.wiki import WikiReader, WikiParsingError, HtmlToMd
import habot.logger

from conf.header import HEADER
from conf import conf

try:
    # It's okay for the secrets not to be in place during testing: they are
    # mocked.
    # pylint: disable=no-name-in-module
    from conf.secrets import habitica_credentials
except ImportError:
    habot.logger.get_logger().error(
            "Credential file not found. If you are trying to use "
            "the bot instead of just running unit tests, please "
            "see readme and properly set Habitica credentials.")


class UpdatePartyDescription(Functionality):
    """
    Replace the quest queue in the party description with an updated one.

    The quest queue contents are fetched from the party wiki page (determined
    in `conf.PARTY_WIKI_URL`).

    The response contains the old and new contents of the party description.
    """

    def __init__(self):
        """
        Initialize the class
        """
        self._partytool = habiticatool.PartyTool(HEADER)
        self._wikireader = WikiReader(conf.PARTY_WIKI_URL)
        super().__init__()

    def help(self):
        """
        Return a help string
        """
        # pylint: disable=no-self-use
        return ("Fetch new quest queue from the party wiki page and update it "
                "to the party description.")

    @requires_party_membership
    def act(self, message):
        """
        Update the quest queue in party description.

        :returns: A response containing the old and new party descriptions.
        """
        old_description = self._partytool.party_description()
        new_queue = self._parse_quest_queue_from_wiki()
        new_description = self._replace_quest_queue(old_description, new_queue)
        self._partytool.update_party_description(
                new_description,
                user_id=habitica_credentials.PARTY_OWNER_USER_ID,
                api_token=habitica_credentials.PARTY_OWNER_API_TOKEN)
        return ("Updated the party description. Old description:\n\n"
                "```\n"
                f"{old_description}\n"
                "```\n"
                "---\n\n"
                "New description:\n\n"
                f"{new_description}")

    def _parse_quest_queue_from_wiki(self):
        """
        Return a string containing a Habitica markdown formatted quest queue.

        The returned quest queue begins with a "header" containing the date and
        time at which the queue was read from the wiki.

        The data is fetched from an unordered list in the wiki page, identified
        by it containing an item containing "(CURRENT)". It is returned in
        Habitica ordered list format with the first quest shown as the
        "zeroeth", e.g.
        ```
        The Quest Queue (as in Wiki on Apr 24 at 14:18 UTC):

         0. (CURRENT) Wind-Up Hatching Potions (Boss 1000)
         1. Dolphin (Boss 300)
         2. Seahorse (Boss 300)
         3. Monkey (Boss 400)
         4. Cheetah (Boss 600)
         5. Kangaroo (Boss 700)
         6. Silver Hatching Potions (collection)
         7. Ferret (Boss 400)
        ```

        :returns: A string containing the current quest queue.
        """
        ols = self._wikireader.find_elements_with_matching_subelement(
                "ol", "(CURRENT)")
        if len(ols) != 1:
            raise WikiParsingError("Identifying a single quest queue in party "
                                   f"wiki page {conf.PARTY_WIKI_URL} failed: "
                                   f"{len(ols)} queue candidates found.")

        current_time = datetime.datetime.now(datetime.timezone.utc)
        timestamp = current_time.strftime("%b %d at %H:%M UTC%z")
        quest_queue_header = f"The Quest Queue (as in Wiki on {timestamp}):"
        quest_queue_content = HtmlToMd(ol_starting_index=0).convert(ols[0])
        return f"{quest_queue_header}\n\n{quest_queue_content}"

    def _replace_quest_queue(self, old_description, new_queue):
        """
        Return the old description with everything in it starting with "The
        Quest queue" replaced with the given new_queue.
        """
        # pylint: disable=no-self-use
        return old_description.split("The Quest Queue ")[0] + new_queue
