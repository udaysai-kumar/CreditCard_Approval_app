"""
db.py
-----
Lightweight SQLite data-access layer. Uses Flask's `g` object to keep
one connection per request. No ORM dependency required.
"""
import sqlite3

from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


SCHEMA = """
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


def init_db(app):
    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA)
        db.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
    init_db(app)
