"""
Logging functionality. Configuration in `conf/logging.conf`.
"""

import os
import logging
import logging.config


def get_logger():
    """
    Return a standard logger for logging bot actions.

    If log directory did not exist, it is created. NB: the log directory is
    hard-coded, so if it is changed in the configuration, the directory is
    still created here.
    """
    if not os.path.isdir("logs"):
        os.makedirs("logs")
    logging.config.fileConfig("conf/logging.conf")
    logger = logging.getLogger("habotLogger")
    return logger
