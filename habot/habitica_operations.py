"""
Perform "normal" habitica operations, e.g. tick a habit.
"""

import requests.exceptions

from habitica_helper.utils import get_dict_from_api
from habitica_helper import habrequest
from habitica_helper.task import Task

from habot.exceptions import CommunicationFailedException
import habot.logger


class HabiticaOperator():
    """
    A class that is able to do things that a human user would normally use
    Habitica for.
    """

    def __init__(self, header):
        self._header = header
        self._logger = habot.logger.get_logger()

    def _get_user_data(self):
        """
        Return the full user data dict.
        """
        url = "https://habitica.com/api/v3/user"
        return get_dict_from_api(self._header, url)

    def _get_tasks(self, task_type=None):
        """
        Return a list of tasks.

        If task_type is given, only tasks of that type are returned.

        :task_type: None (for all tasks) or a Habitica task type ("habit",
                    "daily", or "todo)
        """
        if task_type not in ["habit", "daily", "todo", None]:
            raise ValueError("Task type {} not supported".format(task_type))

        url = "https://habitica.com/api/v3/tasks/user"
        tasks = get_dict_from_api(self._header, url)

        if task_type is None:
            return tasks

        matching_tasks = [task for task in tasks if task["type"] == task_type]
        return matching_tasks

    def find_task(self, task_text, task_type=None):
        """
        Find a task with its name containing the given task_text.

        :task_text: A string that should be found in the task name and uniquely
                    identify a single task.
        :task_type: If given, only tasks of that type ("habit"/"daily"/"todo")
                    are considered when looking for a matching task.
        :returns: A dict representing the found task.

        :raises:
            NotFoundException: when a matching task is not found
        """
        all_tasks = self._get_tasks(task_type=task_type)

        matching_task = None
        for task in all_tasks:
            if task_text in task["text"]:
                if not matching_task:
                    matching_task = task
                else:
                    raise AmbiguousOperationException(
                        "Task text {} doesn't identify a unique task"
                        "".format(task_text))

        if not matching_task:
            raise NotFoundException("Task with text {} not found"
                                    "".format(task_text))

        return matching_task

    def add_task(self, task_text, task_notes=None, task_type="todo"):
        """
        Add a new task for the bot.

        :task_text: The name of the task
        :task_notes: Optional additional description for the task
        :task_type: Type of the task. Allowed values are "habit", "daily" and
                    "todo".
        :returns: the added Task
        """
        task_data = {
            "text": task_text,
            "notes": task_notes,
            "tasktype": task_type,
            }
        task = Task(task_data)
        task.add_to_user(self._header)
        return task

    def tick_task(self, task_text, direction="up", task_type=None):
        """
        Tick a task as done.

        :task_text: A string that should be found in the task name and uniquely
                    identify a single task.
        :direction: Used for ticking habits with plus and minus options.
                    Allowed values are "up" and "down", defaults to "up".
        :task_type: If given, only tasks of that type ("habit"/"daily"/"todo")
                    are considered when looking for a matching task.
        :raises:
            NotFoundException: when a matching task is not found
            CommunicationFailedException: when Habitica answers with non-200
                                          status
        """
        task = self.find_task(task_text, task_type=task_type)

        tick_url = ("https://habitica.com/api/v3/tasks/{}/score/{}"
                    "".format(task["_id"], direction))
        try:
            habrequest.post(tick_url, headers=self._header)
        # pylint: disable=invalid-name
        except requests.exceptions.HTTPError as e:
            # pylint: disable=raise-missing-from
            raise CommunicationFailedException(str(e))

    def join_quest(self):
        """
        If there's an unjoined quest, join it.

        :return: True if a quest was joined.
        """
        self._logger.debug("Checking if a quest can be joined.")
        questdata = get_dict_from_api(
            self._header,
            "https://habitica.com/api/v3/groups/party")["quest"]
        self._logger.debug("Quest information: %s", questdata)
        if ("key" in questdata and
                not questdata["active"] and (
                    self._header["x-api-user"] not in questdata["members"]
                    or not questdata["members"][self._header["x-api-user"]])):
            self._logger.debug("New quest found")
            try:
                habrequest.post(
                    "https://habitica.com/api/v3/groups/party/quests/accept",
                    headers=self._header)
            # pylint: disable=invalid-name
            except requests.exceptions.HTTPError as e:
                self._logger.error("Quest joining failed: %s", str(e))
                # pylint: disable=raise-missing-from
                raise CommunicationFailedException(str(e))
            self._logger.info("Joined quest %s", questdata["key"])
            return True
        return False

    def cron(self):
        """
        Run cron.
        """
        habrequest.post("https://habitica.com/api/v3/cron",
                        headers=self._header)
        self._logger.debug("Cron run successful.")


class AmbiguousOperationException(Exception):
    """
    Exception for situations where a request is not clear.
    """


class NotFoundException(Exception):
    """
    Exception for when a matching object is not found.
    """
