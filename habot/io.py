"""
Communications with non-API external entities.

Currently this means interacting via private messages in Habitica.
"""

from collections import OrderedDict
from datetime import datetime
import requests
import yaml

from habitica_helper.habiticatool import PartyTool
from habitica_helper.task import Task
from habitica_helper.utils import get_dict_from_api, timestamp_to_datetime

from conf.tasks import PM_SENT
from habot.db import DBOperator
from habot.exceptions import CommunicationFailedException
from habot.habitica_operations import HabiticaOperator
import habot.logger
from habot.message import PrivateMessage, ChatMessage, SystemMessage


class HabiticaMessager():
    """
    A class for handling Habitica private messages.
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

    def send_private_message(self, to_uid, message):
        """
        Send a private message with the given content to the given user.

        After a message has been successfully sent, the bot ticks its PM
        sending habit.

        :to_uid: Habitica user ID of the recipient
        :message: The contents of the message
        """
        api_url = "https://habitica.com/api/v3/members/send-private-message"
        response = requests.post(api_url, headers=self._header,
                                 data={"message": message, "toUserId": to_uid})
        if response.status_code != 200:
            raise CommunicationFailedException(response)

        self._habitica_operator.tick_task(PM_SENT, task_type="habit")

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
                    "info_value": value,
                    }
                existing_info = self._db.query_table_based_on_dict(
                    "system_message_info", info_data)
                if not existing_info:
                    self._db.insert_data("system_message_info", info_data)
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
            self._logger.debug("new chat message: message.from_id = %s",
                               chat_message.from_id)
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

    def get_private_messages(self):
        """
        Fetch private messages using Habitica API.

        If there are new messages, they are written to the database and
        returned.

        No paging is implemented: all new messages are assumed to fit into the
        returned data from the API.
        """
        message_data = get_dict_from_api(
            self._header, "https://habitica.com/api/v3/inbox/messages")

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
        self._ensure_db()
        self._db.update_row("private_messages", message.message_id,
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

    def update_partymember_data(self):
        """
        Fetch current party member data from Habitica and update the database.

        If the database contains members that are not currently in the party,
        they are removed from the database.
        """
        partytool = PartyTool(self._header)
        partymembers = partytool.party_members()

        self.add_new_members(partymembers)
        self.remove_old_members(partymembers)

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
        super(MalformedQuestionFileException, self).__init__(message)
