"""
Bot functionality
"""

import datetime
import re

from habitica_helper import habiticatool
from habitica_helper.challenge import Challenge
from habitica_helper.utils import get_dict_from_api

from habot.birthdays import BirthdayReminder
from habot.habitica_operations import HabiticaOperator
from habot.io import (HabiticaMessager, DBSyncer, DBTool, WikiReader,
                      WikiParsingError)
import habot.logger
from habot.message import PrivateMessage
from habot.sharing_weekend import SharingChallengeOperator
from habot import utils

from conf.header import HEADER
from conf.tasks import WINNER_PICKED
from conf.sharing_weekend import STOCK_DAY_NUMBER, STOCK_NAME
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


def handle_PMs():
    """
    React to commands given via private messages.
    """
    # pylint: disable=invalid-name
    new_messages = PrivateMessage.messages_awaiting_reaction()
    for message in new_messages:
        react_to_message(message)


def ignorable(message_content):
    """
    Return True if message should be ignored.

    Currently only gem gifting messages are ignored.
    """
    return re.match(r"`Hello \S*, \S* has sent you \d* gems!`",
                    message_content)


def react_to_message(message):
    """
    Perform whatever actions the given Message requires and send a response
    """
    logger = habot.logger.get_logger()

    if ignorable(message.content):
        HabiticaMessager.set_reaction_pending(message, False)
        logger.debug("Message %s doesn' need a reaction", message.content)
        return

    commands = {
        "list-birthdays": ListBirthdays,
        "send-winner-message": SendWinnerMessage,
        "create-next-sharing-weekend": CreateNextSharingWeekend,
        "award-latest-winner": AwardWinner,
        "ping": Ping,
        "add-task": AddTask,
        "quest-reminders": QuestReminders,
        "party-newsletter": PartyNewsletter,
        "owned-quests": QuestList,
        "update-party-description": UpdatePartyDescription,
        }
    first_word = message.content.strip().split()[0]
    logger.debug("Got message starting with %s", first_word)
    if first_word in commands:
        try:
            functionality = commands[first_word]()
            response = functionality.act(message)
        except:  # noqa: E722  pylint: disable=bare-except
            logger.error("A problem was encountered during reacting to "
                         "message. See stack trace.", exc_info=True)
            response = ("Something unexpected happened while handling command "
                        "`{}`. Contact @Antonbury for "
                        "help.".format(first_word))
    else:
        command_list = ["`{}`: {}".format(command,
                                          commands[command]().help())
                        for command in commands]
        response = ("Command `{}` not recognized.\n\n".format(first_word) +
                    "I am a bot: not a real human user. If I am misbehaving " +
                    "or you need assistance, please contact @Antonbury.\n\n" +
                    "Available commands:\n\n" +
                    "\n\n".join(command_list))

    HabiticaMessager(HEADER).send_private_message(message.from_id, response)
    HabiticaMessager.set_reaction_pending(message, False)


def requires_party_membership(act_function):
    """
    Wrapper for `act` functions that can only be used by party members.

    If a non-member tries to use a command with this decorator, they
    get an error message instead.
    """
    def wrapper(self, message):
        partymember_uids = DBTool().get_party_user_ids()

        if message.from_id not in partymember_uids:
            # pylint: disable=protected-access
            self._logger.debug("Unauthorized %s request from %s",
                               message.content.strip().split()[0],
                               message.from_id)
            return ("This command is usable only by people within the "
                    "party. No messages sent.")
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
                "{}\n"
                "```\n"
                "---\n\n"
                "New description:\n\n"
                "{}"
                "".format(old_description, new_description))

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
                                   "wiki page {} failed: {} queue candidates "
                                   "found.".format(conf.PARTY_WIKI_URL,
                                                   len(ols)))
        quest_queue_items = ["{}. {}".format(i, li.text)
                             for i, li in enumerate(ols[0].getchildren())]

        current_time = datetime.datetime.now(datetime.timezone.utc)
        quest_queue_lines = (
                ["The Quest Queue (as in Wiki on {}):\n"
                 "".format(current_time.strftime("%b %d at %H:%M UTC%z"))]
                + quest_queue_items)
        return "\n".join(quest_queue_lines)

    def _replace_quest_queue(self, old_description, new_queue):
        """
        Return the old description with everything in it starting with "The
        Quest queue" replaced with the given new_queue.
        """
        # pylint: disable=no-self-use
        return old_description.split("The Quest Queue ")[0] + new_queue


class QuestList(Functionality):
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
                "https://habitica.com/api/v3/members/{}".format(member_uid))
            quest_counts = member_data["items"]["quests"]
            for quest_name in quest_counts:
                count = quest_counts[quest_name]
                if count == 1:
                    partymember_str = "@{}".format(member_name)
                elif count >= 1:
                    partymember_str = ("@{user} ({count})"
                                       "".format(user=member_name,
                                                 count=count))
                else:
                    continue

                if quest_name in quests:
                    quests[quest_name] = ", ".join([quests[quest_name],
                                                    partymember_str])
                else:
                    quests[quest_name] = partymember_str

        content_lines = ["- **{}**: {}".format(quest, quests[quest])
                         for quest in quests]
        return "\n".join(content_lines)


class PartyNewsletter(Functionality):
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
        return ("Send an identical message to all party members."
                "\n\n"
                "For example the following command:\n"
                "```\n"
                "party-newsletter"
                "\n\n"
                "{example_content}\n"
                "```\n"
                "will send the following message to all party members:\n"
                "{example_result}"
                "".format(
                    example_content=example_content,
                    example_result=self._format_newsletter(example_content,
                                                           "YourUsername"))
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

        recipient_list_str = "\n".join(["- @{}".format(name)
                                        for name in recipients])
        self._logger.debug("A newsletter sent to %d party members",
                           len(recipients))
        return ("Sent the given newsletter to the following users:\n"
                "{}".format(recipient_list_str))

    def _format_newsletter(self, message, sender_name):
        """
        Return the given message with a standard footer appended.

        The footer tells who originally sent the newsletter and urges people to
        contact the admin if the bot is misbehaving.
        """
        return ("{message}"
                "\n\n---\n\n"
                "This is a party newsletter written by @{user} and "
                "brought you by the party bot. If you suspect you should "
                "not have received this message, please contact "
                "@{admin}."
                "".format(message=message,
                          user=sender_name,
                          admin=self._db_tool.get_loginname(conf.ADMIN_UID))
                )


class QuestReminders(Functionality):
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
            return ("A problem was encountered when reading the quest list: {}"
                    "\n\n"
                    "No messages were sent.".format(str(err)))

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

        return "Sent out {} quest reminders.".format(sent_reminders)

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
                        "holding the names of the participants. Line `{}` "
                        "did not match this format.".format(line)
                        )

            if not parts[0].strip():
                raise ValidationError(
                        "Problem in line `{}`: quest name cannot be empty."
                        "".format(line))

            if not first_line:
                if not parts[1].strip():
                    raise ValidationError(
                            "No quest owners listed for quest {}"
                            "".format(parts[0].strip()))

                for owner_str in parts[1].split(","):
                    owner_name = owner_str.strip().lstrip("@")
                    if not owner_name:
                        raise ValidationError(
                                "Malformed quest owner list for quest {}"
                                "".format(line))
                    try:
                        self._db_tool.get_user_id(owner_name)
                    except ValueError as err:
                        raise ValidationError(
                                "User @{} not found in the party"
                                "".format(owner_name)
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
            who = "You (and {} others)".format(n_users - 1)
        elif n_users == 2:
            who = "You (and one other partymember)"
        else:
            who = "You"
        return ("{who} have a quest coming up in the queue: {quest_name}! "
                "It comes after {previous_quest}, so when you notice that "
                "{previous_quest} has ended, please send out the invite for "
                "{quest_name}.".format(who=who,
                                       quest_name=quest_name,
                                       previous_quest=previous_quest))


class ValidationError(ValueError):
    """
    Error for cases where user input is erroneous
    """


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


class AddTask(Functionality):
    """
    Add a new task for the bot.
    """

    def __init__(self):
        """
        Initialize a HabiticaOperator in addition to normal init.
        """
        self.habitica_operator = HabiticaOperator(HEADER)
        super().__init__()

    def act(self, message):
        """
        Add task specified by the message.

        See docstring of `help` for information about the command syntax.
        """
        if not self._sender_is_admin(message):
            return "Only administrators are allowed to add new tasks."

        try:
            task_type = self._task_type(message)
            task_text = self._task_text(message)
            task_notes = self._task_notes(message)
        except ValueError as err:
            return str(err)

        self.habitica_operator.add_task(
            task_text=task_text,
            task_notes=task_notes,
            task_type=task_type,
            )

        return ("Added a new task with the following properties:\n\n"
                "```\n"
                "type: {}\n"
                "text: {}\n"
                "notes: {}\n"
                "```".format(task_type, task_text, task_notes)
                )

    def help(self):
        return ("Add a new task for the bot. The following syntax is used for "
                "new tasks: \n\n"
                "```\n"
                "    add-task [task_type]: [task name]\n\n"
                "    [task description (optional)]\n"
                "```"
                )

    def _task_type(self, message):
        """
        Parse the task type from the command in the message.
        """
        parameter_parts = self._command_body(message).split(":", 1)

        if len(parameter_parts) < 2:
            raise ValueError("Task type missing from the command, no new "
                             "tasks added. See help:\n\n" + self.help())

        return parameter_parts[0].strip()

    def _task_text(self, message):
        """
        Parse the task name from the command in the message.
        """
        command_parts = self._command_body(message).split(":", 1)[1]
        if len(command_parts) < 2 or not command_parts[1]:
            raise ValueError("Task name missing from the command, no new "
                             "tasks added. See help:\n\n" + self.help())
        return command_parts.split("\n")[0].strip()

    def _task_notes(self, message):
        """
        Parse the task description from the command in the message.

        :returns: Task description if present, otherwise None
        """
        task_text = self._command_body(message).split(":", 1)[1]
        task_text_parts = task_text.split("\n", 1)
        if len(task_text_parts) == 1:
            return None
        return task_text_parts[1].strip()


class ListBirthdays(Functionality):
    """
    Respond with a list of Habitica birthdays.
    """

    def act(self, message):
        """
        Return a response with todays birthdays.
        """
        bday_reminder = BirthdayReminder(HEADER)
        return bday_reminder.birthday_reminder_message()

    def help(self):
        """
        Return a help message.
        """
        # pylint: disable=no-self-use
        return "List party members who are celebrating their birthday today."


class SendWinnerMessage(Functionality):
    """
    Functionality for announcing sharing weekend challenge winner.
    """

    def __init__(self):
        self.partytool = habiticatool.PartyTool(HEADER)
        self.habitica_operator = HabiticaOperator(HEADER)
        super().__init__()

    def act(self, message):
        """
        Determine who should win this week's sharing weekend challenge.

        Returns a message listing the names of participants, the seed used for
        picking the winner, and the resulting winner. In case there are no
        participants, the message just states that.
        """
        challenge_id = self.partytool.current_sharing_weekend()["id"]
        challenge = Challenge(HEADER, challenge_id)
        completer_str = challenge.completer_str()
        try:
            stock_day = utils.last_weekday_date(STOCK_DAY_NUMBER)
            winner_str = challenge.winner_str(stock_day, STOCK_NAME)

            response = completer_str + "\n\n" + winner_str
        except ValueError:
            response = (completer_str + "\n\nNobody completed the challenge, "
                        "so winner cannot be chosen.")

        self.habitica_operator.tick_task(WINNER_PICKED, task_type="habit")
        return response

    def help(self):
        return ("List participants for the current sharing weekend challenge "
                "and declare a winner from amongst them. The winner is chosen "
                "using stock data as a source of randomness.")


class CreateNextSharingWeekend(Functionality):
    """
    A class for creating the next sharing weekend challenge.
    """

    def act(self, message, scheduled_run=False):
        """
        Create a new sharing weekend challenge and return a report.
        """
        # pylint: disable=arguments-differ

        if not scheduled_run and not self._sender_is_admin(message):
            return "Only administrators are allowed to create new challenges."

        tasks_path = "data/sharing_weekend_static_tasks.yml"
        questions_path = "data/weekly_questions.yml"
        self._logger.debug("create-next-sharing-weekend: tasks from %s, "
                           "weekly question from %s",
                           tasks_path, questions_path)

        operator = SharingChallengeOperator(HEADER)
        update_questions = True

        try:
            challenge = operator.create_new()
            operator.add_tasks(challenge.id, tasks_path, questions_path,
                               update_questions=update_questions)
        except:  # noqa: E722  pylint: disable=bare-except
            self._logger.error("Challenge creation failed", exc_info=True)
            return ("New challenge creation failed. Contact @Antonbury for "
                    "help.")

        challenge_url = (
                "https://habitica.com/challenges/{}".format(challenge.id))
        return ("A new sharing weekend challenge as available for joining: "
                "[{url}]({url})".format(url=challenge_url))

    def help(self):
        return ("Create a new sharing weekend challenge. No customization is "
                "currently available: the challenge is created with default "
                "parameters to the party the bot is currently in.")


class AwardWinner(Functionality):
    """
    A class for awarding a winner for a sharing weekend challenge.
    """

    def __init__(self):
        self.partytool = habiticatool.PartyTool(HEADER)
        self.habitica_operator = HabiticaOperator(HEADER)
        super().__init__()

    def act(self, message, scheduled_run=False):
        """
        Award a winner for the newest sharing weekend challenge.

        This operation is allowed only for administrators.

        :scheduled_run: Boolean: when True, message sender is not checked.
        """
        # pylint: disable=arguments-differ

        if not scheduled_run and not self._sender_is_admin(message):
            return "Only administrators are allowed to end challenges."

        challenge_id = self.partytool.current_sharing_weekend()["id"]
        challenge = Challenge(HEADER, challenge_id)
        today = datetime.date.today()
        stock_date = (today
                      - datetime.timedelta(today.weekday() - STOCK_DAY_NUMBER))
        winner = challenge.random_winner(stock_date, STOCK_NAME)
        challenge.award_winner(winner.id)
        return ("Congratulations are in order for {}, the lucky winner of {}!"
                "".format(winner, challenge.name))

    def help(self):
        return ("Award a stock data determined winner for the newest sharing "
                "weekend challenge.")
