"""
Interface for reading and writing YAML files
"""

from collections import OrderedDict

import yaml

from habitica_helper.task import Task


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
        with open(filename, encoding="utf8") as taskfile:
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
        with open(filename, encoding="utf8") as questionfile:
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
                            f"malformed:\n{question}",
                            filename) from key_error

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
        with open(filename, "w", encoding="utf8") as dest:
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
        message = (f"Problem with question file \"{filename}\":\n\n"
                   f"{problem}\n\n"
                   f"{self._INFO}")
        super().__init__(message)
