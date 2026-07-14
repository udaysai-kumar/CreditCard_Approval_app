import functools
import re

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db

bp = Blueprint("auth", __name__, url_prefix="/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.get("user") is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(**kwargs)
    return wrapped_view


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        db = get_db()
        g.user = db.execute(
            "SELECT * FROM Users WHERE UserID = ?", (user_id,)
        ).fetchone()


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        error = None
        if not name or len(name) < 2:
            error = "Please enter your full name."
        elif not EMAIL_RE.match(email):
            error = "Please enter a valid email address."
        elif len(password) < 6:
            error = "Password must be at least 6 characters long."
        elif password != confirm:
            error = "Passwords do not match."

        db = get_db()
        if error is None:
            existing = db.execute(
                "SELECT UserID FROM Users WHERE Email = ?", (email,)
            ).fetchone()
            if existing is not None:
                error = f"An account for {email} already exists."

        if error is None:
            db.execute(
                "INSERT INTO Users (Name, Email, PasswordHash) VALUES (?, ?, ?)",
                (name, email, generate_password_hash(password)),
            )
            db.commit()
            flash("Account created successfully. Please log in.", "success")
            return redirect(url_for("auth.login"))

        flash(error, "danger")

    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute("SELECT * FROM Users WHERE Email = ?", (email,)).fetchone()

        error = None
        if user is None or not check_password_hash(user["PasswordHash"], password):
            error = "Incorrect email or password."

        if error is None:
            session.clear()
            session["user_id"] = user["UserID"]
            flash(f"Welcome back, {user['Name']}!", "success")
            next_url = request.args.get("next") or url_for("main.dashboard")
            return redirect(next_url)

        flash(error, "danger")

    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.landing"))
