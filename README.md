# AI Credit Card Approval Prediction System

**Intelligent Banking Decision Support using Machine Learning**

An end-to-end web application that predicts whether a credit-card application
should be **Approved** or **Rejected**, using a machine-learning model trained
and compared across four algorithms, served through a Flask banking-style
dashboard.

---

## 1. Project Overview

| | |
|---|---|
| **Frontend** | HTML5, CSS3 (custom design system), vanilla JavaScript, Font Awesome |
| **Backend** | Python, Flask (application-factory + Blueprint architecture) |
| **ML** | pandas, NumPy, scikit-learn, Matplotlib, Seaborn, Joblib |
| **Database** | SQLite (`Users`, `ApplicantDetails`, `PredictionHistory`) |
| **Auth** | Session-based login, Werkzeug password hashing |

The system covers the full pipeline described in the internship brief:
data loading → cleaning → feature engineering → encoding → train/test split →
scaling → multi-model training & comparison → best-model selection →
persistence → a Flask web app that serves real-time predictions and stores
every result for audit/history.

> **Dataset note:** this sandbox has no internet access, so the real Kaggle
> "Credit Card Approval Prediction" CSVs (`application_record.csv` +
> `credit_record.csv`) could not be downloaded. `dataset/generate_dataset.py`
> generates a synthetic dataset with the **same column schema** and
> realistic, correlated distributions, so every later step (cleaning,
> feature engineering, encoding, training, comparison) runs exactly as it
> would on the real data. **To use the real dataset:** download
> `application_record.csv` and `credit_record.csv` from Kaggle, merge them
> so the result has an `APPROVED` target column, and drop the file in as
> `dataset/application_record.csv` — `train_model.py` will use it
> automatically instead of the synthetic data.

---

## 2. Installation

```bash
# 1. Clone / unzip the project, then move into it
cd CreditCardApproval

# 2. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Generate the dataset, train the model, and initialize the database
python train_model.py

# 5. Run the Flask app
python app.py
```

Open **http://127.0.0.1:5000/** in your browser, register an account, and
run your first prediction.

---

## 3. Folder Structure

```
CreditCardApproval/
├── app.py                     # Flask app factory / entry point
├── config.py                  # App configuration
├── db.py                      # SQLite data-access layer + schema
├── predict.py                 # Inference helper (loads model/encoder/scaler)
├── train_model.py             # Full ML training pipeline
├── requirements.txt
├── README.md
├── database.db                # Created on first run
├── app_blueprints/
│   ├── auth.py                # Register / login / logout / session mgmt
│   └── main.py                # Landing, dashboard, predict, history, etc.
├── dataset/
│   ├── generate_dataset.py    # Synthetic dataset generator
│   └── credit_card_applications.csv
├── model/
│   ├── saved_model.pkl        # Best-performing trained model
│   ├── encoder.pkl            # LabelEncoders per categorical column
│   ├── scaler.pkl             # StandardScaler
│   ├── feature_columns.pkl    # Feature order used at inference time
│   └── metrics.json           # Accuracy/Precision/Recall/F1/ROC-AUC per model
├── templates/                 # 14 Jinja2 HTML pages (see below)
└── static/
    ├── css/style.css          # Design system (banking / glassmorphism)
    ├── js/main.js              # Validation, counters, gauges, theming
    └── images/charts/         # Auto-generated EDA + model charts
```

## 4. Pages

Landing · About · Register · Login · Dashboard · New Prediction ·
Prediction Result · Prediction History · Model Performance ·
Data Visualizations · Contact · 404 · 500

## 5. Machine Learning Workflow

1. **Load** — real Kaggle CSVs if present, else synthetic fallback.
2. **Clean** — drop duplicates, impute missing income, fill missing
   occupation with "Unemployed".
3. **Feature engineering** — convert `DAYS_BIRTH`/`DAYS_EMPLOYED` into
   `AGE_YEARS` / `EMPLOYED_YEARS`.
4. **Encode** — `LabelEncoder` per categorical column, persisted for
   inference-time reuse.
5. **Split & scale** — 80/20 stratified split, `StandardScaler`.
6. **Train & compare** — Logistic Regression, Decision Tree, Random Forest,
   Gradient Boosting (XGBoost stand-in) — scored on Accuracy, Precision,
   Recall, F1, ROC-AUC.
7. **Select & persist** — highest-F1 model saved via Joblib, along with
   encoders, scaler, and `metrics.json`.
8. **Visualize** — income/gender/education/approval distributions,
   correlation heatmap, ROC curves, confusion matrices, feature importance,
   and a model-comparison bar chart — all written to
   `static/images/charts/`.

## 6. Results

Results vary by run/dataset seed; from the bundled synthetic dataset, the
Gradient Boosting model was automatically selected as best performer. Full
per-model metrics are always viewable live at **/performance** after
training, and are stored in `model/metrics.json`.

## 7. Future Scope

- Swap in the real Kaggle dataset (see note above) for production-realistic
  metrics.
- Add XGBoost proper (`pip install xgboost`) as a fifth candidate model.
- Add role-based admin views for reviewing all users' predictions.
- Deploy behind Gunicorn + Nginx (or a managed platform) with a production
  `SECRET_KEY` and a hardened database (e.g., PostgreSQL).
- Add SHAP-based per-prediction explainability on the result page.

---

**Disclaimer:** This is an academic / internship-portfolio project. It is
trained on synthetic data and is not connected to any real bank or credit
bureau. It must not be used for real lending decisions.
