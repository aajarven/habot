"""
Test the most basic functionality, i.e. responding to a ping.
"""

from habot.functionality.base import Ping
from habot.message import PrivateMessage


def test_ping():
    """
    Ensure that the "ping" command gets "pong" back as a response.
    """
    command_msg = PrivateMessage("from_id", "to_id")
    assert Ping().act(command_msg) == "Pong"
