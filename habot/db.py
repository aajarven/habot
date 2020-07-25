"""
Database operations for the bot.
"""

import mysql.connector

import conf.db as dbconf
import conf.secrets.db_credentials as credentials
import habot.logger


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
        self._logger = habot.logger.get_logger()
        self.conn = mysql.connector.connect(host="localhost",
                                            user=credentials.USER,
                                            passwd=credentials.PASSWORD)
        self._ensure_tables()

    def query_table_based_on_dict(self, table, condition_dict,
                                  database=dbconf.DB_NAME):
        """
        Run a MySQL query on a single table matching the condition dict.

        :table: The table to be queried
        :condition_dict: Values used for the WHERE part of the query. Dict keys
                         are used as column names and values as their values,
                         and all of the values must match.
        :return: A list of dicts corresponding to matching rows.
        """
        keys = condition_dict.keys()
        values = [str(value) for value in condition_dict.values()]
        condition = " AND ".join(["{} = %s".format(key) for key in keys])
        query_str = "SELECT * FROM {} WHERE {}".format(table,
                                                       condition)
        cursor = self._cursor_for_db(database)
        cursor.execute(query_str, tuple(values))
        data = cursor.fetchall()
        columns = cursor.column_names
        cursor.close()
        return self._data_to_dicts(data, columns)

    def query_table(self, table, columns=None, condition=None,
                    database=dbconf.DB_NAME):
        """
        Run a MySQL query on a single table and return the results.

        :table: The table to be queried.
        :columns: A list of names of columns from which to return data. If not
                  provided, all columns are used.
        :condition: A string corresponding to 'WHERE' part of the query (not
                    including the 'WHERE' itself). If not provided, all rows
                    are returned.
        """
        if isinstance(columns, list):
            column_str = ", ".join(columns)
        elif isinstance(columns, str):
            column_str = columns
        elif columns is None:
            column_str = "*"
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
        columns = cursor.column_names
        cursor.close()
        return self._data_to_dicts(data, columns)

    def update_row(self, table, primary_key_value, new_data,
                   database=dbconf.DB_NAME):
        """
        Update a single row in the database based on the primary key value.

        Only single-column primary keys are supported at the moment.

        :table: Name of the table where data should be updated
        :primary_key_value: Value of the primary key on the row that is to be
                            updated
        :new_data: A dict with column names as keys and new values as values
        :database: Database to be used. If not specified, the default database
                   from configuration file is used.
        """
        primary_key = self._primary_key(table, database)
        if len(primary_key) > 1:
            raise NotImplementedError("Multi-column primary keys not "
                                      "supported yet")
        primary_key = primary_key[0]

        values_str = ", ".join(
            ["{} = %s".format(key) for key in new_data])
        update_str = "UPDATE {} SET {} WHERE {}='{}'".format(
            table, values_str, primary_key, primary_key_value)

        cursor = self._cursor_for_db(database)
        cursor.execute(update_str, tuple(new_data.values()))

        affected_rows = cursor.rowcount
        if affected_rows not in [0, 1]:
            statement = cursor.statement
            cursor.close()
            raise DatabaseCommunicationException(
                "Updating the following data:\n{}\ninto table {} should have "
                "affected one row, but instead it affected {}. The used "
                "command:\n{}".format(new_data, table, affected_rows,
                                      statement))

        cursor.close()
        self.conn.commit()

    def insert_data(self, table, data, database=dbconf.DB_NAME):
        """
        Insert a row representing the given data to the table.

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
            values.append(str(value))
        column_str = ", ".join(columns)
        cursor = self._cursor_for_db(database)
        value_parameters = ", ".join(["%s"]*len(columns))
        insert_str = "INSERT INTO {} ({}) VALUES ({})".format(table,
                                                              column_str,
                                                              value_parameters)
        cursor.execute(insert_str, tuple(values))

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

    def delete_row(self, table, condition_column, condition_value,
                   database=dbconf.DB_NAME):
        """
        Delete a single row from the table based on the primary key.

        :table: Database table from which the values are to be deleted
        :condition_column: Column of the table to be used when choosing the row
                           for deletion. Must at the moment be the primary key
                           of the table.
        :condition_value: Value for the condition_column for the deleted row
        :database: Database to be used. If not specified, the default database
                   from configuration file is used.
        """
        # TODO: allow removing based on other keys too
        if not self._is_primary_key(table, condition_column, database):
            raise ValueError("Cannot delete a row based on {}: not a primary "
                             "key.".format(condition_column))
        cursor = self._cursor_for_db(database)
        del_str = "DELETE FROM {} WHERE {} = '{}';".format(table,
                                                           condition_column,
                                                           condition_value)
        cursor.execute(del_str)
        affected_rows = cursor.rowcount
        if affected_rows == 0:
            raise DataNotFoundException("Condition {} = {} did not match "
                                        "any rows on table {}: deletion "
                                        "could not be performed.".format(
                                            condition_column, condition_value,
                                            table))
        if affected_rows > 1:
            statement = cursor.statement
            cursor.close()
            raise DatabaseCommunicationException(
                "Deletion from table {} using statement '{}' would remove "
                "more than one row. Nothing deleted.".format(table,
                                                             statement))

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
        Return all columns in the table.

        The columns are returned as a dict in which the column names are keys,
        and their values are dicts describing the column data. The keys for
        column description values are:
            - 'Type' (data type)
            - 'Null' ('YES' or 'NO' depending on if the value can be NULL)
            - 'Key' ('PRI' or empty, tells if this column is a primary key)
            - 'Default' (Default value for this column)
            - 'Extra' (possible extra information)
        """
        cursor = self._cursor_for_db(database)
        cursor.execute("DESCRIBE {}.{}".format(database, table))

        columns = {}

        descriptions = cursor.description
        for data in cursor:
            info = {}
            for i in range(1, len(descriptions)):
                info[descriptions[i][0]] = data[i]
                columns[data[0]] = info
        cursor.close()
        return columns

    def _data_to_dicts(self, rows, column_names):
        """
        Represent the rows as dicts, column names as keys.

        :rows: Data on the rows to be represented
        :column_names: corresponding column names
        """
        data = []
        for row in rows:
            data.append({
                column_names[i]: row[i] for i in range(len(column_names))
                })
        return data

    def _is_primary_key(self, table, key, database=dbconf.DB_NAME):
        """
        Return True if the given key is primary key for the table.

        Currently only works for single-column keys.
        """
        primary_key = self._primary_key(table, database)
        if len(primary_key) > 1:
            raise NotImplementedError("Multi-column primary keys not "
                                      "supported yet")
        return primary_key[0] == key

    def _primary_key(self, table, database=dbconf.DB_NAME):
        """
        Return the primary key as a list of column names.
        """
        primary_key = []
        for column_name, column_info in self.columns(table, database).items():
            if column_info["Key"] == "PRI":
                primary_key.append(column_name)
        return primary_key

    def _cursor_for_db(self, db):
        """
        Return a cursor for operating on the given database.

        :db: Name of the database
        """
        cursor = self.conn.cursor()
        cursor.execute("USE {}".format(db))
        cursor.execute("SET NAMES 'utf8mb4';")
        cursor.execute("SET CHARACTER SET utf8mb4;")
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
            columns = ["`{}` {}".format(name, table_columns[name]) for name in
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
                command = create_table_cmd(table_name, table_columns,
                                           primary_key)
                self._logger.debug("Creating a new table: %s", command)
                cursor.execute(command)

        cursor.close()


class DatabaseCommunicationException(Exception):
    """
    An exception to be used when something unexpected happens with the db.
    """


class DataNotFoundException(Exception):
    """
    An exception to be used when matching data is not found from the database.
    """
