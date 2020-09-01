"""
Perform "normal" habitica operations, e.g. tick a habit.
"""

import requests

from habitica_helper.utils import get_dict_from_api

from habot.exceptions import CommunicationFailedException
import habot.logger


class HabiticaOperator(object):
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
        response = requests.post(tick_url, headers=self._header)
        if response.status_code != 200:
            raise CommunicationFailedException(response)

    def join_quest(self):
        """
        If there's an unjoined quest, join it.

        :return: True if a quest was joined.
        """
        self._logger.debug("Checking if a quest can be joined.")
        partydata = get_dict_from_api(
            self._header,
            "https://habitica.com/api/v3/groups/party")
        if (partydata["quest"]["key"] and not partydata["quest"]["active"] and
                not partydata["quest"]["members"][self._header["x-api-user"]]):
            self._logger.debug("New quest found")
            response = requests.post(
                "https://habitica.com/api/v3/groups/party/quests/accept",
                headers=self._header)
            if response.status_code != 200:
                self._logger.error("Quest joining failed: %s", response.text)
                raise CommunicationFailedException(response)
            self._logger.info("Joined quest %s", partydata["quest"]["key"])
            return True
        return False


class AmbiguousOperationException(Exception):
    """
    Exception for situations where a request is not clear.
    """


class NotFoundException(Exception):
    """
    Exception for when a matching object is not found.
    """
