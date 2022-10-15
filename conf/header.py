"""
The static header info Habitica requires.
"""
# credentials added by user, not present always when linting
# pylint: disable=no-name-in-module,import-error
try:
    from conf.secrets.habitica_credentials import (
        PLAYER_USER_ID, PLAYER_API_TOKEN,
        PARTY_OWNER_USER_ID, PARTY_OWNER_API_TOKEN,
    )
except ImportError:
    from habot.logger import get_logger
    get_logger().error("Credential file not found. If you are trying to use "
                       "the bot instead of just running unit tests, please "
                       "see readme and properly set Habitica credentials.")
    HEADER = {
        "x-client":
            "f687a6c7-860a-4c7c-8a07-9d0dcbb7c831-habot",
        "x-api-user": "not-a-real-player-uid",
        "x-api-key":  "not-a-real-player-api-key",
    }

    PARTY_OWNER_HEADER = {
        "x-client":
            "f687a6c7-860a-4c7c-8a07-9d0dcbb7c831-habot",
        "x-api-user": "not-a-real-party-owner-uid",
        "x-api-key":  "not-a-real-party-owner-api-key",
    }
else:
    HEADER = {
        "x-client":
            "f687a6c7-860a-4c7c-8a07-9d0dcbb7c831-habot",
        "x-api-user": PLAYER_USER_ID,
        "x-api-key":  PLAYER_API_TOKEN,
    }

    PARTY_OWNER_HEADER = {
        "x-client":
            "f687a6c7-860a-4c7c-8a07-9d0dcbb7c831-habot",
        "x-api-user": PARTY_OWNER_USER_ID,
        "x-api-key":  PARTY_OWNER_API_TOKEN,
    }
