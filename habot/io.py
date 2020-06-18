"""
Communications with non-API external entities.

Currently this means interacting via private messages in Habitica.
"""

from collections import OrderedDict
import requests
import yaml

from habitica_helper.habiticatool import PartyTool
from habitica_helper.task import Task
from habitica_helper.utils import get_dict_from_api, timestamp_to_datetime

from conf.tasks import PM_SENT
from habot.db import DBOperator
from habot.exceptions import CommunicationFailedException
from habot.habitica_operations import HabiticaOperator
from habot.message import PrivateMessage


class HabiticaMessager():
    """
    A class for handling Habitica private messages.
    """

    def __init__(self, header):
        """
        Initialize the class.

        :header: Habitica requires specific fields to be present in all API
                 calls. This must be a dict containing them.
        """
        self._header = header
        self._habitica_operator = HabiticaOperator(header)

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

    def get_private_messages(self):
        """
        Fetch private messages using Habitica API.

        If there are new messages, they are written to the database and
        returned.

        No paging is implemented: all new messages are assumed to fit into the
        returned data from the API.
        """
        messages = get_dict_from_api(
            self._header, "https://habitica.com/api/v3/inbox/messages")
        messages = [PrivateMessage(
                        message["ownerId"], message["uuid"],
                        timestamp=timestamp_to_datetime(message["timestamp"]),
                        content=message["text"], message_id=message["id"])
                    for message in messages]
        self.add_PMs_to_db(messages)

    def add_PMs_to_db(self, messages):
        """
        Write all given private messages to the database.

        New messages are marked as reaction_pending=True. If none of the given
        messages are present in the database, returns True to signal that
        fetching more messages might be necessary. Otherwise returns False.

        :messages: `PrivateMessage`s to be added to the database
        :returns: True if all of the messages were new (not already in the db),
                  otherwise False
        """
        # pylint: disable=invalid-name
        db = DBOperator()
        all_new = True
        for message in messages:
            existing_message = db.query_table(
                "private_messages",
                condition="id='{}'".format(message.message_id))
            if not existing_message:
                db_data = {
                    "id": message.message_id,
                    "from_id": message.from_id,
                    "to_id": message.to_id,
                    "content": message.content,
                    "timestamp": message.timestamp,
                    "reaction_pending": 1,
                    }
                db.insert_data("private_messages", db_data)
            else:
                all_new = False
        return all_new


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
