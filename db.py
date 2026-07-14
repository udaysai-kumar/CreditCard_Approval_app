"""
db.py
-----
Robust data-access layer supporting SQLite locally and PostgreSQL via pg8000 in production.
Wraps the pg8000 connection to support the standard SQLite-style .execute() methods cleanly.
"""
import os
import sqlite3
from flask import current_app, g

class PostgreSQLConnectionWrapper:
    """Wraps a pg8000 connection to mimic SQLite's direct .execute() syntax and row conversion."""
    def __init__(self, conn):
        self.conn = conn

    def execute(self, query, params=None):
        cursor = self.conn.cursor()
        # Convert SQLite style '?' placeholders to PostgreSQL '%s' style placeholders
        if "?" in query:
            query = query.replace("?", "%s")
        
        cursor.execute(query, params or ())
        return PostgreSQLCursorWrapper(cursor)

    def commit(self):
        return self.conn.commit()

    def close(self):
        return self.conn.close()


class PostgreSQLCursorWrapper:
    """Wraps a pg8000 cursor to mimic SQLite row extraction methods seamlessly."""
    def __init__(self, cursor):
        self.cursor = cursor

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is None:
            return None
        # Convert the tuple/list array into a dictionary map matching column description names
        columns = [desc[0] for desc in self.cursor.description]
        return dict(zip(columns, row))

    def fetchall(self):
        rows = self.cursor.fetchall()
        columns = [desc[0] for desc in self.cursor.description]
        return [dict(zip(columns, r)) for r in rows]


def get_db():
    if "db" not in g:
        db_uri = current_app.config["DATABASE_PATH"]
        
        # Check if we are using cloud PostgreSQL on Render
        if db_uri and (db_uri.startswith("postgres://") or db_uri.startswith("postgresql://")):
            import pg8000
            
            if db_uri.startswith("postgres://"):
                db_uri = db_uri.replace("postgres://", "postgresql://", 1)
                
            try:
                clean_uri = db_uri.split("://")[1]
                user_pass, host_db = clean_uri.split("@")
                user, password = user_pass.split(":")
                host_port, dbname = host_db.split("/")
                
                host = host_port.split(":")[0]
                port = int(host_port.split(":")[1]) if ":" in host_port else 5432
                
                conn = pg8000.connect(
                    user=user,
                    password=password,
                    host=host,
                    port=port,
                    database=dbname
                )
                # Wrap the connection to provide .execute() functionality seamlessly
                g.db = PostgreSQLConnectionWrapper(conn)
            except Exception as e:
                raise RuntimeError(f"Failed to parse or connect to PostgreSQL: {e}")
        else:
            # Fallback to local SQLite development configuration
            g.db = sqlite3.connect(db_uri)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
            
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

# Schema definitions remain intact for automatic structural generation
SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS Users (
    UserID INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL,
    Email TEXT UNIQUE NOT NULL,
    PasswordHash TEXT NOT NULL,
    Role TEXT DEFAULT 'user',
    CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ApplicantDetails (
    ApplicantID INTEGER PRIMARY KEY AUTOINCREMENT,
    UserID INTEGER,
    ApplicantName TEXT,
    Gender TEXT, Age INTEGER, Income REAL,
    IncomeType TEXT, EducationType TEXT, FamilyStatus TEXT,
    HousingType TEXT, EmployedYears INTEGER, Children INTEGER,
    FamilyMembers INTEGER, OwnCar TEXT, OwnRealty TEXT,
    Phone TEXT, Email TEXT, OverdueStatus INTEGER,
    FOREIGN KEY (UserID) REFERENCES Users(UserID)
);
CREATE TABLE IF NOT EXISTS PredictionHistory (
    PredictionID INTEGER PRIMARY KEY AUTOINCREMENT,
    UserID INTEGER,
    ApplicantID INTEGER,
    ApplicantName TEXT,
    ApprovalResult TEXT,
    Probability REAL,
    RiskLevel TEXT,
    ModelUsed TEXT,
    PredictionDate TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES Users(UserID),
    FOREIGN KEY (ApplicantID) REFERENCES ApplicantDetails(ApplicantID)
);
"""

SCHEMA_POSTGRES = """
CREATE TABLE IF NOT EXISTS Users (
    UserID SERIAL PRIMARY KEY,
    Name TEXT NOT NULL,
    Email TEXT UNIQUE NOT NULL,
    PasswordHash TEXT NOT NULL,
    Role TEXT DEFAULT 'user',
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ApplicantDetails (
    ApplicantID SERIAL PRIMARY KEY,
    UserID INTEGER,
    ApplicantName TEXT,
    Gender TEXT, Age INTEGER, Income REAL,
    IncomeType TEXT, EducationType TEXT, FamilyStatus TEXT,
    HousingType TEXT, EmployedYears INTEGER, Children INTEGER,
    FamilyMembers INTEGER, OwnCar TEXT, OwnRealty TEXT,
    Phone TEXT, Email TEXT, OverdueStatus INTEGER,
    FOREIGN KEY (UserID) REFERENCES Users(UserID)
);
CREATE TABLE IF NOT EXISTS PredictionHistory (
    PredictionID SERIAL PRIMARY KEY,
    UserID INTEGER,
    ApplicantID INTEGER,
    ApplicantName TEXT,
    ApprovalResult TEXT,
    Probability REAL,
    RiskLevel TEXT,
    ModelUsed TEXT,
    PredictionDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES Users(UserID),
    FOREIGN KEY (ApplicantID) REFERENCES ApplicantDetails(ApplicantID)
);
"""

def init_db(app):
    with app.app_context():
        db = get_db()
        db_uri = app.config["DATABASE_PATH"]
        
        if db_uri and (db_uri.startswith("postgres://") or db_uri.startswith("postgresql://")):
            # Extract raw connection from wrapper for initialization queries
            raw_conn = db.conn
            cursor = raw_conn.cursor()
            cursor.execute(SCHEMA_POSTGRES)
            raw_conn.commit()
        else:
            db.executescript(SCHEMA_SQLITE)
            db.commit()

def init_app(app):
    app.teardown_appcontext(close_db)
    init_db(app)
