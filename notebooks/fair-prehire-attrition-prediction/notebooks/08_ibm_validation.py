"""
============================================================
IBM HR Dataset Validation
============================================================
Purpose:
- Load IBM HR attrition dataset
- Map features to match the model's feature space
- Train baseline model on IBM data
- Test the trained model on IBM data (transfer learning)
- Compare performance and generalization
============================================================
"""

import os
import pandas as pd
import numpy as np
import joblib
import json
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import f1_score, accuracy_score, roc_auc_score, confusion_matrix, classification_report
from sklearn.ensemble import RandomForestClassifier
import warnings
warnings.filterwarnings('ignore')

print("="*60)
print("IBM HR DATASET VALIDATION")
print("="*60)

# ============================================================
# Define FinalEnsemble class BEFORE loading
# ============================================================

class FinalEnsemble:
    """Custom ensemble wrapper - must be defined before unpickling"""
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
        
        weighted_proba = np.sum(probas, axis=0)
        row_sums = weighted_proba.sum(axis=1, keepdims=True)
        normalized_proba = weighted_proba / row_sums
        return normalized_proba
    
    def predict(self, X):
        proba = self.predict_proba(X)
        return np.argmax(proba, axis=1)

# ============================================================
# Auto-Detecting Paths
# ============================================================

SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent

DATA_DIR = PROJECT_ROOT / "data" 
MODEL_DIR = PROJECT_ROOT / "models"
RESULTS_DIR = PROJECT_ROOT / "results"
ARTIFACT_DIR = RESULTS_DIR / "artifacts" / "ibm_validation"

# Create folders
for folder in [DATA_DIR, MODEL_DIR, RESULTS_DIR, ARTIFACT_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

IBM_PATH = DATA_DIR / "ibm_hr.csv"

print(f"\n Project root: {PROJECT_ROOT}")
print(f" IBM data path: {IBM_PATH}")
print(f" Models folder: {MODEL_DIR}")
print(f" Output folder: {ARTIFACT_DIR}")

# ============================================================
# Load IBM Dataset
# ============================================================

print("\n Loading IBM HR Dataset...")

if not IBM_PATH.exists():
    print(f" Error: IBM dataset not found at {IBM_PATH}")
    print("\n Please download from:")
    print("https://www.kaggle.com/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset")
    print(f"\nPlace it in: {IBM_PATH}")
    exit(1)

df = pd.read_csv(IBM_PATH)
print(f" Loaded IBM data: {df.shape}")
print(f"\nFirst few columns: {df.columns[:10].tolist()}")
print(f"\nAttrition distribution:\n{df['Attrition'].value_counts()}")

# ============================================================
# 1. Create Comparable Target Labels
# ============================================================

print("\n Creating comparable target labels...")

def map_ibm_label(row):
    """
    Map IBM attrition to the 3-class system:
    0 = High risk (leaves < 6 months / early quit)
    1 = Medium risk (leaves 6-12 months)  
    2 = Low risk (stays > 1 year)
    
    Note: IBM doesn't have exact departure dates, so YearsAtCompany is used
    as a proxy for tenure patterns
    """
    if row["Attrition"] == "Yes":
        # Left the company
        if row["YearsAtCompany"] < 1:
            return 0  # High risk - early quit
        elif row["YearsAtCompany"] < 2:
            return 1  # Medium risk - quit after 1-2 years
        else:
            return 1  # Putting longer tenures into medium to avoid sparse class
    else:
        # Still at company
        return 2  # Low risk - stayed

df["attrition_risk"] = df.apply(map_ibm_label, axis=1)

print("\n Label distribution:")
print(df["attrition_risk"].value_counts().sort_index())
print(f"\nClass proportions:")
for i in range(3):
    prop = (df["attrition_risk"] == i).mean()
    label = ["High Risk (0-6mo)", "Medium Risk (6-12mo)", "Low Risk (>12mo)"][i]
    print(f"  {label}: {prop:.1%}")

# ============================================================
# 2. Feature Engineering from IBM Data
# ============================================================

print("\n Engineering features to match the model...")

# Load trained model's feature names
try:
    X_test_sample = joblib.load(MODEL_DIR / "X_test.pkl")
    expected_features = X_test_sample.columns.tolist()
    print(f"\n Model expects {len(expected_features)} features:")
    for i, feat in enumerate(expected_features, 1):
        print(f"  {i}. {feat}")
except:
    print("  Could not load X_test.pkl, will use default feature set")
    expected_features = None

print("\n  IMPORTANT NOTE:")
print("IBM dataset lacks some CV-specific features (skill_match, title_similarity, etc.)")
print("These will be approximated with reasonable defaults for generalization testing.\n")

# Create feature mappings from IBM to the model
# Note: Some features are approximated as IBM doesn't have exact equivalents
ibm_features = pd.DataFrame({
    # Experience-based features
    "total_exp_years": df["TotalWorkingYears"],
    "total_exp_months": df["TotalWorkingYears"] * 12,
    "avg_tenure_months": df["YearsInCurrentRole"] * 12,
    "current_job_tenure": df["YearsInCurrentRole"] * 12,
    "min_tenure_months": df["YearsInCurrentRole"] * 12 * 0.8,  # Approximate
    "max_tenure_months": df["YearsInCurrentRole"] * 12 * 1.2,  # Approximate
    
    # Job hopping indicators
    "total_jobs": df["NumCompaniesWorked"],
    "short_stints_count": np.where(df["NumCompaniesWorked"] > 3, 2, 0),  # Approximate
    "very_short_stints_count": np.where(df["NumCompaniesWorked"] > 5, 1, 0),  # Approximate
    "job_hopping_rate": df["NumCompaniesWorked"] / (df["TotalWorkingYears"] + 1),
    
    # Career progression
    "has_progression": np.where(df["JobLevel"] >= 3, 1, 0),
    
    # Education
    "has_masters": np.where(df["Education"] >= 4, 1, 0),
    
    # Skills & Certifications (approximated)
    "n_skills": np.random.randint(8, 18, len(df)),  # Reasonable range
    "n_certifications": np.where(df["Education"] >= 4, 2, np.where(df["Education"] >= 3, 1, 0)),
    
    # Location/Remote (approximated - assume all on-site)
    "is_remote": np.zeros(len(df)),
    
    # Matching scores (approximated with reasonable defaults)
    "skill_match_score": np.random.uniform(0.5, 0.85, len(df)),  # Moderate to good match
    "title_match_score": np.random.uniform(0.6, 0.9, len(df)),   # Reasonable title match
    "exp_match_score": 1 - (df["NumCompaniesWorked"] / 10).clip(0, 0.5),  # Based on job switches
    "edu_match_score": np.where(df["Education"] >= 3, 1, 0.7),
    "location_match_score": np.ones(len(df)) * 0.8,  # Assume decent location match
    "overall_match_score": np.random.uniform(0.55, 0.8, len(df)),
    
    # Qualification flags
    "is_overqualified": np.where((df["Education"] >= 5) & (df["JobLevel"] <= 2), 1, 0),
    "is_underqualified": np.where((df["Education"] <= 2) & (df["JobLevel"] >= 3), 1, 0),
    
    # Work mode
    "work_mode_mismatch": np.zeros(len(df))  # Assume no mismatch
})

# Ensuring that the features expected by the model are obtained
if expected_features:
    # Add any missing features with default values
    for feat in expected_features:
        if feat not in ibm_features.columns:
            print(f"    Adding missing feature '{feat}' with default value 0")
            ibm_features[feat] = 0
    
    # Reorder to match expected order
    ibm_features = ibm_features[expected_features]
    print(f"\n Features aligned: {ibm_features.shape}")
else:
    print(f"\n Created feature matrix: {ibm_features.shape}")

X_ibm = ibm_features.fillna(0)
y_ibm = df["attrition_risk"]

print(f"\n Feature summary (first 5 features):")
print(X_ibm.iloc[:, :5].describe().round(2))

# ============================================================
# 3. Baseline Model on IBM Data
# ============================================================

print("\n" + "="*60)
print(" TRAINING BASELINE MODEL ON IBM DATA")
print("="*60)

X_train, X_test, y_train, y_test = train_test_split(
    X_ibm, y_ibm, test_size=0.2, random_state=42, stratify=y_ibm
)

print(f"Train: {X_train.shape}, Test: {X_test.shape}")
print(f"\nTrain label distribution:")
print(y_train.value_counts().sort_index())

# Train Random Forest baseline
rf_ibm = RandomForestClassifier(
    n_estimators=200,
    max_depth=10,
    random_state=42,
    n_jobs=-1,
    class_weight='balanced'  # Handle class imbalance
)

print("\n Training Random Forest on IBM data...")
rf_ibm.fit(X_train, y_train)
y_pred_baseline = rf_ibm.predict(X_test)

# Evaluate baseline
f1_baseline = f1_score(y_test, y_pred_baseline, average="macro")
acc_baseline = accuracy_score(y_test, y_pred_baseline)

print("\n IBM Baseline Model Results:")
print(f"F1-macro: {f1_baseline:.4f}")
print(f"Accuracy: {acc_baseline:.4f}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred_baseline, 
                          target_names=["High Risk (<6mo)", "Medium Risk (6-12mo)", "Low Risk (>12mo)"],
                          digits=4))

# Confusion matrix
cm_baseline = confusion_matrix(y_test, y_pred_baseline)
fig, ax = plt.subplots(figsize=(8, 6))
sns.heatmap(cm_baseline, annot=True, fmt="d", cmap="Blues",
            xticklabels=["High", "Medium", "Low"],
            yticklabels=["High", "Medium", "Low"],
            ax=ax)
ax.set_title("IBM Baseline Model - Confusion Matrix\n(Random Forest trained on IBM data)", 
            fontsize=12, fontweight='bold')
ax.set_xlabel("Predicted", fontsize=11)
ax.set_ylabel("Actual", fontsize=11)
plt.tight_layout()
cm_path = ARTIFACT_DIR / "ibm_baseline_cm.png"
plt.savefig(cm_path, dpi=150, bbox_inches='tight')
print(f"\n Saved: {cm_path}")
plt.close()

# Save baseline model
joblib.dump(rf_ibm, ARTIFACT_DIR / "ibm_baseline.pkl")
print(f" Saved baseline model")

# ============================================================
# 4. Transfer Learning - Trained Model on IBM Data
# ============================================================

print("\n" + "="*60)
print(" TESTING TRAINED MODEL ON IBM DATA (TRANSFER LEARNING)")
print("="*60)

# Load the trained model
print("\n Loading the trained model...")

ensemble_files = [
    ("ensemble_soft_weighted_calibrated.joblib", "Calibrated Ensemble"),
    ("ensemble_soft_weighted.joblib", "Weighted Ensemble"),
    ("final_ensemble.pkl", "Custom Ensemble")
]

final_model = None
model_name = None

for filename, name in ensemble_files:
    filepath = MODEL_DIR / filename
    if filepath.exists():
        try:
            final_model = joblib.load(filepath)
            model_name = name
            print(f" Loaded {name} ({filename})")
            break
        except Exception as e:
            print(f"  Failed to load {filename}: {e}")
            continue

if final_model is None:
    print(" Error: No ensemble model could be loaded.")
    print("\nAvailable models:")
    for file in MODEL_DIR.glob("*.pkl"):
        print(f"  • {file.name}")
    for file in MODEL_DIR.glob("*.joblib"):
        print(f"  • {file.name}")
    exit(1)

# Test on full IBM dataset
print("\n Generating predictions on full IBM dataset...")
try:
    y_pred_transfer = final_model.predict(X_ibm)
    
    # Evaluate transfer performance
    f1_transfer = f1_score(y_ibm, y_pred_transfer, average="macro")
    acc_transfer = accuracy_score(y_ibm, y_pred_transfer)
    
    print("\n Trained Model on IBM Data (Zero-Shot Transfer):")
    print(f"F1-macro: {f1_transfer:.4f}")
    print(f"Accuracy: {acc_transfer:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_ibm, y_pred_transfer,
                              target_names=["High Risk (<6mo)", "Medium Risk (6-12mo)", "Low Risk (>12mo)"],
                              digits=4))
    
    # Confusion matrix
    cm_transfer = confusion_matrix(y_ibm, y_pred_transfer)
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(cm_transfer, annot=True, fmt="d", cmap="Greens",
                xticklabels=["High", "Medium", "Low"],
                yticklabels=["High", "Medium", "Low"],
                ax=ax)
    ax.set_title(f"{model_name} on IBM Dataset\n(Zero-shot transfer learning)", 
                fontsize=12, fontweight='bold')
    ax.set_xlabel("Predicted", fontsize=11)
    ax.set_ylabel("Actual", fontsize=11)
    plt.tight_layout()
    cm_path = ARTIFACT_DIR / "trained_model_ibm_cm.png"
    plt.savefig(cm_path, dpi=150, bbox_inches='tight')
    print(f"\n Saved: {cm_path}")
    plt.close()
    
except Exception as e:
    print(f" Error during transfer learning: {e}")
    import traceback
    traceback.print_exc()
    print("\nThis might be due to feature mismatch.")
    print(f"Model input shape: {X_ibm.shape}")
    print(f"Features: {X_ibm.columns.tolist()[:5]}...")
    exit(1)

# ============================================================
# 5. Performance Comparison
# ============================================================

print("\n" + "="*60)
print(" PERFORMANCE COMPARISON")
print("="*60)

comparison = {
    "model_tested": model_name,
    "dataset": {
        "name": "IBM HR Analytics Attrition Dataset",
        "size": int(len(df)),
        "test_size": int(len(X_test))
    },
    "ibm_baseline": {
        "f1_macro": float(f1_baseline),
        "accuracy": float(acc_baseline),
        "description": "Random Forest trained directly on IBM data"
    },
    "trained_model_transfer": {
        "f1_macro": float(f1_transfer),
        "accuracy": float(acc_transfer),
        "description": f"{model_name} tested on IBM data (zero-shot)"
    },
    "performance_comparison": {
        "f1_difference": float(f1_baseline - f1_transfer),
        "f1_difference_percent": float((f1_baseline - f1_transfer) / f1_baseline * 100) if f1_baseline > 0 else 0,
        "accuracy_difference": float(acc_baseline - acc_transfer)
    }
}

print(f"\n{'Model':<30} {'F1-Macro':<12} {'Accuracy':<12}")
print("="*54)
print(f"{'IBM Baseline (trained)':<30} {f1_baseline:<12.4f} {acc_baseline:<12.4f}")
print(f"{'Trained Model (zero-shot)':<30} {f1_transfer:<12.4f} {acc_transfer:<12.4f}")
print("="*54)
print(f"{'Difference':<30} {comparison['performance_comparison']['f1_difference']:<12.4f} {comparison['performance_comparison']['accuracy_difference']:<12.4f}")
print(f"{'Relative drop':<30} {comparison['performance_comparison']['f1_difference_percent']:<11.1f}%")

# Assess generalization
if f1_transfer >= f1_baseline * 0.85:
    print("\n ✓ EXCELLENT GENERALIZATION!")
    print("   The model performs within 15% of baseline on external data.")
    print("   Strong adaptation despite different data distributions.")
    print("   This validates the robustness of the approach.")
    generalization_status = "excellent"
    generalization_color = "green"
elif f1_transfer >= f1_baseline * 0.70:
    print("\n ⚠ MODERATE GENERALIZATION")
    print("   The model shows reasonable generalization with expected performance drop (15-30%).")
    generalization_status = "moderate"
    generalization_color = "orange"
else:
    print("\n ✗ POOR GENERALIZATION")
    print("   Significant performance gap detected.")
    print("   Model may be overfitted to training domain.")
    print("   Consider domain adaptation or retraining with diverse data.")
    generalization_status = "poor"
    generalization_color = "red"

comparison["generalization"] = {
    "status": generalization_status,
    "threshold_met": f1_transfer >= f1_baseline * 0.85
}

# Visualization
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Bar chart comparison
ax1 = axes[0]
models = ["IBM Baseline\n(Trained on IBM)", f"Trained Model\n(Zero-shot)"]
f1_scores = [f1_baseline, f1_transfer]
accuracies = [acc_baseline, acc_transfer]

x = np.arange(len(models))
width = 0.35

bars1 = ax1.bar(x - width/2, f1_scores, width, label='F1-Macro', color='steelblue', edgecolor='black')
bars2 = ax1.bar(x + width/2, accuracies, width, label='Accuracy', color='coral', edgecolor='black')

ax1.set_xlabel('Model', fontsize=11, fontweight='bold')
ax1.set_ylabel('Score', fontsize=11, fontweight='bold')
ax1.set_title('IBM Dataset Validation: Model Comparison', fontsize=12, fontweight='bold')
ax1.set_xticks(x)
ax1.set_xticklabels(models)
ax1.set_ylim(0, 1)
ax1.legend(loc='lower right')
ax1.grid(axis='y', alpha=0.3)

# Add value labels
for i, (f1, acc) in enumerate(zip(f1_scores, accuracies)):
    ax1.text(i - width/2, f1 + 0.02, f'{f1:.3f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax1.text(i + width/2, acc + 0.02, f'{acc:.3f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

# Performance drop visualization
ax2 = axes[1]
categories = ['F1-Macro', 'Accuracy']
baseline_scores = [f1_baseline, acc_baseline]
trained_scores = [f1_transfer, acc_transfer]

x2 = np.arange(len(categories))
width2 = 0.35

ax2.bar(x2 - width2/2, baseline_scores, width2, label='IBM Baseline', color='steelblue', edgecolor='black')
ax2.bar(x2 + width2/2, trained_scores, width2, label='Trained Model', color='coral', edgecolor='black')

ax2.set_xlabel('Metric', fontsize=11, fontweight='bold')
ax2.set_ylabel('Score', fontsize=11, fontweight='bold')
ax2.set_title('Performance Drop Analysis', fontsize=12, fontweight='bold')
ax2.set_xticks(x2)
ax2.set_xticklabels(categories)
ax2.set_ylim(0, 1)
ax2.legend()
ax2.grid(axis='y', alpha=0.3)

# Add value labels and drop %
for i, (base, trained) in enumerate(zip(baseline_scores, trained_scores)):
    ax2.text(i - width2/2, base + 0.02, f'{base:.3f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
    ax2.text(i + width2/2, trained + 0.02, f'{trained:.3f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
    drop_pct = (base - trained) / base * 100
    ax2.text(i, (base + trained) / 2, f'↓{drop_pct:.1f}%', ha='center', va='center', 
            fontsize=9, color='red', fontweight='bold')

plt.tight_layout()
comp_path = ARTIFACT_DIR / "ibm_comparison.png"
plt.savefig(comp_path, dpi=150, bbox_inches='tight')
print(f"\n Saved comparison plot: {comp_path}")
plt.close()

# ============================================================
# 6. Save Summary
# ============================================================

summary_path = ARTIFACT_DIR / "ibm_validation_summary.json"
with open(summary_path, "w") as f:
    json.dump(comparison, f, indent=2)
print(f" Saved summary: {summary_path}")

# ============================================================
# Final Report
# ============================================================

print("\n" + "="*60)
print(" IBM VALIDATION COMPLETED")
print("="*60)

print(f"\n All artifacts saved to: {ARTIFACT_DIR}")

print("\n Key Findings:")
print(f"  • IBM dataset size: {len(df)} employees")
print(f"  • Test set size: {len(X_test)} employees")
print(f"  • Baseline F1 (trained on IBM): {f1_baseline:.4f}")
print(f"  • Transfer F1 (trained model): {f1_transfer:.4f}")
print(f"  • Performance gap: {abs(f1_baseline - f1_transfer):.4f} ({comparison['performance_comparison']['f1_difference_percent']:.1f}%)")

print(f"\n Generalization Assessment: {generalization_status.upper()}")

if f1_transfer >= f1_baseline * 0.85:
    print("\n STRONG CONCLUSION:")
    print("   The model demonstrates excellent generalization to external data.")
    print("   Strong adaptation despite different data distributions.")
    print("   This validates the robustness of the approach.")
elif f1_transfer >= f1_baseline * 0.70:
    print("\n  MODERATE CONCLUSION:")
    print("   The model shows reasonable generalization with expected performance drop.")
else:
    print("\n WEAK CONCLUSION:")
    print("   Significant performance gap detected.")
    print("   Model may be overfitted to training domain.")

print("\n Important Notes:")
print("  • IBM dataset lacks CV-specific features (skill_match, title_similarity)")
print("  • These were approximated with reasonable defaults")
print("  • Some performance drop is expected and acceptable")
print("  • This validation tests model robustness to feature approximation")
print("  • Real deployment should use actual feature values when available")

print("\n" + "="*60)
print(" IBM VALIDATION COMPLETED")
print("="*60)