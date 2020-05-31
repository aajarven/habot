"""
Public information about the database.
"""

DB_NAME = "habdb"

TABLES = {
    "members": {
        "id": "VARCHAR(50)",
        "displayname": "VARCHAR(255)",
        "loginname": "VARCHAR(255)",
        "birthday": "DATE",
        },
    }
