from os import getenv

from pony.orm import Database

db = Database()


def bind_db():
    user = getenv("POSTGRESQL_USERNAME")
    password = getenv("POSTGRESQL_PASSWORD")
    database = getenv("POSTGRESQL_DATABASE")
    host = getenv("POSTGRESQL_HOST")
    port = getenv("POSTGRESQL_PORT")

    db.bind(provider="postgres", user=user, password=password, host=host, database=database, port=port)
    db.generate_mapping(create_tables=True)



