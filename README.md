# Antonbury's Habitica Bot

![stylecheck](https://github.com/aajarven/habot/workflows/stylecheck/badge.svg)
![test](https://github.com/aajarven/habot/workflows/test/badge.svg)

This is a simple bot, written to help with party-related tasks in [Habitica](https://habitica.com/). The functionalities implemented in `run_scheduled` are likely too specific to be much use for others, but the `habot` package contains modules that are likely to at least serve as a good starting point for developing other tools for Habitica using Python.

The bot is in many ways a next step from [habitica-helper](https://github.com/aajarven/habitica-helper), and functionality from there is actually directly used here.

## Requirements
In order to actually run this tool as a bot, you'll of course need a computer to host it on. I'm personally using a Raspberry Pi for that, because they are cheap and silent, and the bot is light enough to easily run on one.

In order to limit API queries, the bot saves some data to a mysql database, so one has to be running and credentials for it set in `conf/secrets/db_credentials.py`. See `conf/secrets/db_credentials_template.py` for an example.

The bot runs on Python, any version above 3.6 should be fine. Python requirements can be installed with `pip install -r requirements.txt`.


## Features

There are modules e.g. for the following tasks. They might be handy for people developing their own Habitica assistance tools.
 - Listing Habitica birthdays of party members and creating birthday reminders
 - Listing, ticking, and creating tasks
 - Joining challenges
 - Sending and reading private and party messages
 - Interacting with the database

The bot is currently able to interact with the world around based on timed events (see `run-scheduled.py`) and by reacting to private messages.

Commands for these actions are recognized:
 - Respond to a ping
 - List birthdays of all party members
 - Send a message with a list of party members celebrating their Habitica birthday
 - Create a new sharing weekend challenge (e.g. the name of the challenge is currently hard-coded, so this might not be of use for others out of the box)
 - Award a random winner for a challenge (again, uses some hard-coded values, so usage requires some programming)
 - Send reminders for a list of people who are supposed to invite the party to a quest soon
 - Forward a newsletter to all party members
