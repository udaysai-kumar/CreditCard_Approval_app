"""
train_model.py
---------------
End-to-end training pipeline for the AI Credit Card Approval Prediction
System.

Steps:
 1. Load dataset (real Kaggle CSVs if present, else synthetic fallback)
 2. Clean data (drop duplicates, handle missing values)
 3. Feature engineering (age, employment years, income bands)
 4. Encode categorical variables (LabelEncoder, saved for inference)
 5. Train/test split + StandardScaler
 6. Train Logistic Regression, Decision Tree, Random Forest,
    Gradient Boosting (stand-in for XGBoost, which isn't installed here)
 7. Compare on Accuracy / Precision / Recall / F1 / ROC-AUC
 8. Auto-select best model, save charts, save model + encoders + scaler
 9. Persist metrics to model/metrics.json for the Flask app to display
"""

import json
import os
import sqlite3

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

sns.set_theme(style="darkgrid")
PALETTE = ["#0B3D91", "#2E86DE", "#00B894", "#54A0FF", "#0A2647"]

BASE = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE, "dataset")
MODEL_DIR = os.path.join(BASE, "model")
CHARTS_DIR = os.path.join(BASE, "static", "images", "charts")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)

CAT_COLS = [
    "CODE_GENDER", "FLAG_OWN_CAR", "FLAG_OWN_REALTY",
    "NAME_INCOME_TYPE", "NAME_EDUCATION_TYPE", "NAME_FAMILY_STATUS",
    "NAME_HOUSING_TYPE", "OCCUPATION_TYPE",
]
FEATURE_COLS = [
    "CODE_GENDER", "FLAG_OWN_CAR", "FLAG_OWN_REALTY", "CNT_CHILDREN",
    "AMT_INCOME_TOTAL", "NAME_INCOME_TYPE", "NAME_EDUCATION_TYPE",
    "NAME_FAMILY_STATUS", "NAME_HOUSING_TYPE", "AGE_YEARS",
    "EMPLOYED_YEARS", "FLAG_WORK_PHONE", "FLAG_PHONE", "FLAG_EMAIL",
    "OCCUPATION_TYPE", "CNT_FAM_MEMBERS", "OVERDUE_STATUS",
]
TARGET_COL = "APPROVED"


# ------------------------------------------------------------------ #
# 1. LOAD
# ------------------------------------------------------------------ #
def load_dataset():
    real_csv = os.path.join(DATASET_DIR, "application_record.csv")
    synth_csv = os.path.join(DATASET_DIR, "credit_card_applications.csv")
    if os.path.exists(real_csv):
        print("Loading real Kaggle dataset...")
        df = pd.read_csv(real_csv)
        if "APPROVED" not in df.columns:
            raise ValueError("Real dataset must be merged with a target 'APPROVED' column.")
    else:
        print("Real dataset not found -> using synthetic dataset (dataset/generate_dataset.py).")
        if not os.path.exists(synth_csv):
            from dataset.generate_dataset import generate
            generate().to_csv(synth_csv, index=False)
        df = pd.read_csv(synth_csv)
    print(f"Loaded {len(df)} rows, {df.shape[1]} columns.")
    return df


# ------------------------------------------------------------------ #
# 2. CLEAN
# ------------------------------------------------------------------ #
def clean_data(df):
    before = len(df)
    df = df.drop_duplicates(subset=[c for c in df.columns if c != "ID"], keep="first")
    print(f"Removed {before - len(df)} duplicate rows.")

    df["AMT_INCOME_TOTAL"] = df["AMT_INCOME_TOTAL"].fillna(df["AMT_INCOME_TOTAL"].median())
    df["OCCUPATION_TYPE"] = df["OCCUPATION_TYPE"].fillna("Unemployed")
    df = df.dropna(subset=[TARGET_COL])
    print(f"Missing values remaining:\n{df.isnull().sum()[df.isnull().sum() > 0]}")
    return df.reset_index(drop=True)


# ------------------------------------------------------------------ #
# 3. FEATURE ENGINEERING
# ------------------------------------------------------------------ #
def engineer_features(df):
    df["AGE_YEARS"] = (-df["DAYS_BIRTH"] / 365).astype(int)
    df["EMPLOYED_YEARS"] = np.where(
        df["DAYS_EMPLOYED"] > 0, 0, (-df["DAYS_EMPLOYED"] / 365).clip(lower=0)
    ).astype(int)
    if "OVERDUE_STATUS" not in df.columns:
        df["OVERDUE_STATUS"] = 0
    return df


# ------------------------------------------------------------------ #
# 4. ENCODE
# ------------------------------------------------------------------ #
def encode_features(df):
    encoders = {}
    for col in CAT_COLS:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        encoders[col] = le
    return df, encoders


# ------------------------------------------------------------------ #
# 5-7. TRAIN + COMPARE
# ------------------------------------------------------------------ #
def train_and_compare(X_train, X_test, y_train, y_test):
    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "Decision Tree": DecisionTreeClassifier(max_depth=8, random_state=42),
        "Random Forest": RandomForestClassifier(
            n_estimators=200, max_depth=12, random_state=42, n_jobs=-1
        ),
        "Gradient Boosting (XGBoost stand-in)": GradientBoostingClassifier(random_state=42),
    }

    results = {}
    fitted = {}
    plt.figure(figsize=(7, 6))

    for name, model in models.items():
        print(f"\nTraining {name}...")
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, y_proba)

        results[name] = {
            "accuracy": round(acc, 4), "precision": round(prec, 4),
            "recall": round(rec, 4), "f1_score": round(f1, 4),
            "roc_auc": round(auc, 4),
        }
        fitted[name] = model
        print(f"  Accuracy={acc:.4f} Precision={prec:.4f} Recall={rec:.4f} "
              f"F1={f1:.4f} ROC-AUC={auc:.4f}")

        fpr, tpr, _ = roc_curve(y_test, y_proba)
        plt.plot(fpr, tpr, label=f"{name} (AUC={auc:.3f})")

        cm = confusion_matrix(y_test, y_pred)
        fig, ax = plt.subplots(figsize=(5, 4))
        ConfusionMatrixDisplay(cm, display_labels=["Rejected", "Approved"]).plot(
            ax=ax, cmap="Blues", colorbar=False
        )
        ax.set_title(f"Confusion Matrix - {name}")
        plt.tight_layout()
        safe_name = name.split(" (")[0].replace(" ", "_").lower()
        plt.savefig(os.path.join(CHARTS_DIR, f"confusion_{safe_name}.png"), dpi=110)
        plt.close(fig)

    plt.plot([0, 1], [0, 1], "k--", alpha=0.4)
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve Comparison — All Models")
    plt.legend(loc="lower right", fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(CHARTS_DIR, "roc_curves_comparison.png"), dpi=110)
    plt.close()

    best_name = max(results, key=lambda k: results[k]["f1_score"])
    print(f"\nBest model selected: {best_name}")
    return results, fitted, best_name


# ------------------------------------------------------------------ #
# DATA VISUALIZATIONS (EDA)
# ------------------------------------------------------------------ #
def generate_eda_charts(df):
    def save(fig, filename):
        fig.tight_layout()
        fig.savefig(os.path.join(CHARTS_DIR, filename), dpi=110)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    sns.histplot(df["AMT_INCOME_TOTAL"], bins=40, color=PALETTE[1], ax=ax)
    ax.set_title("Income Distribution")
    save(fig, "income_distribution.png")

    fig, ax = plt.subplots(figsize=(5, 4))
    df["CODE_GENDER"].value_counts().plot.pie(
        autopct="%1.1f%%", colors=PALETTE, ax=ax, ylabel=""
    )
    ax.set_title("Gender Distribution")
    save(fig, "gender_distribution.png")

    fig, ax = plt.subplots(figsize=(7, 4))
    sns.countplot(y=df["NAME_EDUCATION_TYPE"], order=df["NAME_EDUCATION_TYPE"].value_counts().index,
                  palette=PALETTE, ax=ax)
    ax.set_title("Education Distribution")
    save(fig, "education_distribution.png")

    fig, ax = plt.subplots(figsize=(5, 4))
    df["APPROVED"].map({1: "Approved", 0: "Rejected"}).value_counts().plot.pie(
        autopct="%1.1f%%", colors=[PALETTE[2], PALETTE[0]], ax=ax, ylabel=""
    )
    ax.set_title("Approval Distribution")
    save(fig, "approval_distribution.png")

    numeric_df = df.select_dtypes(include=[np.number])
    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(numeric_df.corr(), annot=False, cmap="Blues", ax=ax)
    ax.set_title("Correlation Heatmap")
    save(fig, "correlation_heatmap.png")

    fig, ax = plt.subplots(figsize=(6, 4))
    sns.countplot(x=df["NAME_FAMILY_STATUS"], palette=PALETTE, ax=ax)
    ax.set_title("Family Status Count")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    save(fig, "family_status_count.png")


def generate_feature_importance(model, feature_names, model_name):
    if not hasattr(model, "feature_importances_"):
        return
    importances = pd.Series(model.feature_importances_, index=feature_names).sort_values()
    fig, ax = plt.subplots(figsize=(7, 6))
    importances.tail(15).plot.barh(color=PALETTE[1], ax=ax)
    ax.set_title(f"Feature Importance — {model_name}")
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "feature_importance.png"), dpi=110)
    plt.close(fig)


# ------------------------------------------------------------------ #
# DATABASE INIT
# ------------------------------------------------------------------ #
def init_database():
    db_path = os.path.join(BASE, "database.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript("""
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
    """)
    conn.commit()
    conn.close()
    print(f"Database initialized at {db_path}")


# ------------------------------------------------------------------ #
# MAIN PIPELINE
# ------------------------------------------------------------------ #
def main():
    df = load_dataset()
    df = clean_data(df)
    df = engineer_features(df)
    generate_eda_charts(df)

    df_encoded, encoders = encode_features(df.copy())

    X = df_encoded[FEATURE_COLS]
    y = df_encoded[TARGET_COL]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    results, fitted_models, best_name = train_and_compare(
        X_train_scaled, X_test_scaled, y_train, y_test
    )
    best_model = fitted_models[best_name]
    generate_feature_importance(best_model, FEATURE_COLS, best_name)

    # Model comparison bar chart
    comp_df = pd.DataFrame(results).T
    fig, ax = plt.subplots(figsize=(8, 5))
    comp_df[["accuracy", "precision", "recall", "f1_score"]].plot.bar(
        ax=ax, color=PALETTE
    )
    ax.set_title("Model Comparison")
    ax.set_ylim(0, 1)
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(CHARTS_DIR, "model_comparison.png"), dpi=110)
    plt.close(fig)

    # Persist artifacts
    joblib.dump(best_model, os.path.join(MODEL_DIR, "saved_model.pkl"))
    joblib.dump(encoders, os.path.join(MODEL_DIR, "encoder.pkl"))
    joblib.dump(scaler, os.path.join(MODEL_DIR, "scaler.pkl"))
    joblib.dump(FEATURE_COLS, os.path.join(MODEL_DIR, "feature_columns.pkl"))

    metrics_payload = {
        "best_model": best_name,
        "results": results,
        "trained_rows": int(len(df)),
        "test_rows": int(len(X_test)),
    }
    with open(os.path.join(MODEL_DIR, "metrics.json"), "w") as f:
        json.dump(metrics_payload, f, indent=2)

    init_database()
    print("\nTraining complete. Model, encoders, scaler, and metrics saved to /model.")


if __name__ == "__main__":
    main()
