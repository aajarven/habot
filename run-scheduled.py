"""
"""  # TODO

import time

import schedule

from conf.header import HEADER
from habot.bot import handle_PMs
from habot.io import HabiticaMessager

if __name__ == "__main__":
    messager = HabiticaMessager(HEADER)
    schedule.every(1).minutes.do(messager.get_private_messages)
    schedule.every(1).minutes.do(handle_PMs)

    while True:
        schedule.run_pending()
        time.sleep(1)
