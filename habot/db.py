"""
Database operations for the bot.
"""

import mysql.connector

import conf.db as dbconf
import conf.secrets.db_credentials as credentials


class DBOperator():
    """
    A tool for working with the habitica database.
    """

    def __init__(self):
        """
        Initialize the database connection.

        If the database doesn't have all the databases or tables it should,
        those are created.
        """
        self.conn = mysql.connector.connect(host="localhost",
                                            user=credentials.USER,
                                            passwd=credentials.PASSWORD)
        self._ensure_tables()

    def query_table(self, table, columns="*", condition=None,
                    database=dbconf.DB_NAME):
        """
        Run a MySQL query on a single table and return the results.

        :table: The table to be queried.
        :columns: A list of column names. If not provided, all columns used.
        :condition: A string corresponding to 'WHERE' part of the query (not
                    including the 'WHERE' itself). If not provided, all rows
                    are returned.
        """
        if isinstance(columns, list):
            column_str = ", ".join(columns)
        elif isinstance(columns, str):
            column_str = columns
        else:
            raise ValueError("Illegal column selector '{}' received. A string "
                             "or list expected.".format(columns))

        if condition:
            condition_str = "WHERE {}".format(condition)
        else:
            condition_str = ""

        query_str = "SELECT {} FROM {} {}".format(column_str, table,
                                                  condition_str)
        cursor = self._cursor_for_db(database)
        cursor.execute(query_str)
        data = cursor.fetchall()
        cursor.close()
        return data

    def insert_data(self, table, data, database=dbconf.DB_NAME):
        """
        Insert given data to the table.

        :table: Name of the table to which a new row is inserted
        :data: A dict representing the data to be inserted. The keys must
               correspond to the column names in the table, and values to their
               inserted values.
        :raises: DatabaseCommunicationException if exactly one row isn't
                 affected by the operation. In this case, the database is not
                 altered.
        """
        columns = []
        values = []
        for key, value in data.items():
            columns.append(key)
            values.append("'{}'".format(value))
        column_str = ", ".join(columns)
        value_str = ", ".join(values)
        cursor = self._cursor_for_db(database)
        insert_str = "INSERT INTO {} ({}) VALUES ({})".format(table,
                                                              column_str,
                                                              value_str)
        cursor.execute(insert_str)

        affected_rows = cursor.rowcount
        if affected_rows != 1:
            statement = cursor.statement
            cursor.close()
            raise DatabaseCommunicationException(
                "Inserting the following data:\n{}\ninto table {} should have "
                "affected one row, but instead it affected {}. The used "
                "command:\n{}".format(data, table, affected_rows, statement))

        cursor.close()
        self.conn.commit()

    def databases(self):
        """
        Return a list of available databases.
        """
        cursor = self.conn.cursor()
        cursor.execute("SHOW DATABASES")
        dbs = [db[0] for db in cursor]
        cursor.close()
        return dbs

    def tables(self, database=dbconf.DB_NAME):
        """
        Return a list of tables in a database.

        :database: Name of the database
        """
        cursor = self._cursor_for_db(database)
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor]
        cursor.close()
        return tables

    def columns(self, table, database=dbconf.DB_NAME):
        """
        Return a list of columns in the table.
        """

    def _cursor_for_db(self, db):
        """
        Return a cursor for operating on the given database.

        :db: Name of the database
        """
        cursor = self.conn.cursor()
        cursor.execute("USE {}".format(db))
        return cursor

    def _ensure_tables(self):
        """
        Make sure that the database follows the data model.

        If tables or databases are missing, they are created.
        """
        def create_table_cmd(table_name, table_columns, primary_key):
            """
            Return a string that can be executed to create a table.
            """
            columns = ["{} {}".format(name, table_columns[name]) for name in
                       table_columns]
            return "CREATE TABLE {} ({}, PRIMARY KEY (`{}`))".format(
                table_name, ", ".join(columns), primary_key)

        cursor = self.conn.cursor()

        # ensure that the database exists
        if dbconf.DB_NAME not in self.databases():
            cursor.execute("CREATE DATABASE {}".format(dbconf.DB_NAME))

        # ensure that all tables exist
        cursor.execute("USE {}".format(dbconf.DB_NAME))
        tables = self.tables()
        for table_name, (table_columns, primary_key) in dbconf.TABLES.items():
            if table_name not in tables:
                cursor.execute(create_table_cmd(table_name, table_columns,
                                                primary_key))

        cursor.close()


class DatabaseCommunicationException(Exception):
    """
    En exception to be used when something unexpected happens with the db.
    """
