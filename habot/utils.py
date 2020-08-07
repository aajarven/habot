"""
Utility functions
"""

import datetime


def last_weekday_date(weekday_number):
    """
    Return a datetime corresponding to the last given day.

    Following weekday_numbers are supported:
    0 Monday
    1 Tuesday
    3 Wednesday
    4 Thursday
    5 Friday
    6 Saturday
    7 Sunday
    """
    today = datetime.date.today()
    return today - datetime.timedelta(today.weekday() - weekday_number)
