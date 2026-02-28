"""
============================================================
Model Training with Real Fairness Metadata
============================================================
Trains ensemble models and saves real fairness metadata
(region, university_tier, career_gap - NOT synthetic demographics)
============================================================
"""

import os
import json
import joblib
from pathlib import Path
from pprint import pprint

import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split, StratifiedKFold, RandomizedSearchCV
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.metrics import f1_score, classification_report, confusion_matrix, roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier, VotingClassifier
from sklearn.calibration import CalibratedClassifierCV
from scipy.stats import randint, uniform

# Optional models
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except:
    XGBOOST_AVAILABLE = False

try:
    from catboost import CatBoostClassifier
    CATBOOST_AVAILABLE = True
except:
    CATBOOST_AVAILABLE = False

try:
    from interpret.glassbox import ExplainableBoostingClassifier
    EBM_AVAILABLE = True
except:
    EBM_AVAILABLE = False

import warnings
warnings.filterwarnings('ignore')

print("="*60)
print("MODEL TRAINING WITH REAL FAIRNESS METADATA")
print("="*60)

# ============================================================
# Path Configuration
# ============================================================

SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "results"

MODELS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

print(f"\n Data folder: {DATA_DIR}")
print(f" Models folder: {MODELS_DIR}")
print(f" Results folder: {REPORTS_DIR}")
print(f"\nAvailable: XGBoost={XGBOOST_AVAILABLE}, CatBoost={CATBOOST_AVAILABLE}, EBM={EBM_AVAILABLE}")

# ============================================================
# Load Data
# ============================================================

FEATURES_FILE = DATA_DIR / "features_labeled.csv"

if not FEATURES_FILE.exists():
    raise FileNotFoundError(f"{FEATURES_FILE} not found. Run 03_label_generation.py first.")

print(f"\n Loading: {FEATURES_FILE}")
df = pd.read_csv(FEATURES_FILE)
print(f" Loaded features: {df.shape}")

# Confirm target
if "attrition_risk" not in df.columns:
    raise ValueError("Target column 'attrition_risk' not found.")

# ============================================================
# Extract and Save Fairness Metadata (REAL, not synthetic)
# ============================================================

print("\n Extracting REAL fairness metadata...")

# Define fairness columns (from CV generator)
FAIRNESS_COLS = ["region", "university_tier", "has_career_gap", "career_gap_months"]

# Check if fairness columns exist
fairness_present = all(col in df.columns for col in FAIRNESS_COLS)

if fairness_present:
    fairness_metadata = df[["cv_id", "jd_id"] + FAIRNESS_COLS].copy()
    print(" Found real fairness metadata:")
    for col in FAIRNESS_COLS:
        print(f"  • {col}: {df[col].nunique()} unique values")
else:
    print("  Warning: Some fairness columns missing. Available columns:")
    print(df.columns.tolist())
    fairness_metadata = None

# Drop identifier and fairness columns from training data
id_cols = ["cv_id", "jd_id", "cv_file", "jd_title", "file", "candidate_id"]
present_id_cols = [c for c in id_cols if c in df.columns]

df = df.drop(columns=present_id_cols + FAIRNESS_COLS, errors="ignore")

# Also drop any synthetic demographic columns if they somehow exist
synthetic_cols = ["gender", "age_group", "education_level"]
df = df.drop(columns=synthetic_cols, errors="ignore")

print(f"\n Removed identifier and fairness columns from features")
print(f"Remaining columns: {len(df.columns)}")

# Shuffle
df = df.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

# ============================================================
# Train/Test Split
# ============================================================

print("\n Splitting data...")

X = df.drop(columns=["attrition_risk", "attrition_risk_label"], errors="ignore")
y = df["attrition_risk"].astype(int)

# Identify column types
cat_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()
num_cols = X.select_dtypes(include=[np.number]).columns.tolist()

print(f"Numeric features: {len(num_cols)}")
print(f"Categorical features: {len(cat_cols)}")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, stratify=y, random_state=RANDOM_SEED
)

print(f"Train: {X_train.shape}, Test: {X_test.shape}")

# ============================================================
# Save Test Data and Fairness Metadata
# ============================================================

print("\n Saving test data and fairness metadata...")

joblib.dump(X_test, MODELS_DIR / "X_test.pkl")
joblib.dump(y_test, MODELS_DIR / "y_test.pkl")
print(" Saved X_test.pkl and y_test.pkl")

# Save REAL fairness metadata (split to match test set)
if fairness_metadata is not None:
    # Match fairness metadata to test indices
    test_indices = X_test.index
    fairness_test = fairness_metadata.loc[test_indices].reset_index(drop=True)
    
    # Save as dict for easy loading
    fairness_meta_dict = {
        "region": fairness_test["region"].values.tolist(),
        "university_tier": fairness_test["university_tier"].values.tolist(),
        "has_career_gap": fairness_test["has_career_gap"].values.tolist(),
        "career_gap_months": fairness_test["career_gap_months"].values.tolist()
    }
    
    joblib.dump(fairness_meta_dict, MODELS_DIR / "fairness_meta_test.pkl")
    print(" Saved fairness_meta_test.pkl (REAL metadata)")
    print(f"   Contains: {list(fairness_meta_dict.keys())}")
else:
    print("  Fairness metadata not saved (columns missing)")

# ============================================================
# Preprocessing Pipeline
# ============================================================

print("\n Building preprocessing pipeline...")

numeric_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler())
])

categorical_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="constant", fill_value="__missing__")),
    ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
])

preprocessor = ColumnTransformer(
    transformers=[
        ("num", numeric_transformer, num_cols),
        ("cat", categorical_transformer, cat_cols)
    ],
    remainder="drop"
)

# Fit and transform
preprocessor.fit(X_train)
X_train_trans = preprocessor.transform(X_train)
print(f" After preprocessing: {X_train_trans.shape}")

# Save preprocessor
joblib.dump(preprocessor, MODELS_DIR / "scaler.pkl")
print(" Saved scaler.pkl")

# ============================================================
# Model Definitions
# ============================================================

print("\n Defining models...")

cv = StratifiedKFold(n_splits=4, shuffle=True, random_state=RANDOM_SEED)
N_ITER = 18

models_search = {}

# Logistic Regression
lr_pipe = Pipeline([
    ("pre", preprocessor),
    ("clf", LogisticRegression(max_iter=2000, multi_class="multinomial", random_state=RANDOM_SEED))
])
lr_param = {
    "clf__C": uniform(0.01, 10),
    "clf__class_weight": [None, "balanced"]
}
models_search["LogisticRegression"] = (lr_pipe, lr_param)

# Random Forest
rf_pipe = Pipeline([
    ("pre", preprocessor),
    ("clf", RandomForestClassifier(random_state=RANDOM_SEED, n_jobs=-1))
])
rf_param = {
    "clf__n_estimators": randint(100, 400),
    "clf__max_depth": randint(3, 20),
    "clf__min_samples_split": randint(2, 8),
    "clf__class_weight": [None, "balanced"]
}
models_search["RandomForest"] = (rf_pipe, rf_param)

# XGBoost or HistGradientBoosting
if XGBOOST_AVAILABLE:
    xgb_pipe = Pipeline([
        ("pre", preprocessor),
        ("clf", xgb.XGBClassifier(use_label_encoder=False, eval_metric="mlogloss", 
                                 random_state=RANDOM_SEED, n_jobs=-1))
    ])
    xgb_param = {
        "clf__n_estimators": randint(80, 400),
        "clf__max_depth": randint(3, 12),
        "clf__learning_rate": uniform(0.01, 0.3),
        "clf__subsample": uniform(0.6, 0.4),
        "clf__colsample_bytree": uniform(0.6, 0.4)
    }
    models_search["XGBoost"] = (xgb_pipe, xgb_param)
else:
    hgb_pipe = Pipeline([
        ("pre", preprocessor),
        ("clf", HistGradientBoostingClassifier(random_state=RANDOM_SEED))
    ])
    hgb_param = {
        "clf__max_iter": randint(80, 400),
        "clf__max_depth": randint(3, 20)
    }
    models_search["HistGB"] = (hgb_pipe, hgb_param)

# CatBoost
if CATBOOST_AVAILABLE:
    cat_pipe = Pipeline([
        ("pre", preprocessor),
        ("clf", CatBoostClassifier(verbose=0, random_state=RANDOM_SEED, thread_count=4))
    ])
    cat_param = {
        "clf__iterations": randint(100, 600),
        "clf__depth": randint(4, 10),
        "clf__learning_rate": uniform(0.01, 0.3)
    }
    models_search["CatBoost"] = (cat_pipe, cat_param)

# EBM
if EBM_AVAILABLE:
    ebm_pipe = Pipeline([
        ("pre", preprocessor),
        ("clf", ExplainableBoostingClassifier(random_state=RANDOM_SEED))
    ])
    ebm_param = {
        "clf__max_bins": [128],
        "clf__interactions": [0, 5, 10]
    }
    models_search["EBM"] = (ebm_pipe, ebm_param)

# ============================================================
# Hyperparameter Search
# ============================================================

print("\n" + "="*60)
print(" HYPERPARAMETER TUNING")
print("="*60)

search_results = {}
tuned_models = {}
cv_scores_summary = {}

for name, (pipe, param_dist) in models_search.items():
    print(f"\n→ Tuning {name}...")
    rs = RandomizedSearchCV(
        estimator=pipe,
        param_distributions=param_dist,
        n_iter=N_ITER,
        scoring="f1_macro",
        cv=cv,
        verbose=1,
        random_state=RANDOM_SEED,
        n_jobs=1
    )
    rs.fit(X_train, y_train)
    print(f"Best {name} params: {rs.best_params_}")
    print(f"Best CV F1-macro: {rs.best_score_:.4f}")
    
    search_results[name] = rs
    tuned_models[name] = rs.best_estimator_
    cv_scores_summary[name] = float(rs.best_score_)

# ============================================================
# Save Individual Models
# ============================================================

print("\n Saving individual base models...")

for name, model in tuned_models.items():
    if name == "LogisticRegression":
        joblib.dump(model, MODELS_DIR / "logreg.pkl")
        print(" Saved logreg.pkl")
    elif name == "RandomForest":
        joblib.dump(model, MODELS_DIR / "rf.pkl")
        print(" Saved rf.pkl")
    elif name == "XGBoost" or name == "HistGB":
        joblib.dump(model, MODELS_DIR / "xgb.pkl")
        print(" Saved xgb.pkl")
    elif name == "CatBoost":
        joblib.dump(model, MODELS_DIR / "cat.pkl")
        print(" Saved cat.pkl")
    elif name == "EBM":
        joblib.dump(model, MODELS_DIR / "ebm.pkl")
        print(" Saved ebm.pkl")

# ============================================================
# Evaluate on Test Set
# ============================================================

print("\n" + "="*60)
print(" EVALUATING ON TEST SET")
print("="*60)

def evaluate_on_test(name, model, X_test, y_test):
    y_pred = model.predict(X_test)
    try:
        y_proba = model.predict_proba(X_test)
        auc = roc_auc_score(y_test, y_proba, multi_class="ovr")
    except:
        y_proba = None
        auc = None
    
    f1 = f1_score(y_test, y_pred, average="macro")
    print(f"\n{name}")
    print(f"  F1-macro: {f1:.4f}")
    print(f"  ROC-AUC: {auc:.4f}" if auc else "  ROC-AUC: N/A")
    
    return {"f1": f1, "auc": auc, "y_pred": y_pred, "y_proba": y_proba}

eval_summary = {}
for name, model in tuned_models.items():
    res = evaluate_on_test(name, model, X_test, y_test)
    eval_summary[name] = res

# ============================================================
# Build Weighted Ensemble
# ============================================================

print("\n" + "="*60)
print(" BUILDING WEIGHTED ENSEMBLE")
print("="*60)

eps = 1e-6
names = list(cv_scores_summary.keys())
scores = np.array([cv_scores_summary[n] for n in names])
scores = np.maximum(scores, 0.0)

if scores.sum() == 0:
    weights = np.ones_like(scores)
else:
    weights = (scores + eps) / (scores + eps).sum()

weights_map = {n: float(w) for n, w in zip(names, weights)}
print("\nModel weights (proportional to CV F1-macro):")
pprint(weights_map)

# Save weights
with open(MODELS_DIR / "final_weights.json", "w") as f:
    json.dump(weights_map, f, indent=2)
print("\n Saved final_weights.json")

# Create ensemble
estimators = [(n, tuned_models[n]) for n in names]
voting = VotingClassifier(estimators=estimators, voting="soft", weights=list(weights), n_jobs=1)

print("\nFitting ensemble...")
voting.fit(X_train, y_train)

ensemble_res = evaluate_on_test("Ensemble (soft-weighted)", voting, X_test, y_test)
eval_summary["Ensemble"] = ensemble_res

# Calibrate ensemble
print("\nCalibrating ensemble...")
calibrated = CalibratedClassifierCV(estimator=voting, cv=3, method="isotonic")
calibrated.fit(X_train, y_train)

cal_res = evaluate_on_test("Ensemble (calibrated)", calibrated, X_test, y_test)
eval_summary["Ensemble_Calibrated"] = cal_res

# ============================================================
# Save Ensemble Models
# ============================================================

print("\n Saving ensemble models...")

joblib.dump(voting, MODELS_DIR / "ensemble_soft_weighted.joblib")
joblib.dump(calibrated, MODELS_DIR / "ensemble_soft_weighted_calibrated.joblib")

# Create final ensemble wrapper
class FinalEnsemble:
    def __init__(self, models_dict, weights, preprocessor):
        self.models = models_dict
        self.weights = weights
        self.preprocessor = preprocessor
    
    def predict_proba(self, X):
        X_proc = self.preprocessor.transform(X)
        probas = []
        for name, model in self.models.items():
            clf = model.named_steps["clf"]
            p = clf.predict_proba(X_proc)
            probas.append(self.weights[name] * p)
        return np.sum(probas, axis=0)
    
    def predict(self, X):
        proba = self.predict_proba(X)
        return np.argmax(proba, axis=1)

# Build final models dict
final_models_dict = {}
final_weights_short = {}

if "LogisticRegression" in tuned_models:
    final_models_dict["logreg"] = tuned_models["LogisticRegression"]
    final_weights_short["logreg"] = weights_map["LogisticRegression"]

if "RandomForest" in tuned_models:
    final_models_dict["rf"] = tuned_models["RandomForest"]
    final_weights_short["rf"] = weights_map["RandomForest"]

if "XGBoost" in tuned_models:
    final_models_dict["xgb"] = tuned_models["XGBoost"]
    final_weights_short["xgb"] = weights_map["XGBoost"]
elif "HistGB" in tuned_models:
    final_models_dict["xgb"] = tuned_models["HistGB"]
    final_weights_short["xgb"] = weights_map["HistGB"]

if "CatBoost" in tuned_models:
    final_models_dict["cat"] = tuned_models["CatBoost"]
    final_weights_short["cat"] = weights_map["CatBoost"]

final_ensemble = FinalEnsemble(final_models_dict, final_weights_short, preprocessor)
joblib.dump(final_ensemble, MODELS_DIR / "final_ensemble.pkl")
print(" Saved final_ensemble.pkl")

# ============================================================
# Save Training Report
# ============================================================

report = {
    "cv_scores": cv_scores_summary,
    "test_metrics": {
        k: {"f1": float(v["f1"]), "auc": float(v["auc"]) if v["auc"] else None} 
        for k, v in eval_summary.items()
    },
    "weights": weights_map,
    "features_used": {
        "num_cols": num_cols,
        "cat_cols": cat_cols,
        "total_features": len(num_cols) + len(cat_cols)
    },
    "fairness_metadata": {
        "columns": FAIRNESS_COLS if fairness_present else [],
        "note": "Using real structural fairness metadata (not synthetic demographics)"
    }
}

with open(REPORTS_DIR / "training_report.json", "w") as f:
    json.dump(report, f, indent=2)
print(" Saved training_report.json")

# ============================================================
# Feature Importance Export
# ============================================================

print("\n Exporting feature importances...")

def get_feature_names_from_preprocessor(preprocessor):
    num_features = num_cols
    cat_features = []
    if cat_cols:
        try:
            ohe = preprocessor.named_transformers_["cat"].named_steps["onehot"]
            cat_names = ohe.get_feature_names_out(cat_cols).tolist()
            cat_features = cat_names
        except:
            cat_features = cat_cols
    return num_features + cat_features

try:
    feature_names_after_preproc = get_feature_names_from_preprocessor(preprocessor)
except:
    feature_names_after_preproc = num_cols + cat_cols

for name, model in tuned_models.items():
    try:
        clf = model.named_steps["clf"] if hasattr(model, "named_steps") else model
        if hasattr(clf, "feature_importances_"):
            fi = clf.feature_importances_
            df_fi = pd.DataFrame({
                "feature": feature_names_after_preproc[:len(fi)],
                "importance": fi
            }).sort_values("importance", ascending=False)
            fn = REPORTS_DIR / f"feature_importances_{name}.csv"
            df_fi.to_csv(fn, index=False)
            print(f" Saved importances for {name}")
    except Exception as e:
        print(f"  Could not export importances for {name}: {e}")

# EBM global explanations
if EBM_AVAILABLE and "EBM" in tuned_models:
    try:
        ebm_model = tuned_models["EBM"].named_steps["clf"]
        ebm_global = ebm_model.explain_global()
        joblib.dump(ebm_global, REPORTS_DIR / "ebm_global.joblib")
        print(" Saved EBM global explanation")
    except Exception as e:
        print(f"  EBM explanation failed: {e}")

# ============================================================
# Summary
# ============================================================

print("\n" + "="*60)
print(" MODEL TRAINING COMPLETED")
print("="*60)
print(f"\n Models saved in: {MODELS_DIR}")
print(f" Reports saved in: {REPORTS_DIR}")

print("\n Best Model Performance:")
best_model = max(eval_summary.items(), key=lambda x: x[1]["f1"])
print(f"  {best_model[0]}: F1={best_model[1]['f1']:.4f}")

print("\n Fairness Metadata Status:")
if fairness_present:
    print("   Real structural fairness metadata saved")
    print(f"  Contains: {FAIRNESS_COLS}")
else:
    print("    Fairness metadata not available")

print("="*60)