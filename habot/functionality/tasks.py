"""
Functionality for adding new tasks for the bot
"""

from habot.functionality.base import Functionality
from habot.habitica_operations import HabiticaOperator

from conf.header import HEADER


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
                f"type: {task_type}\n"
                f"text: {task_text}\n"
                f"notes: {task_notes}\n"
                "```"
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
