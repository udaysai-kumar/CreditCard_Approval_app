"""
generate_dataset.py
--------------------
Generates a realistic synthetic credit-card-application dataset.

NOTE: This sandbox has no internet access, so the real Kaggle
"Credit Card Approval Prediction" dataset (application_record.csv +
credit_record.csv) cannot be downloaded. This script produces a
synthetic dataset with the SAME COLUMN SCHEMA and realistic,
correlated distributions, so the rest of the pipeline (cleaning,
feature engineering, encoding, model training/comparison) runs
exactly as it would on the real data.

To use the REAL dataset instead: download application_record.csv and
credit_record.csv from Kaggle ("Credit Card Approval Prediction" by
rikdifos) and drop them into this dataset/ folder with those exact
names, then skip this script -- train_model.py will use them directly
if present.
"""

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)
N = 8000


def generate():
    gender = RNG.choice(["M", "F"], size=N, p=[0.45, 0.55])
    own_car = RNG.choice(["Y", "N"], size=N, p=[0.4, 0.6])
    own_realty = RNG.choice(["Y", "N"], size=N, p=[0.55, 0.45])
    children = RNG.poisson(0.5, size=N).clip(0, 5)

    income_type = RNG.choice(
        ["Working", "Commercial associate", "Pensioner", "State servant", "Student"],
        size=N, p=[0.5, 0.23, 0.15, 0.1, 0.02],
    )
    base_income = np.select(
        [income_type == "Working", income_type == "Commercial associate",
         income_type == "Pensioner", income_type == "State servant",
         income_type == "Student"],
        [180000, 230000, 120000, 160000, 60000],
    )
    income = np.abs(RNG.normal(base_income, base_income * 0.35)).round(-2)

    education_type = RNG.choice(
        ["Secondary / secondary special", "Higher education",
         "Incomplete higher", "Lower secondary", "Academic degree"],
        size=N, p=[0.55, 0.3, 0.08, 0.05, 0.02],
    )
    family_status = RNG.choice(
        ["Married", "Single / not married", "Civil marriage", "Separated", "Widow"],
        size=N, p=[0.55, 0.2, 0.1, 0.1, 0.05],
    )
    housing_type = RNG.choice(
        ["House / apartment", "With parents", "Municipal apartment",
         "Rented apartment", "Office apartment", "Co-op apartment"],
        size=N, p=[0.7, 0.1, 0.08, 0.07, 0.03, 0.02],
    )

    age_years = RNG.integers(21, 65, size=N)
    days_birth = -(age_years * 365 + RNG.integers(0, 365, size=N))

    employed = RNG.random(N) > 0.07  # ~7% unemployed / pensioners w/ no job
    emp_years = np.where(employed, RNG.integers(0, 40, size=N), 0)
    days_employed = np.where(employed, -(emp_years * 365 + RNG.integers(0, 365, size=N)), 365243)

    occupation_type = RNG.choice(
        ["Laborers", "Core staff", "Sales staff", "Managers", "Drivers",
         "High skill tech staff", "Accountants", "Medicine staff",
         "Cooking staff", "Security staff", "Cleaning staff",
         "Private service staff", "Low-skill Laborers", "Secretaries",
         "Waiters/barmen staff", "Realty agents", "HR staff", "IT staff"],
        size=N,
    )
    occupation_type = occupation_type.astype(object)
    occupation_type[~employed] = None

    flag_work_phone = RNG.choice([0, 1], size=N, p=[0.8, 0.2])
    flag_phone = RNG.choice([0, 1], size=N, p=[0.6, 0.4])
    flag_email = RNG.choice([0, 1], size=N, p=[0.7, 0.3])
    cnt_fam_members = (children + RNG.choice([1, 2], size=N, p=[0.35, 0.65])).clip(1, 8)

    # ---- credit history proxy fields (from the Credit_History entity) ----
    months_balance = RNG.integers(1, 61, size=N)
    overdue_status = RNG.choice([0, 1, 2, 3], size=N, p=[0.82, 0.11, 0.05, 0.02])

    # ---- target: APPROVED (1) / REJECTED (0) ----
    # A believable, weighted risk score drives approval probability.
    score = (
        0.35
        + 0.15 * (income > np.median(income))
        + 0.10 * employed
        + 0.08 * (own_realty == "Y")
        + 0.05 * (own_car == "Y")
        + 0.10 * (emp_years >= 2)
        + 0.10 * (education_type == "Higher education")
        - 0.20 * (overdue_status >= 2)
        - 0.08 * (children >= 3)
        - 0.05 * (age_years < 23)
    )
    score = np.clip(score, 0.03, 0.97)
    approved = RNG.binomial(1, score)

    df = pd.DataFrame({
        "ID": np.arange(5008804, 5008804 + N),
        "CODE_GENDER": gender,
        "FLAG_OWN_CAR": own_car,
        "FLAG_OWN_REALTY": own_realty,
        "CNT_CHILDREN": children,
        "AMT_INCOME_TOTAL": income,
        "NAME_INCOME_TYPE": income_type,
        "NAME_EDUCATION_TYPE": education_type,
        "NAME_FAMILY_STATUS": family_status,
        "NAME_HOUSING_TYPE": housing_type,
        "DAYS_BIRTH": days_birth,
        "DAYS_EMPLOYED": days_employed,
        "FLAG_MOBIL": 1,
        "FLAG_WORK_PHONE": flag_work_phone,
        "FLAG_PHONE": flag_phone,
        "FLAG_EMAIL": flag_email,
        "OCCUPATION_TYPE": occupation_type,
        "CNT_FAM_MEMBERS": cnt_fam_members,
        "MONTHS_BALANCE": months_balance,
        "OVERDUE_STATUS": overdue_status,
        "APPROVED": approved,
    })

    # Inject a few duplicates and missing values, matching the workflow
    # steps described in the internship doc (dedupe + missing-value handling).
    dup_idx = RNG.choice(df.index, size=40, replace=False)
    df = pd.concat([df, df.loc[dup_idx]], ignore_index=True)
    miss_idx = RNG.choice(df.index, size=60, replace=False)
    df.loc[miss_idx, "AMT_INCOME_TOTAL"] = np.nan

    return df


if __name__ == "__main__":
    data = generate()
    out_path = "dataset/credit_card_applications.csv"
    data.to_csv(out_path, index=False)
    print(f"Generated {len(data)} rows -> {out_path}")
    print(data["APPROVED"].value_counts(normalize=True))
