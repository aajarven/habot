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
    "private_messages": ({
        "id": "VARCHAR(50)",
        "from_id": "VARCHAR(50)",
        "to_id": "VARCHAR(50)",
        "timestamp": "DATETIME",
        "content": "VARCHAR(3000)",
        "reaction_pending": "BOOLEAN",
        }, "id"),
    }
