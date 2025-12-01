from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()

@event.listens_for(Engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    dbapi_connection.execute("PRAGMA foreign_keys=ON")