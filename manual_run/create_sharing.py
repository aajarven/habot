"""
Use the bot functionality to create a sharing weekend challenge.

The challenge is created for the party of the bot account.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from habitica_helper.task import Task

from habot.sharing_weekend import SharingChallengeOperator
from conf.header import HEADER

op = SharingChallengeOperator(HEADER)
challenge = op.create_new()
op.add_tasks(challenge.id, "data/sharing_weekend_static_tasks.yml",
                           "data/weekly_questions.yml")
#task = Task({"text": "test task", "tasktype": "todo"})
#task.create_to_challenge(challenge.id, HEADER)
