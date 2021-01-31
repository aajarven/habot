"""
The static header info Habitica requires.
"""
# credentials added by user, not present always when linting
# pylint: disable=no-name-in-module,import-error
from conf.secrets.habitica_credentials import (
    PLAYER_USER_ID, PLAYER_API_TOKEN,
)

HEADER = {
    "x-client":
        "f687a6c7-860a-4c7c-8a07-9d0dcbb7c831-habot",
    "x-api-user": PLAYER_USER_ID,
    "x-api-key":  PLAYER_API_TOKEN,
}
