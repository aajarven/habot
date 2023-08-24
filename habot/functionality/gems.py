"""
Functionality related to managing the gem balance of the bot.
"""

from habot.functionality.base import Functionality
from habot.habitica_operations import HabiticaOperator

from conf.header import HEADER


class GemBalance(Functionality):
    """
    Report the current gem balance in wallet
    """

    def __init__(self):
        self.habitica_operator = HabiticaOperator(HEADER)
        super().__init__()

    def act(self, message):
        """
        Report the number of gems in the bot's wallet.
        """
        return f"I have {self.habitica_operator.gem_balance()} gems"

    def help(self):
        return "Reports the number of gems currently in the bot's wallet"
