"""
Public information about the database.
"""

DB_NAME = "habdb"

# table: (data, primary_key)
TABLES = {
    "members": ({
        "id": "VARCHAR(50)",
        "displayname": "VARCHAR(255)",
        "loginname": "VARCHAR(255)",
        "birthday": "DATE",
        }, "id"),
    }
