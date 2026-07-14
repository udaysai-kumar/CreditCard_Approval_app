import sqlite3
import os
from flask import current_app, g

def get_db():
    if "db" not in g:
        db_url = current_app.config["DATABASE_PATH"]
        if db_url and db_url.startswith("postgres"):
            # Connect to cloud PostgreSQL
            import psycopg2
            import psycopg2.extras
            g.db = psycopg2.connect(db_url)
            g.db.row_factory = psycopg2.extras.DictRow
        else:
            # Fallback to local SQLite development
            g.db = sqlite3.connect(db_url)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
    return g.db
