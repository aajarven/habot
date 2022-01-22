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
        "lastlogin": "DATE",
        }, "id"),
    "private_messages": ({
        "id": "VARCHAR(50)",
        "from_id": "VARCHAR(50)",
        "to_id": "VARCHAR(50)",
        "timestamp": "DATETIME",
        "content": "VARCHAR(6000)",
        "reaction_pending": "BOOLEAN",
        }, "id"),
    "chat_messages": ({
        "id": "VARCHAR(50)",
        "from_id": "VARCHAR(50)",
        "to_group": "VARCHAR(50)",
        "timestamp": "DATETIME",
        "content": "VARCHAR(6000)",
        "reaction_pending": "BOOLEAN",
        }, "id"),
    "system_messages": ({
        "id": "VARCHAR(50)",
        "to_group": "VARCHAR(50)",
        "timestamp": "DATETIME",
        "content": "VARCHAR(6000)",
        "type": "VARCHAR(6000)",
        }, "id"),
    "likes": ({
        "id": "INT AUTO_INCREMENT",
        "message": "VARCHAR(50)",
        "user": "VARCHAR(50)",
        }, "id"),
    "flags": ({
        "id": "INT AUTO_INCREMENT",
        "message": "VARCHAR(50)",
        "user": "VARCHAR(50)",
        }, "id"),
    "system_message_info": ({
        "id": "INT AUTO_INCREMENT",
        "message_id": "VARCHAR(50)",
        "info_key": "VARCHAR(50)",
        "info_value": "VARCHAR(200)",
        }, "id"),
    }
