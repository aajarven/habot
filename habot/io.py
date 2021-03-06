"""
Communications with non-API external entities.

Currently this means interacting via private or party messages in Habitica.
"""

from collections import OrderedDict
from datetime import datetime
from io import StringIO
from lxml import etree
import requests.exceptions
import yaml

from habitica_helper.habiticatool import PartyTool
from habitica_helper.task import Task
from habitica_helper.utils import get_dict_from_api, timestamp_to_datetime
from habitica_helper import habrequest

from conf.tasks import PM_SENT, GROUP_MSG_SENT
from habot.db import DBOperator
from habot.exceptions import CommunicationFailedException
from habot.habitica_operations import HabiticaOperator
import habot.logger
from habot.message import PrivateMessage, ChatMessage, SystemMessage


class DBTool():
    """
    High-level tools for using the database.
    """
    # pylint: disable=too-few-public-methods

    def __init__(self):
        """
        Initialize the class
        """
        self._logger = habot.logger.get_logger()
        self._db = DBOperator()

    def get_user_id(self, habitica_loginname):
        """
        Return the user ID of a party member corresponding to given login name.
        """
        members = self._db.query_table(
            "members",
            condition="loginname='{}'".format(habitica_loginname),
            columns="id",
            )
        if not members:
            raise ValueError("User with login name {} not found"
                             "".format(habitica_loginname))
        return members[0]["id"]

    def get_party_user_ids(self):
        """
        Return a list of user IDs for all party members.
        """
        members = self._db.query_table(
            "members",
            columns="id",
            )
        return [data_dict["id"] for data_dict in members]

    def get_loginname(self, uid):
        """
        Return the login name of the party member with the given UID.
        """
        members = self._db.query_table(
            "members",
            condition="id='{}'".format(uid),
            columns="loginname",
            )
        if not members:
            raise ValueError("User with user ID {} not found"
                             "".format(uid))
        return members[0]["loginname"]


class HabiticaMessager():
    """
    A class for handling Habitica messages (private and party).
    """

    def __init__(self, header):
        """
        Initialize the class.

        Database operator is not created at init, because all operations don't
        need one.

        :header: Habitica requires specific fields to be present in all API
                 calls. This must be a dict containing them.
        """
        self._header = header
        self._habitica_operator = HabiticaOperator(header)
        self._logger = habot.logger.get_logger()
        self._db = None

    def _ensure_db(self):
        """
        Make sure that a database operator is available
        """
        if not self._db:
            self._db = DBOperator()

    def _split_long_message(self, message, max_length=3000):
        """
        If the given message is too long, split it into multiple messages.

        If the message is shorter than the given max_length, the returned list
        will just contain the original message. Otherwise the message is split
        into parts, each shorter than the given max_length. Splitting is only
        done at newlines.

        :message: String containing the message body
        :max_length: Maximum length for one message. Default 3000.
        :raises: `UnsplittableMessage` if the message contains a paragraph that
                 is longer than `max_length` and thus cannot be split at a
                 newline.
        :returns: A list of strings, each string containing one piece of the
                  given message.
        """
        # pylint: disable=no-self-use

        if len(message) < max_length:
            return [message]

        split_at = "\n"
        messages = []
        while len(message) > max_length:
            split_index = message.find(split_at)
            if split_index > max_length or split_index == -1:
                raise UnsplittableMessage("Cannot find a legal split "
                                          "location in the following part "
                                          "of an outgoing message:\n"
                                          "{}".format(message))
            while split_index != -1:
                next_split_candidate = message.find(split_at, split_index + 1)
                if (next_split_candidate > max_length
                        or next_split_candidate == -1):
                    break
                split_index = next_split_candidate
            messages.append(message[:split_index])
            message = message[split_index+1:]
        messages.append(message)
        return messages

    def send_private_message(self, to_uid, message):
        """
        Send a private message with the given content to the given user.

        After a message has been successfully sent, the bot ticks its PM
        sending habit.

        :to_uid: Habitica user ID of the recipient
        :message: The contents of the message
        """
        api_url = "https://habitica.com/api/v3/members/send-private-message"
        message_parts = self._split_long_message(message)
        if len(message_parts) > 3:
            raise SpamDetected("Sending {} messages at once is not supported."
                               "".format(len(message_parts)))
        for message_part in message_parts:
            try:
                habrequest.post(api_url, headers=self._header,
                                data={"message": message_part,
                                      "toUserId": to_uid})
            #  pylint: disable=invalid-name
            except requests.exceptions.HTTPError as e:
                #  pylint: disable=raise-missing-from
                raise CommunicationFailedException(str(e))

        self._habitica_operator.tick_task(PM_SENT, task_type="habit")

    def send_group_message(self, group_id, message):
        """
        Send a message with the given content to the given group.

        :group_id: UUID of the recipient group, or 'party' for current party of
                   the bot.
        :message: Contents of the message to be sent
        """
        api_url = "https://habitica.com/api/v3/groups/{}/chat".format(group_id)
        try:
            habrequest.post(api_url, headers=self._header,
                            data={"message": message})
        #  pylint: disable=invalid-name
        except requests.exceptions.HTTPError as e:
            #  pylint: disable=raise-missing-from
            raise CommunicationFailedException(str(e))
        self._habitica_operator.tick_task(GROUP_MSG_SENT, task_type="habit")

    def get_party_messages(self):
        """
        Fetches party messages and stores them into the database.

        Both system messages (e.g. boss damage) and chat messages (sent by
        habiticians) are stored.
        """
        message_data = get_dict_from_api(
            self._header, "https://habitica.com/api/v3/groups/party/chat")
        messages = [None] * len(message_data)
        for i, message_dict in zip(range(len(message_data)), message_data):
            if "user" in message_dict:
                messages[i] = ChatMessage(
                    message_dict["uuid"], message_dict["groupId"],
                    content=message_dict["text"],
                    message_id=message_dict["id"],
                    timestamp=datetime.utcfromtimestamp(
                        # Habitica saves party chat message times as unix time
                        # with three extra digits for milliseconds (no
                        # decimal separator)
                        message_dict["timestamp"]/1000),
                    likers=self._marker_list(message_dict["likes"]),
                    flags=self._marker_list(message_dict["flags"]))
            else:
                messages[i] = SystemMessage(
                    message_dict["groupId"],
                    datetime.utcfromtimestamp(
                        # Habitica saves party chat message times as unix time
                        # with three extra digits for milliseconds (no
                        # decimal separator)
                        message_dict["timestamp"]/1000),
                    content=message_dict["text"],
                    message_id=message_dict["id"],
                    likers=self._marker_list(message_dict["likes"]),
                    info=message_dict["info"]
                    )
        self._logger.debug("Fetched %d messages from Habitica API",
                           len(messages))

        new_messages = 0
        for message in messages:
            if isinstance(message, SystemMessage):
                new = self._write_system_message_to_db(message)
            elif isinstance(message, ChatMessage):
                new = self._write_chat_message_to_db(message)
            else:
                raise ValueError("Unexpected message type received from API")
            new_messages += 1 if new else 0
        self._logger.debug("%d new chat/system messages written to the "
                           "database", new_messages)

    def _write_system_message_to_db(self, system_message):
        """
        Add a system message to the database if not already there.

        In addition to writing the core message data, contents of the `info`
        dict are also written into their own table. All values within this
        dict, including e.g. nested dicts and integers, are coerced to strings.

        System messages can also be liked: these likes are written into `likes`
        table.

        :system_message: SystemMessage to be written to the database
        :returns: True if a new message was added to the database
        """
        self._ensure_db()
        existing_message = self._db.query_table(
            "system_messages",
            condition="id='{}'".format(system_message.message_id))
        if not existing_message:
            for key, value in system_message.info.items():
                info_data = {
                    "message_id": system_message.message_id,
                    "info_key": key,
                    "info_value": str(value),
                    }
                existing_info = self._db.query_table_based_on_dict(
                    "system_message_info", info_data)
                if not existing_info:
                    self._db.insert_data("system_message_info", info_data)
            for liker in system_message.likers:
                self._write_like(system_message.message_id, liker)
            message_data = {
                "id": system_message.message_id,
                "to_group": system_message.group_id,
                "timestamp": system_message.timestamp,
                "content": system_message.content,
                }
            self._db.insert_data("system_messages", message_data)
            return True
        return False

    def _write_chat_message_to_db(self, chat_message):
        """
        Add a chat message to the database if not already there.

        At this point, all chat messages are marked as not requiring a
        reaction.

        :chat_message: ChatMessage to be written to the database
        :returns: True if a new message was added to database, otherwise False
        """
        self._ensure_db()
        existing_message = self._db.query_table(
            "chat_messages",
            condition="id='{}'".format(chat_message.message_id))
        if not existing_message:
            for liker in chat_message.likers:
                self._write_like(chat_message.message_id, liker)
            for flagger in chat_message.flags:
                self._write_like(chat_message.message_id, flagger)
            db_data = {
                "id": chat_message.message_id,
                "from_id": chat_message.from_id,
                "to_group": chat_message.group_id,
                "content": chat_message.content,
                "timestamp": chat_message.timestamp,
                "reaction_pending": 0,
                }
            self._db.insert_data("chat_messages", db_data)
            return True
        return False

    def _marker_list(self, user_dict):
        """
        Return a list of users who have liked/flagged a message.

        This list is parsed from the given user_dict, which has UIDs as keys
        and True/False as the value depending on whether the given user has
        marked that message as liked/flagged. This is the format Habitica
        reports likes for party messages.
        """
        # pylint: disable=no-self-use
        return [uid for uid in user_dict if user_dict[uid]]

    def _write_like(self, message_id, user_id):
        """
        Add information about a person liking a message into the db.

        If the row already exists, it is not inserted again.

        :message_id: The liked message
        :user_id: The person who hit the like button
        """
        self._ensure_db()
        like_dict = {"message": message_id, "user": user_id}
        existing_like = self._db.query_table_based_on_dict("likes", like_dict)
        if not existing_like:
            self._db.insert_data("likes", like_dict)

    def _write_flag(self, message_id, user_id):
        """
        Add information about a person reporting a message into the db.

        If the row already exists, it is not inserted again.

        :message_id: The reported message
        :user_id: The person who reported the message
        """
        self._ensure_db()
        flag_dict = {"message": message_id, "user": user_id}
        existing_flag = self._db.query_table_based_on_dict("flags", flag_dict)
        if not existing_flag:
            self._db.insert_data("flags", flag_dict)

    def get_private_messages(self):
        """
        Fetch private messages using Habitica API.

        If there are new messages, they are written to the database and
        returned.

        No paging is implemented: all new messages are assumed to fit into the
        returned data from the API.
        """
        try:
            message_data = get_dict_from_api(
                self._header, "https://habitica.com/api/v3/inbox/messages")
        except requests.exceptions.HTTPError as err:
            raise CommunicationFailedException(err.response) from err

        messages = [None] * len(message_data)
        for i, message_dict in zip(range(len(message_data)), message_data):
            if message_dict["sent"]:
                recipient = message_dict["uuid"]
                sender = message_dict["ownerId"]
            else:
                recipient = message_dict["ownerId"]
                sender = message_dict["uuid"]
            messages[i] = PrivateMessage(
                sender, recipient,
                timestamp=timestamp_to_datetime(message_dict["timestamp"]),
                content=message_dict["text"],
                message_id=message_dict["id"])
        self._logger.debug("Fetched %d messages from Habitica API",
                           len(messages))
        self.add_PMs_to_db(messages)

    def add_PMs_to_db(self, messages):
        """
        Write all given private messages to the database.

        New messages not sent by this user are marked as
        reaction_pending=True if they have not already been responded to (i.e.
        a newer message sent to the same user is present in the database).
        If none of the given messages are present in the database, returns
        True to signal that fetching more messages might be necessary.
        Otherwise returns False.

        :messages: `PrivateMessage`s to be added to the database
        :returns: True if all of the messages were new (not already in the db),
                  otherwise False
        """
        # pylint: disable=invalid-name
        self._ensure_db()
        all_new = True
        for message in messages:
            existing_message = self._db.query_table(
                "private_messages",
                condition="id='{}'".format(message.message_id))
            if not existing_message:
                self._logger.debug("message.from_id = %s", message.from_id)
                self._logger.debug("id of x-api-user: %s",
                                   self._header["x-api-user"])
                if (message.from_id == self._header["x-api-user"] or
                        self._has_newer_sent_message_in_db(message.from_id,
                                                           message.timestamp)):
                    reaction_pending = 0
                else:
                    reaction_pending = 1
                self._logger.debug("Adding new message to the database: '%s', "
                                   "reaction_pending=%d", message.excerpt(),
                                   reaction_pending)
                db_data = {
                    "id": message.message_id,
                    "from_id": message.from_id,
                    "to_id": message.to_id,
                    "content": message.content,
                    "timestamp": message.timestamp,
                    "reaction_pending": reaction_pending,
                    }
                self._db.insert_data("private_messages", db_data)
            else:
                all_new = False
        return all_new

    @classmethod
    def set_reaction_pending(cls, message, reaction):
        """
        Set reaction_pending field in the DB for a given message.

        :message: A Message for which database is altered
        :reaction: True/False for reaction pending
        """
        db = DBOperator()
        db.update_row("private_messages", message.message_id,
                      {"reaction_pending": reaction})

    def _has_newer_sent_message_in_db(self, to_id, timestamp):
        """
        Return True if `to_id` has been sent a message after `timestamp`.

        This is checked from the database, so if a message has not yet been
        processed into the DB, it won't affect the result. However, if the
        messages are processed from newest to oldest, this function can be used
        to determine if a "new" message has already been responded to.

        :to_id: Habitica user UID
        :timestamp: datetime after which to look for messages
        """
        self._ensure_db()
        sent_messages = self._db.query_table(
            "private_messages",
            condition="timestamp>'{}' AND to_id='{}'".format(timestamp, to_id))
        if sent_messages:
            return True
        return False


class DBSyncer():
    """
    Fetch data from Habitica API and write it to the database.
    """

    def __init__(self, header):
        """
        :header: Habitica API call header for a party member
        """
        self._header = header
        self._db = DBOperator()
        self._logger = habot.logger.get_logger()

    def update_partymember_data(self):
        """
        Fetch current party member data from Habitica and update the database.

        If the database contains members that are not currently in the party,
        they are removed from the database.
        """
        self._logger.debug("Going to update partymember data in the DB.")
        partytool = PartyTool(self._header)
        partymembers = partytool.party_members()

        self.add_new_members(partymembers)
        self._logger.debug("Added new members")
        self.remove_old_members(partymembers)
        self._logger.debug("Removed outdated members")

    def remove_old_members(self, partymembers):
        """
        Remove everyone who is not a current party member from "members" table.

        :partymembers: A complete list of current party members.
        """
        member_ids_in_party = [member.id for member in partymembers]
        members_in_db = self._db.query_table("members", "id")
        for member in members_in_db:
            if member["id"] not in member_ids_in_party:
                self._db.delete_row("members", "id", member["id"])

    def add_new_members(self, partymembers):
        """
        Update the database to contain data for all given party members.

        If someone is missing entirely, they are added, or if someone's
        information has changed (e.g. displayname), the corresponding row is
        updated.
        """
        for member in partymembers:
            db_data = {
                "id": member.id,
                "displayname": member.displayname,
                "loginname": member.login_name,
                "birthday": member.habitica_birthday,
                }
            user_row = self._db.query_table(
                "members", condition="id='{}'".format(member.id))
            if len(user_row) == 0:
                self._db.insert_data("members", db_data)
            elif user_row != db_data:
                self._db.update_row("members", member.id, db_data)


class YAMLFileIO():
    """
    Read and write YAML files in a way that benefits the bot.
    """

    @classmethod
    def read_tasks(cls, filename):
        """
        Create tasks representing the ones in the file.

        The input file must be a YAML file, containing a list of dicts, each of
        them representing one task. Each task must have keys "text" and
        "tasktype", and may also contain any of the following: "notes", "date",
        "difficulty", "uppable" and "downable".

        :returns: A list of tasks
        """
        tasks = []
        with open(filename) as taskfile:
            file_contents = yaml.load(taskfile, Loader=yaml.BaseLoader)
            for taskdict in file_contents:
                # TODO error handling
                tasks.append(Task(taskdict))
        return tasks

    @classmethod
    def read_question_list(cls, filename, unused_only=False):
        """
        Parse a YAML file containing weekly questions.

        The expected syntax for the file is that it contains a list
        "questions", each item of which is a dict with keys "question",
        "description" and "used". For example

        questions:
          - question: What is your favourite fruit?
            description: Do you like bananas or apples more? Or maybe kiwis?
            used: True
          - question: What is your favourite animal?
            description: The only real answer here is labrador though =3
            used: False

        is a valid question list file.

        :returns: An OrderedDict of Tasks. Only the text, tasktype and notes
                  are set for the task, everything else has to be added later.
                  The value for each task is a boolean that denotes if the task
                  was marked as being used already.
        """
        with open(filename) as questionfile:
            file_contents = yaml.load(questionfile, Loader=yaml.BaseLoader)
            try:
                questions = file_contents["questions"]
            except KeyError as key_error:
                raise \
                    MalformedQuestionFileException(
                        "The question file doesn't seem to contain a question "
                        "list", filename) \
                    from key_error
            question_tasks = OrderedDict()
            for question in questions:
                try:
                    if unused_only and question["used"].lower() == "true":
                        continue

                    task_data = {
                        "text": question["question"],
                        "tasktype": "todo",
                        "notes": question["description"],
                        }
                    question_tasks[Task(task_data)] = (
                        question["used"].lower() == "true")
                except KeyError as key_error:
                    raise \
                        MalformedQuestionFileException(
                            "The following question in the question list is "
                            "malformed:\n{}".format(question),
                            filename) \
                        from key_error

            return question_tasks

    @classmethod
    def write_question_list(cls, questions, filename):
        """
        Save all questions as YAML into the given file.

        The given questions must be a dict, keys of which are Tasks and values
        booleans determining whether that question has already been used.

        questions:
          - question: What is your favourite fruit?
            description: Do you like bananas or apples more? Or maybe kiwis?
            used: True
          - question: What is your favourite animal?
            description: The only real answer here is labrador though =3
            used: False

        :questions: A dict of Habitica tasks and booleans telling whether they
                    have already been used in some previous challenge.
        :filename: The output file.
        """
        question_data = []
        for question in questions:
            question_data.append({
                "question": question.text,
                "description": question.notes,
                "used": questions[question]})
        with open(filename, "w") as dest:
            yaml.dump({"questions": question_data}, dest,
                      default_flow_style=False)


class WikiReader():
    """
    Tool for fetching content of a page from Habitica wiki.
    """

    def __init__(self, url):
        """
        Initialize the object

        :url: String containing url to the page, e.g.
              "https://habitica.fandom.com/wiki/The_Keep:Mental_Health_Warriors_Unite".
        """
        self.url = url
        self._parser = etree.HTMLParser()
        self._page = None

    class Decorators():
        """
        Decorators used by WikiReader
        """
        # pylint: disable=too-few-public-methods

        @classmethod
        def needs_page(cls, method):
            """
            Decorator for functions that need the page to be fetched
            """
            def _decorated(*args, **kwargs):
                # pylint: disable=protected-access
                if not args[0]._page:
                    args[0]._read_page()
                return method(*args, **kwargs)
            return _decorated

    def _read_page(self):
        """
        Fetch the page from the wiki.

        :raise:
            :HTTPError: if the page cannot be fetched
            :WikiParsingError: if the page content cannot be found
        """
        response = requests.get(self.url)
        response.raise_for_status()
        full_page_tree = etree.parse(StringIO(str(response.content)),
                                     self._parser)
        content = full_page_tree.getroot().cssselect(".WikiaPage")
        if len(content) != 1:
            raise WikiParsingError("More than one `WikiaPage` element "
                                   "encountered")
        self._page = content[0]

    @property
    @Decorators.needs_page
    def page(self):
        """
        Return the HTML contents of the page as lxml ElementTree.
        :returns: lxml Element corresponding to the root node of the wiki page
                  content.
        """
        return self._page

    @Decorators.needs_page
    def find_elements_with_matching_subelement(self, element_selector,
                                               child_text):
        """
        Return a list of elements of given type that have a matching children.

        The given `child_text` must only be present in one of the children
        elements: it is not necessary for it to be the full content of the
        element.

        :element_selector: CSS selector for finding the elements. E.g. `div` or
                           `#someid` or `ul.navigation`.
        :child_text: A string that must be found in the content of at least one
                     of the child elements.
        :returns: A list of lxml ElementTrees, each startig from an element
                  that matched the search criteria.
        """
        css_matching_elements = self._page.cssselect(element_selector)
        full_match_elements = []
        for element in css_matching_elements:
            for child in element.iterchildren():
                if child.text and child_text in child.text:
                    full_match_elements.append(element)
        return full_match_elements


class MalformedQuestionFileException(Exception):
    """
    Exception raised when the question list cannot be parsed.

    Has the following attributes:
    :problem: A short description of the problem
    :filename: The problematic file
    :message: A custom extra message
    """

    _INFO = ('The expected syntax for the file is that it contains a list '
             '"questions", each item of which is a dict with keys "question", '
             '"description" and "used". For example:\n\n'
             'questions:\n'
             '  - question: What is your favourite fruit?\n'
             '    description: Do you like bananas or apples more? Or maybe '
             'kiwis?\n'
             '    used: True\n'
             '  - question: What is your favourite animal?\n'
             '    description: The only real answer here is labrador ofc =3\n'
             '    used: False\n\n'
             'is a valid question list file.')

    def __init__(self, problem, filename):
        message = ("Problem with question file \"{}\":\n\n{}\n\n{}"
                   "".format(filename, problem, self._INFO))
        super().__init__(message)


class UnsplittableMessage(Exception):
    """
    Exception raised when splitting a too long message is not possible.
    """


class SpamDetected(Exception):
    """
    Exception for situations where the spot is being used for spamming.
    """


class WikiParsingError(Exception):
    """
    Exception for unexpected content from Habitica Wiki.
    """
