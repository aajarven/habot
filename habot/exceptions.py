"""
Exceptions that shared between modules
"""


class CommunicationFailedException(Exception):
    """
    An exception to be raised when communication attempt doesn't succeed.
    """
    def __init__(self, response):
        """
        Set the message from the response.

        :response: requests Response object
        """
        super().__init__(str(response))
        self.response = response
