import csv
import io
import json
import os

from flask import (
    Blueprint, Response, current_app, flash, g, redirect,
    render_template, request, url_for,
)

from app_blueprints.auth import login_required
from db import get_db
from predict import predict_application

bp = Blueprint("main", __name__)


def load_metrics():
    metrics_path = os.path.join(current_app.config["MODEL_DIR"], "metrics.json")
    if not os.path.exists(metrics_path):
        return None
    with open(metrics_path) as f:
        return json.load(f)


# --------------------------------------------------------------- #
# PUBLIC PAGES
# --------------------------------------------------------------- #
@bp.route("/")
def landing():
    metrics = load_metrics()
    best_accuracy = None
    if metrics:
        best_accuracy = metrics["results"][metrics["best_model"]]["accuracy"] * 100
    return render_template("landing.html", best_accuracy=best_accuracy)


@bp.route("/about")
def about():
    return render_template("about.html")


@bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        flash("Thanks for reaching out — our team will respond within 1 business day.", "success")
        return redirect(url_for("main.contact"))
    return render_template("contact.html")


# --------------------------------------------------------------- #
# DASHBOARD
# --------------------------------------------------------------- #
@bp.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    user_id = g.user["UserID"]

    total = db.execute(
        "SELECT COUNT(*) c FROM PredictionHistory WHERE UserID = ?", (user_id,)
    ).fetchone()["c"]
    approved = db.execute(
        "SELECT COUNT(*) c FROM PredictionHistory WHERE UserID = ? AND ApprovalResult = 'Approved'",
        (user_id,),
    ).fetchone()["c"]
    rejected = total - approved

    recent = db.execute(
        "SELECT * FROM PredictionHistory WHERE UserID = ? ORDER BY PredictionDate DESC LIMIT 6",
        (user_id,),
    ).fetchall()

    metrics = load_metrics()
    model_accuracy = metrics["results"][metrics["best_model"]]["accuracy"] * 100 if metrics else 0

    return render_template(
        "dashboard.html",
        total=total, approved=approved, rejected=rejected,
        recent=recent, model_accuracy=round(model_accuracy, 2),
        best_model=metrics["best_model"] if metrics else "N/A",
    )


# --------------------------------------------------------------- #
# PREDICTION
# --------------------------------------------------------------- #
@bp.route("/predict", methods=["GET", "POST"])
@login_required
def predict():
    if request.method == "POST":
        form = request.form
        errors = []

        required = ["applicant_name", "gender", "age", "income", "email"]
        for field in required:
            if not form.get(field):
                errors.append(f"'{field.replace('_', ' ').title()}' is required.")
        try:
            age = int(form.get("age", 0))
            if age < 18 or age > 100:
                errors.append("Age must be between 18 and 100.")
        except ValueError:
            errors.append("Age must be a valid number.")
        try:
            income = float(form.get("income", 0))
            if income < 0:
                errors.append("Income cannot be negative.")
        except ValueError:
            errors.append("Income must be a valid number.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("predict.html", form=form)

        result = predict_application(form)

        db = get_db()
        cur = db.execute(
            """INSERT INTO ApplicantDetails
               (UserID, ApplicantName, Gender, Age, Income, IncomeType, EducationType,
                FamilyStatus, HousingType, EmployedYears, Children, FamilyMembers,
                OwnCar, OwnRealty, Phone, Email, OverdueStatus)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                g.user["UserID"], form.get("applicant_name"), form.get("gender"),
                age, income, form.get("income_type"), form.get("education_type"),
                form.get("family_status"), form.get("housing_type"),
                int(form.get("employed_years", 0)), int(form.get("children", 0)),
                int(form.get("family_members", 1)), form.get("own_car", "N"),
                form.get("own_realty", "N"), form.get("phone_number", ""),
                form.get("email"), int(form.get("overdue_status", 0)),
            ),
        )
        applicant_id = cur.lastrowid

        metrics = load_metrics()
        model_used = metrics["best_model"] if metrics else "N/A"

        db.execute(
            """INSERT INTO PredictionHistory
               (UserID, ApplicantID, ApplicantName, ApprovalResult, Probability, RiskLevel, ModelUsed)
               VALUES (?,?,?,?,?,?,?)""",
            (
                g.user["UserID"], applicant_id, form.get("applicant_name"),
                result["prediction"], result["approval_probability"],
                result["risk_level"], model_used,
            ),
        )
        db.commit()

        return render_template(
            "result.html", result=result, applicant_name=form.get("applicant_name")
        )

    return render_template("predict.html", form={})


# --------------------------------------------------------------- #
# HISTORY
# --------------------------------------------------------------- #
@bp.route("/history")
@login_required
def history():
    db = get_db()
    query = "SELECT * FROM PredictionHistory WHERE UserID = ?"
    params = [g.user["UserID"]]

    status = request.args.get("status", "")
    search = request.args.get("search", "")
    sort = request.args.get("sort", "PredictionDate")
    order = request.args.get("order", "DESC")

    if status in ("Approved", "Rejected"):
        query += " AND ApprovalResult = ?"
        params.append(status)
    if search:
        query += " AND ApplicantName LIKE ?"
        params.append(f"%{search}%")

    allowed_sorts = {"PredictionDate", "ApplicantName", "ApprovalResult", "Probability"}
    if sort not in allowed_sorts:
        sort = "PredictionDate"
    order = "DESC" if order.upper() != "ASC" else "ASC"
    query += f" ORDER BY {sort} {order}"

    rows = db.execute(query, params).fetchall()
    return render_template(
        "history.html", rows=rows, status=status, search=search, sort=sort, order=order
    )


@bp.route("/history/delete/<int:prediction_id>", methods=["POST"])
@login_required
def delete_history(prediction_id):
    db = get_db()
    db.execute(
        "DELETE FROM PredictionHistory WHERE PredictionID = ? AND UserID = ?",
        (prediction_id, g.user["UserID"]),
    )
    db.commit()
    flash("Prediction record deleted.", "info")
    return redirect(url_for("main.history"))


@bp.route("/history/export")
@login_required
def export_history():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM PredictionHistory WHERE UserID = ? ORDER BY PredictionDate DESC",
        (g.user["UserID"],),
    ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["PredictionID", "ApplicantName", "ApprovalResult", "Probability",
                      "RiskLevel", "ModelUsed", "PredictionDate"])
    for r in rows:
        writer.writerow([r["PredictionID"], r["ApplicantName"], r["ApprovalResult"],
                          r["Probability"], r["RiskLevel"], r["ModelUsed"], r["PredictionDate"]])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=prediction_history.csv"},
    )


# --------------------------------------------------------------- #
# MODEL PERFORMANCE + VISUALIZATIONS
# --------------------------------------------------------------- #
@bp.route("/performance")
@login_required
def performance():
    metrics = load_metrics()
    return render_template("performance.html", metrics=metrics)


@bp.route("/visualizations")
@login_required
def visualizations():
    charts_dir = current_app.config["CHARTS_DIR"]
    charts = sorted(os.listdir(charts_dir)) if os.path.exists(charts_dir) else []
    return render_template("visualizations.html", charts=charts)
