"""
Test the easily-testable parts of the challenge creation.
"""

import pytest

from freezegun import freeze_time

from habot.sharing_weekend import SharingChallengeOperator


@pytest.fixture()
def noconnect_operator():
    """
    SharingChallengeOperator without a header that would allow real requests.
    """
    return SharingChallengeOperator({})

# pylint doesn't recognize fixtures
# pylint: disable=redefined-outer-name

# we want to test private functionality
# pylint: disable=protected-access


@freeze_time("2020-05-12")
def test_challenge_name(noconnect_operator):
    """
    Test that challenge name generation works within one month.
    """
    assert (noconnect_operator._next_weekend_name() ==
            "Sharing Weekend May 16−18")


@freeze_time("2020-05-26")
def test_challenge_name_two_months(noconnect_operator):
    """
    Test that name generation when the weekend spans across two months.
    """
    assert (noconnect_operator._next_weekend_name() ==
            "Sharing Weekend May 30 − Jun 1")


@freeze_time("2020-05-17")
def test_challenge_name_on_weekend(noconnect_operator):
    """
    Test that challenge name generation works when run during a weekend
    """
    assert (noconnect_operator._next_weekend_name() ==
            "Sharing Weekend May 23−25")
