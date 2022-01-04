"""
Bot functionality related to questing.

This includes:
    - Listing quests of which someone in the party owns a copy
    - Sending reminders for party members whose quest is currently in the queue
"""

from habitica_helper.utils import get_dict_from_api

from habot.functionality.base import Functionality, requires_party_membership
from habot.io.db import DBTool, DBSyncer
from habot.io.messages import HabiticaMessager

from conf.header import HEADER


class ListOwnedQuests(Functionality):
    """
    Respond with a list of quests owned by the party members and their owners.
    """

    def __init__(self):
        """
        Initialize the class
        """
        self._db_tool = DBTool()
        super().__init__()

    def help(self):
        return ("List all quests someone in party owns and the names of the "
                "owners.")

    @requires_party_membership
    def act(self, message):
        """
        Return a table containing quests and their owners.
        """
        partymember_uids = self._db_tool.get_party_user_ids()
        quests = {}
        for member_uid in partymember_uids:
            member_name = self._db_tool.get_loginname(member_uid)
            member_data = get_dict_from_api(
                HEADER,
                f"https://habitica.com/api/v3/members/{member_uid}")
            quest_counts = member_data["items"]["quests"]
            for quest_name in quest_counts:
                count = quest_counts[quest_name]
                if count == 1:
                    partymember_str = f"@{member_name}"
                elif count >= 1:
                    partymember_str = f"@{member_name} ({count})"
                else:
                    continue

                if quest_name in quests:
                    quests[quest_name] = ", ".join([quests[quest_name],
                                                    partymember_str])
                else:
                    quests[quest_name] = partymember_str

        content_lines = [f"- **{quest}**: {quests[quest]}" for quest in quests]
        return "\n".join(content_lines)


class SendQuestReminders(Functionality):
    """
    Send out quest reminders.
    """
    # In this class, responses to user contain backticks which have to be
    # escaped for Habitica. Thus this warning is disabled to avoid them being
    # flagged as possibly erroneous.
    # pylint: disable=anomalous-backslash-in-string

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
        Provide instructions for the reminder command.
        """
        # pylint: disable=no-self-use
        return (
                "Send out quest reminders to the people in the given quest "
                "queue. The quest queue must be given inside a code block "
                "with each quest on its own line. Each quest line starts with "
                "the name of the quest, followed by a semicolon (;) and a "
                "comma-separated list of quest owner Habitica login names."
                "\n\n"
                "Reminders are sent for all except the first quest in the "
                "given queue. The first quest name is only used for telling "
                "the owner(s) of the second quest after which quest they "
                "should send the invite."
                "\n\n"
                "Each user is sent a separate message for each quest. Thus, "
                "if one user owns copies of more than one quest in the queue, "
                "they will receive more than one message."
                "\n\n"
                "For example the following message is a valid quest reminder:"
                "\n"
                "````\n"
                "quest-reminders\n"
                "```\n"
                "Lunar Battle: Part 1; @FirstInQueue\n"
                "Unicorn; @SomePartyMember\n"
                "Brazen Beetle Battle; @OtherGuy, @Questgoer9000\n"
                "```\n"
                "````\n"
                "and will result in quest reminder being sent out to "
                "`@SomePartyMember` for unicorn quest and to `@OtherGuy` "
                "and `@QuestGoer9000` for the beetle. Note that as mentioned, "
                "@FirstInQueue gets no reminder of their quest."
                "")

    def act(self, message):
        """
        Send reminders for quests in the message body.

        The body is expected to consist of a code block (enclosed by three
        backticks ``` on each side) containing one line for each quest
        for which a reminder is to be sent. The earliest quests are assumed
        to be in order from earliest in the queue to the last.

        Each line must begin with a identifier of the quest (this can be
        anything, e.g. the name of the quest) followed by a semicolon and a
        comma-separeted list of Habitica login names of the partymembers who
        should be reminded of this quest. For example
        Questname; @user1, @user2, @user3
        is a valid line.
        """
        self._db_syncer.update_partymember_data()
        content = self._command_body(message)

        try:
            self._validate(content)
        except ValidationError as err:
            return ("A problem was encountered when reading the quest list: "
                    f"{str(err)}\n\n"
                    "No messages were sent.")

        reminder_data = content.split("```")[1]
        reminder_lines = reminder_data.strip().split("\n")
        previous_quest = reminder_lines[0].split(";")[0]
        sent_reminders = 0
        for line in reminder_lines[1:]:
            if line.strip():
                parts = line.split(";")
                quest_name = parts[0].strip()
                users = [name.strip().lstrip("@")
                         for name in parts[1].split(",")]
                for user in users:
                    self._send_reminder(quest_name, user, len(users),
                                        previous_quest)
                    sent_reminders += 1
                previous_quest = quest_name

        return f"Sent out {sent_reminders} quest reminders."

    def _validate(self, command_body):
        """
        Ensure that the command body looks sensible.

        Make sure that
          - the command body contains exactly one code block
          - each non-empty line in the code block contains exactly one
            semicolon
          - there is content both before and after the semicolon
          - all names in the list of quest owners start with an '@'

        If the command is deemed faulty, a ValidationError is raised.
        """
        parts = command_body.split("```")
        if not len(parts) == 3:
            raise ValidationError(
                    "The list of reminders to be sent must be given inside "
                    "a code block (surrounded by three backticks i"
                    "\`\`\`). A code block was not found in "  # noqa: W605
                    "the message."
                    )

        reminder_data = parts[1]
        first_line = True

        for line in reminder_data.split("\n"):

            if not line.strip():
                continue

            parts = line.split(";")
            if len(parts) != 2:
                raise ValidationError(
                        "Each line in the quest queue must be divided into "
                        "two parts by a semicolon (;), the first part "
                        "containing the name of the quest and the latter "
                        "holding the names of the participants. Line "
                        f"`{line}` did not match this format."
                        )

            if not parts[0].strip():
                raise ValidationError(
                        f"Problem in line `{line}`: quest name cannot be "
                        "empty."
                        )

            if not first_line:
                if not parts[1].strip():
                    raise ValidationError(
                            "No quest owners listed for quest "
                            f"{parts[0].strip()}"
                            )

                for owner_str in parts[1].split(","):
                    owner_name = owner_str.strip().lstrip("@")
                    if not owner_name:
                        raise ValidationError(
                                f"Malformed quest owner list for quest {line}"
                                )
                    try:
                        self._db_tool.get_user_id(owner_name)
                    except ValueError as err:
                        raise ValidationError(
                                f"User @{owner_name} not found in the party"
                                ) from err
            first_line = False
        self._logger.debug("Quest data successfully validated")

    def _send_reminder(self, quest_name, user_name, n_users, previous_quest):
        """
        Send out a reminder about given quest to given user.

        :quest_name: Name of the quest
        :user_name: Habitica login name for the recipient
        :n_users: Total number of users receiving this reminder
        :previous_quest: Name of the quest after which the user should send out
                         the invitation to their quest
        """
        recipient_uid = self._db_tool.get_user_id(user_name)
        message = self._message(quest_name, n_users, previous_quest)
        self._logger.debug("Sending a quest reminder for %s to %s (%s)",
                           quest_name, user_name, recipient_uid)
        self._messager.send_private_message(recipient_uid, message)

    def _message(self, quest_name, n_users, previous_quest):
        """
        Return a reminder message for the parameters.

        :quest_name: Name of the quest
        :n_users: Total number of users receiving this reminder
        :previous_quest: Name of the quest after which the user should send out
                         the invitation to their quest
        """
        # pylint: disable=no-self-use
        if n_users > 2:
            who = f"You (and {n_users - 1} others)"
        elif n_users == 2:
            who = "You (and one other partymember)"
        else:
            who = "You"
        return (f"{who} have a quest coming up in the queue: {quest_name}! "
                f"It comes after {previous_quest}, so when you notice that "
                f"{previous_quest} has ended, please send out the invite for "
                f"{quest_name}.")


class ValidationError(ValueError):
    """
    Error for cases where user input is erroneous
    """
