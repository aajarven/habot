"""
Delete all challenges the user currently owns
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import requests

from habitica_helper.utils import get_dict_from_api

from conf.header import HEADER

all_challenges = get_dict_from_api(
        HEADER,
        "https://habitica.com/api/v3/challenges/groups/party")

if len(all_challenges) == 0:
    print("No challenges found.")
    exit()

confirmation = input("About to purge all challenges for user {}. Proceed? "
                     "(y/n) ".format(
                         all_challenges[0]["leader"]["profile"]["name"]))
if confirmation.lower() not in ["yes", "y", "1", "true"]:
    print("Nothing removed.")
    exit()

deleted = 0
for challenge in all_challenges:
    if challenge["leader"]["id"] == HEADER["x-api-user"]:
        requests.delete(
            "https://habitica.com/api/v3/challenges/{}".format(challenge["id"]),
            headers=HEADER)
        deleted += 1
print("Deleted {} challenges.".format(deleted))
