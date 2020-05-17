"""
Use the bot functionality to create a sharing weekend challenge.

The challenge is created for the party of the bot account.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from habot.sharing_weekend import SharingChallengeOperator
from conf.header import HEADER

op = SharingChallengeOperator(HEADER)
op.create_new()
