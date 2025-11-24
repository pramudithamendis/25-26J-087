"""
============================================================
Ensemble Evaluation & Visualization
============================================================
Generates visualizations and deployment artifacts
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, roc_auc_score, classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

print("="*60)
print("ENSEMBLE EVALUATION & VISUALIZATION")
print("="*60)

# ============================================================
# Path Configuration
# ============================================================

SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
MODEL_DIR = PROJECT_ROOT / "models"
RESULTS_DIR = PROJECT_ROOT / "results"
VIZ_DIR = RESULTS_DIR / "visualizations"

VIZ_DIR.mkdir(parents=True, exist_ok=True)

print(f"\n Models: {MODEL_DIR}")
print(f" Results: {RESULTS_DIR}")
print(f" Visualizations: {VIZ_DIR}")

# ============================================================
# Load Test Data & Models
# ============================================================

print("\n Loading test data and models...")

X_test = joblib.load(MODEL_DIR / "X_test.pkl")
y_test = joblib.load(MODEL_DIR / "y_test.pkl")

# Prefer the calibrated ensemble
print("\n Looking for ensemble model...")

ensemble_files = [
    ("ensemble_soft_weighted_calibrated.joblib", "Calibrated Ensemble"),
    ("ensemble_soft_weighted.joblib", "Weighted Ensemble"),
    ("final_ensemble.pkl", "Custom Ensemble")
]

final_ensemble = None
ensemble_name = None

for filename, name in ensemble_files:
    filepath = MODEL_DIR / filename
    if filepath.exists():
        try:
            # For custom ensemble, need the class definition
            if filename == "final_ensemble.pkl":
                # Define FinalEnsemble class before loading
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
                        
                        weighted_proba = np.sum(probas, axis=0)
                        # Normalize to ensure probabilities sum to 1.0
                        row_sums = weighted_proba.sum(axis=1, keepdims=True)
                        normalized_proba = weighted_proba / row_sums
                        return normalized_proba
                    
                    def predict(self, X):
                        proba = self.predict_proba(X)
                        return np.argmax(proba, axis=1)
            
            final_ensemble = joblib.load(filepath)
            ensemble_name = name
            print(f" Loaded: {name} ({filename})")
            break
        except Exception as e:
            print(f"  Failed to load {filename}: {e}")
            continue

if final_ensemble is None:
    print(" No ensemble model found!")
    print("\nAvailable models in models folder:")
    for file in MODEL_DIR.glob("*.pkl"):
        print(f"  • {file.name}")
    for file in MODEL_DIR.glob("*.joblib"):
        print(f"  • {file.name}")
    exit(1)

print(f" Loaded test data: {X_test.shape}")

# ============================================================
# Generate Predictions
# ============================================================

print("\n Generating predictions...")

y_pred = final_ensemble.predict(X_test)
y_proba = final_ensemble.predict_proba(X_test)

# Verify and normalize probabilities
proba_sums = y_proba.sum(axis=1)
if not np.allclose(proba_sums, 1.0, rtol=1e-5):
    print("  Probabilities not perfectly normalized, normalizing...")
    y_proba = y_proba / proba_sums.reshape(-1, 1)
    print(" Probabilities normalized")

f1_macro = f1_score(y_test, y_pred, average="macro")

# Calculate AUC with error handling
try:
    auc_macro = roc_auc_score(y_test, y_proba, multi_class="ovr", average="macro")
except Exception as e:
    print(f"  Could not calculate ROC-AUC: {e}")
    auc_macro = None

print(f"\n {ensemble_name} Performance:")
print(f"  F1-Macro: {f1_macro:.4f}")
if auc_macro is not None:
    print(f"  ROC-AUC: {auc_macro:.4f}")
else:
    print(f"  ROC-AUC: N/A")

# ============================================================
# Classification Report
# ============================================================

print("\n Classification Report:")
print(classification_report(
    y_test, y_pred, 
    target_names=["High Risk (0-6mo)", "Medium Risk (6-12mo)", "Low Risk (>12mo)"],
    digits=4
))

# ============================================================
# Visualization 1: Confusion Matrix
# ============================================================

print("\n Generating confusion matrix...")

cm = confusion_matrix(y_test, y_pred)

fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", 
            xticklabels=["High", "Medium", "Low"],
            yticklabels=["High", "Medium", "Low"],
            cbar_kws={'label': 'Count'},
            annot_kws={'size': 14, 'weight': 'bold'})
plt.title(f"Confusion Matrix - {ensemble_name}\n(Test Set, N={len(y_test)})", 
          fontsize=14, fontweight='bold')
plt.xlabel("Predicted Attrition Risk", fontsize=12)
plt.ylabel("Actual Attrition Risk", fontsize=12)

# Add accuracy annotation
accuracy = np.trace(cm) / np.sum(cm)
plt.text(1.5, -0.3, f"Accuracy: {accuracy:.2%}", fontsize=11, ha='center', fontweight='bold')

plt.tight_layout()
cm_path = VIZ_DIR / "confusion_matrix_ensemble.png"
plt.savefig(cm_path, dpi=300, bbox_inches='tight')
print(f" Saved: {cm_path}")
plt.close()

# ============================================================
# Visualization 2: Model Comparison
# ============================================================

print("\n Comparing all models...")

# Load individual models and calculate F1
models_to_compare = {
    "Logistic Regression": "logreg.pkl",
    "Random Forest": "rf.pkl",
    "XGBoost": "xgb.pkl",
    "CatBoost": "cat.pkl",
    "EBM": "ebm.pkl"
}

comparison = {}
for name, filename in models_to_compare.items():
    filepath = MODEL_DIR / filename
    if filepath.exists():
        try:
            model = joblib.load(filepath)
            pred = model.predict(X_test)
            f1 = f1_score(y_test, pred, average="macro")
            comparison[name] = f1
            print(f"  {name}: {f1:.4f}")
        except Exception as e:
            print(f"  {name}: Error - {e}")
    else:
        print(f"  {name}: Not found")

# Add ensemble
comparison[ensemble_name] = f1_macro

# Sort by performance
comparison = dict(sorted(comparison.items(), key=lambda x: x[1]))

# Plot
fig, ax = plt.subplots(figsize=(12, 7))
models = list(comparison.keys())
scores = list(comparison.values())

colors = ['#3498db' if 'Ensemble' not in m and 'Calibrated' not in m else '#e74c3c' for m in models]

bars = ax.barh(models, scores, color=colors, edgecolor='black', linewidth=1.2)

# Add value labels
for i, (model, score) in enumerate(zip(models, scores)):
    ax.text(score + 0.005, i, f"{score:.4f}", va='center', fontsize=10, fontweight='bold')

# Add target line
ax.axvline(x=0.80, color='green', linestyle='--', linewidth=2, label='Target (0.80)', alpha=0.7)

ax.set_xlabel("F1-Macro Score", fontsize=12, fontweight='bold')
ax.set_title("Model Performance Comparison on Test Set", fontsize=14, fontweight='bold')
ax.set_xlim(0.70, 1.0)
ax.legend(loc='lower right')
ax.grid(axis='x', alpha=0.3)

plt.tight_layout()
comp_path = VIZ_DIR / "model_comparison.png"
plt.savefig(comp_path, dpi=300, bbox_inches='tight')
print(f" Saved: {comp_path}")
plt.close()

# ============================================================
# Visualization 3: Prediction Distribution
# ============================================================

print("\n Analyzing prediction distribution...")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Actual distribution
actual_counts = [(y_test == 0).sum(), (y_test == 1).sum(), (y_test == 2).sum()]
axes[0].bar(['High', 'Medium', 'Low'], actual_counts,
           color=['#e74c3c', '#f39c12', '#2ecc71'], edgecolor='black', linewidth=2)
axes[0].set_title("Actual Distribution (Test Set)", fontsize=12, fontweight='bold')
axes[0].set_ylabel("Count", fontsize=11)
axes[0].grid(axis='y', alpha=0.3)

# Add count labels
for i, count in enumerate(actual_counts):
    axes[0].text(i, count + 10, str(count), ha='center', fontweight='bold', fontsize=11)

# Predicted distribution
pred_counts = [(y_pred == 0).sum(), (y_pred == 1).sum(), (y_pred == 2).sum()]
axes[1].bar(['High', 'Medium', 'Low'], pred_counts,
           color=['#e74c3c', '#f39c12', '#2ecc71'], edgecolor='black', linewidth=2)
axes[1].set_title("Predicted Distribution (Test Set)", fontsize=12, fontweight='bold')
axes[1].set_ylabel("Count", fontsize=11)
axes[1].grid(axis='y', alpha=0.3)

# Add count labels
for i, count in enumerate(pred_counts):
    axes[1].text(i, count + 10, str(count), ha='center', fontweight='bold', fontsize=11)

plt.suptitle("Attrition Risk Distribution", fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
dist_path = VIZ_DIR / "prediction_distribution.png"
plt.savefig(dist_path, dpi=300, bbox_inches='tight')
print(f" Saved: {dist_path}")
plt.close()

# ============================================================
# Visualization 4: Per-Class Performance
# ============================================================

print("\n Generating per-class performance chart...")

from sklearn.metrics import precision_recall_fscore_support

precision, recall, f1_scores, support = precision_recall_fscore_support(y_test, y_pred)

metrics_df = pd.DataFrame({
    'Precision': precision,
    'Recall': recall,
    'F1-Score': f1_scores
}, index=['High Risk', 'Medium Risk', 'Low Risk'])

fig, ax = plt.subplots(figsize=(10, 6))
metrics_df.plot(kind='bar', ax=ax, color=['#3498db', '#e74c3c', '#2ecc71'], 
                edgecolor='black', linewidth=1.2)
ax.set_title("Per-Class Performance Metrics", fontsize=14, fontweight='bold')
ax.set_ylabel("Score", fontsize=12)
ax.set_xlabel("Risk Category", fontsize=12)
ax.set_ylim(0, 1.0)
ax.legend(loc='lower right', fontsize=10)
ax.grid(axis='y', alpha=0.3)
plt.xticks(rotation=45, ha='right')

# Add value labels on bars
for container in ax.containers:
    ax.bar_label(container, fmt='%.3f', padding=3, fontsize=9)

plt.tight_layout()
perf_path = VIZ_DIR / "per_class_performance.png"
plt.savefig(perf_path, dpi=300, bbox_inches='tight')
print(f" Saved: {perf_path}")
plt.close()

# ============================================================
# Save Deployment Summary
# ============================================================

print("\n Saving deployment summary...")

summary = {
    "model_name": ensemble_name,
    "test_set_size": int(len(y_test)),
    "metrics": {
        "f1_macro": float(f1_macro),
        "roc_auc_macro": float(auc_macro) if auc_macro is not None else None,
        "accuracy": float((y_test == y_pred).mean())
    },
    "per_class_performance": {},
    "base_models_f1": {k: float(v) for k, v in comparison.items()},
    "confusion_matrix": cm.tolist(),
    "label_distribution": {
        "actual": {
            "high_risk": int((y_test == 0).sum()),
            "medium_risk": int((y_test == 1).sum()),
            "low_risk": int((y_test == 2).sum())
        },
        "predicted": {
            "high_risk": int((y_pred == 0).sum()),
            "medium_risk": int((y_pred == 1).sum()),
            "low_risk": int((y_pred == 2).sum())
        }
    }
}

# Per-class metrics
for i, label in enumerate(["High Risk", "Medium Risk", "Low Risk"]):
    summary["per_class_performance"][label] = {
        "precision": float(precision[i]),
        "recall": float(recall[i]),
        "f1_score": float(f1_scores[i]),
        "support": int(support[i])
    }

summary_path = RESULTS_DIR / "deployment_summary.json"
with open(summary_path, "w") as f:
    json.dump(summary, f, indent=2)
print(f" Saved deployment summary: {summary_path}")

# ============================================================
# Example Predictions
# ============================================================

print("\n" + "="*60)
print(" EXAMPLE PREDICTIONS")
print("="*60)

np.random.seed(42)
sample_indices = np.random.choice(len(X_test), 5, replace=False)
sample_X = X_test.iloc[sample_indices]
sample_y_true = y_test.iloc[sample_indices].values
sample_proba = final_ensemble.predict_proba(sample_X)
sample_pred = final_ensemble.predict(sample_X)

risk_labels = ["High Risk", "Medium Risk", "Low Risk"]

for i in range(5):
    print(f"\n{'─'*50}")
    print(f"Candidate {i+1}:")
    print(f"  Actual:    {risk_labels[sample_y_true[i]]}")
    print(f"  Predicted: {risk_labels[sample_pred[i]]}")
    print(f"  Confidence: {sample_proba[i].max():.1%}")
    print(f"  Probabilities:")
    print(f"    • High Risk:   {sample_proba[i][0]:>6.2%}")
    print(f"    • Medium Risk: {sample_proba[i][1]:>6.2%}")
    print(f"    • Low Risk:    {sample_proba[i][2]:>6.2%}")
    
    if sample_y_true[i] == sample_pred[i]:
        print(f"   CORRECT PREDICTION")
    else:
        print(f"   INCORRECT (predicted {risk_labels[sample_pred[i]]} instead of {risk_labels[sample_y_true[i]]})")

# ============================================================
# Final Summary
# ============================================================

print("\n" + "="*60)
print("✅ ENSEMBLE EVALUATION COMPLETED")
print("="*60)
print(f"\n Final Results Summary:")
print(f"  Model: {ensemble_name}")
print(f"  Test Set Size: {len(y_test)}")
print(f"")
print(f"  Metrics:")
print(f"    F1-Macro: {f1_macro:.4f} {' EXCEEDS TARGET (≥0.80)' if f1_macro >= 0.80 else ' BELOW TARGET'}")
if auc_macro is not None:
    print(f"    ROC-AUC:  {auc_macro:.4f} {' EXCEEDS TARGET (≥0.85)' if auc_macro >= 0.85 else ' BELOW TARGET'}")
print(f"    Accuracy: {(y_test == y_pred).mean():.4f}")

print(f"\n Generated Outputs:")
print(f"  • Confusion Matrix: confusion_matrix_ensemble.png")
print(f"  • Model Comparison: model_comparison.png")
print(f"  • Distribution Plot: prediction_distribution.png")
print(f"  • Per-Class Performance: per_class_performance.png")
print(f"  • Deployment Summary: deployment_summary.json")

print(f"\n All files saved in:")
print(f"  Visualizations: {VIZ_DIR}")
print(f"  Summary: {RESULTS_DIR}")

print("="*60)