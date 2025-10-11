from utilities.database import create_table_schema, connect_to_database

#Creating database
conn, cursor = connect_to_database()
create_table_schema(cursor)

# Populate with active systems. This will control entire program