"""
db.py
-----
Robust data-access layer supporting SQLite locally and PostgreSQL via pg8000 in production.
"""
import os
import sqlite3
from flask import current_app, g

def get_db():
    if "db" not in g:
        db_uri = current_app.config["DATABASE_PATH"]
        
        # Check if we are using cloud PostgreSQL on Render
        if db_uri and (db_uri.startswith("postgres://") or db_uri.startswith("postgresql://")):
            import pg8000
            
            # Standardize URL schema prefix for pg8000 compatibility
            if db_uri.startswith("postgres://"):
                db_uri = db_uri.replace("postgres://", "postgresql://", 1)
                
            # Parse connection details from string url
            # Format: postgresql://user:password@host:port/dbname
            try:
                # Strip prefix
                clean_uri = db_uri.split("://")[1]
                user_pass, host_db = clean_uri.split("@")
                user, password = user_pass.split(":")
                host_port, dbname = host_db.split("/")
                
                host = host_port.split(":")[0]
                port = int(host_port.split(":")[1]) if ":" in host_port else 5432
                
                # Connect using pure-python pg8000 driver
                conn = pg8000.connect(
                    user=user,
                    password=password,
                    host=host,
                    port=port,
                    database=dbname
                )
                g.db = conn
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

# PostgreSQL uses SERIAL instead of AUTOINCREMENT for primary keys
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
            cursor = db.cursor()
            # Execute queries natively
            cursor.execute(SCHEMA_POSTGRES)
            db.commit()
        else:
            db.executescript(SCHEMA_SQLITE)
            db.commit()

def init_app(app):
    app.teardown_appcontext(close_db)
    init_db(app)
