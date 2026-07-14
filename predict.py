"""
predict.py
----------
Loads the trained model + encoders + scaler and exposes a single
`predict_application()` function used by the Flask app to score a new
credit-card application in real time.
"""
import os
import joblib
import numpy as np
import pandas as pd

# Dynamic path resolution that works seamlessly locally and on Render production
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(BASE_DIR, "model")):
    MODEL_DIR = os.path.join(BASE_DIR, "model")
else:
    # If executed from inside the blueprint subfolder, travel up one level to the root
    MODEL_DIR = os.path.join(os.path.dirname(BASE_DIR), "model")

_model = None
_encoders = None
_scaler = None
_feature_cols = None


def _load_artifacts():
    global _model, _encoders, _scaler, _feature_cols
    if _model is None:
        _model = joblib.load(os.path.join(MODEL_DIR, "saved_model.pkl"))
        _encoders = joblib.load(os.path.join(MODEL_DIR, "encoder.pkl"))
        _scaler = joblib.load(os.path.join(MODEL_DIR, "scaler.pkl"))
        _feature_cols = joblib.load(os.path.join(MODEL_DIR, "feature_columns.pkl"))
    return _model, _encoders, _scaler, _feature_cols


def _safe_encode(encoder, value):
    """Encode a category, falling back to the most common class if unseen."""
    value = str(value)
    if value in encoder.classes_:
        return int(encoder.transform([value])[0])
    return int(encoder.transform([encoder.classes_[0]])[0])


def predict_application(form: dict):
    """
    form keys expected (raw, human strings from the prediction form):
    gender, own_car, own_realty, children, income, income_type,
    education_type, family_status, housing_type, age, employed_years,
    work_phone, phone, email, occupation_type, family_members, overdue_status
    """
    model, encoders, scaler, feature_cols = _load_artifacts()

    row = {
        "CODE_GENDER": _safe_encode(encoders["CODE_GENDER"], form.get("gender", "M")),
        "FLAG_OWN_CAR": _safe_encode(encoders["FLAG_OWN_CAR"], form.get("own_car", "N")),
        "FLAG_OWN_REALTY": _safe_encode(encoders["FLAG_OWN_REALTY"], form.get("own_realty", "N")),
        "CNT_CHILDREN": int(form.get("children", 0)),
        "AMT_INCOME_TOTAL": float(form.get("income", 0)),
        "NAME_INCOME_TYPE": _safe_encode(encoders["NAME_INCOME_TYPE"], form.get("income_type", "Working")),
        "NAME_EDUCATION_TYPE": _safe_encode(encoders["NAME_EDUCATION_TYPE"], form.get("education_type", "Secondary / secondary special")),
        "NAME_FAMILY_STATUS": _safe_encode(encoders["NAME_FAMILY_STATUS"], form.get("family_status", "Married")),
        "NAME_HOUSING_TYPE": _safe_encode(encoders["NAME_HOUSING_TYPE"], form.get("housing_type", "House / apartment")),
        "AGE_YEARS": int(form.get("age", 30)),
        "EMPLOYED_YEARS": int(form.get("employed_years", 0)),
        "FLAG_WORK_PHONE": int(form.get("work_phone", 0)),
        "FLAG_PHONE": int(form.get("phone", 0)),
        "FLAG_EMAIL": 1,
        "OCCUPATION_TYPE": _safe_encode(encoders["OCCUPATION_TYPE"], form.get("occupation_type", "Laborers")),
        "CNT_FAM_MEMBERS": int(form.get("family_members", 1)),
        "OVERDUE_STATUS": int(form.get("overdue_status", 0)),
    }

    X = pd.DataFrame([[row[c] for c in feature_cols]], columns=feature_cols)
    X_scaled = scaler.transform(X)

    pred = int(model.predict(X_scaled)[0])
    proba = model.predict_proba(X_scaled)[0]
    confidence = float(proba[pred])
    approval_probability = float(proba[1])

    if approval_probability >= 0.75:
        risk_level = "Low Risk"
    elif approval_probability >= 0.45:
        risk_level = "Medium Risk"
    else:
        risk_level = "High Risk"

    reasoning = []
    if row["AMT_INCOME_TOTAL"] < 100000:
        reasoning.append("Reported income is below the typical approval threshold.")
    if row["OVERDUE_STATUS"] >= 2:
        reasoning.append("Credit history shows significant overdue payments.")
    if row["EMPLOYED_YEARS"] >= 2:
        reasoning.append("Stable employment history strengthens the application.")
    if form.get("own_realty") == "Y":
        reasoning.append("Property ownership improves creditworthiness.")
    if not reasoning:
        reasoning.append("Decision is based on the overall applicant risk profile.")

    return {
        "prediction": "Approved" if pred == 1 else "Rejected",
        "prediction_code": pred,
        "confidence": round(confidence * 100, 2),
        "approval_probability": round(approval_probability * 100, 2),
        "risk_level": risk_level,
        "reasoning": reasoning,
        "recommendation": (
            "Proceed with card issuance under standard terms."
            if pred == 1 else
            "Application does not currently meet approval criteria. "
            "Consider requesting additional documentation or a co-applicant."
        ),
    }
