"""
Shared test stuff
"""

import pytest


@pytest.fixture(autouse=True)
def prevent_external_requests(monkeypatch):
    """
    Make test crash if it tries to make a real request.
    """
    def forbidden_request(self, method, url, *args, **kwargs):
        raise RuntimeError(
            "A test attempted {} call to {}".format(method, url)
        )

    monkeypatch.setattr(
        "urllib3.connectionpool.HTTPConnectionPool.urlopen", forbidden_request
    )

