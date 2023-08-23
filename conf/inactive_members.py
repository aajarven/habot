"""
Here it is possible to disable inactivity reminders and removing from party for
some party members.
"""

# list of Habitica users who will not be kicked from the party even if
# inactive. E.g.
# ALLOW_INACTIVITY_FROM = ["@someHabiticaUser", "@someoneElse"]
ALLOW_INACTIVITY_FROM = []

# How many days have to have elapsed since the last time a user logged in for
# them to be removed from the party due to inactivity.
INACTIVITY_THRESHOLD_DAYS = 3*30
