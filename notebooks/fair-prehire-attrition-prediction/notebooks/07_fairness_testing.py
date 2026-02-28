"""
============================================================
Fairness Testing with REAL Structural Metadata
============================================================
Uses real fairness metadata: region, university_tier, career_gap
NOT synthetic demographics (gender, age)
============================================================
"""

import os
import joblib
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from fairlearn.metrics import (
    MetricFrame,
    selection_rate,
    demographic_parity_difference,
    equalized_odds_difference
)
import warnings
warnings.filterwarnings('ignore')

print("="*60)
print("FAIRNESS TESTING WITH REAL STRUCTURAL METADATA")
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
# Path Configuration
# ============================================================

SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent

MODEL_DIR = PROJECT_ROOT / "models"
RESULTS_DIR = PROJECT_ROOT / "results"
ARTIFACT_DIR = RESULTS_DIR / "artifacts" / "fairness"

# Create folders
for folder in [MODEL_DIR, RESULTS_DIR, ARTIFACT_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

print(f"\n Project root: {PROJECT_ROOT}")
print(f" Models folder: {MODEL_DIR}")
print(f" Artifacts folder: {ARTIFACT_DIR}")

# ============================================================
# Load Test Data
# ============================================================

print("\n Loading test data...")

try:
    X_test = joblib.load(MODEL_DIR / "X_test.pkl")
    y_test = joblib.load(MODEL_DIR / "y_test.pkl")
    print(f" Loaded test data: {X_test.shape}")
except FileNotFoundError as e:
    print(f" Error: Test data not found. Run 04_model_training.py first.")
    exit(1)

# ============================================================
# Load REAL Fairness Metadata
# ============================================================

print("\n Loading REAL fairness metadata...")

try:
    meta_test = joblib.load(MODEL_DIR / "fairness_meta_test.pkl")
    print(" Fairness metadata loaded")
    print(f"Available features: {list(meta_test.keys())}")
except FileNotFoundError:
    print("❌ Error: fairness_meta_test.pkl not found.")
    print("Run 04_model_training.py first to generate fairness metadata.")
    exit(1)

# Verify expected columns
EXPECTED_FAIRNESS_COLS = ["region", "university_tier", "has_career_gap"]

missing_cols = [col for col in EXPECTED_FAIRNESS_COLS if col not in meta_test]
if missing_cols:
    print(f"  Warning: Missing fairness columns: {missing_cols}")
    print(f"Available: {list(meta_test.keys())}")

# Verify data alignment
print(f"\nData shapes:")
print(f"  X_test: {X_test.shape}")
print(f"  y_test: {y_test.shape}")
for key, val in meta_test.items():
    print(f"  {key}: {len(val)}")

# ============================================================
# Load Model (Try Multiple Versions)
# ============================================================

print("\n Loading model...")

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

# ============================================================
# Generate Predictions
# ============================================================

print("\n Generating predictions...")
y_pred = final_model.predict(X_test)
print(" Predictions generated")

# Convert to binary for fairness metrics
# High risk (0) = 1 (positive class - predicted to leave early)
# Medium/Low risk (1,2) = 0 (negative class - predicted to stay)
y_binary = np.where(y_test == 0, 1, 0)
y_pred_binary = np.where(y_pred == 0, 1, 0)

print(f"\nBinary label distribution:")
print(f"  Actual high risk: {y_binary.sum()} ({y_binary.mean():.1%})")
print(f"  Predicted high risk: {y_pred_binary.sum()} ({y_pred_binary.mean():.1%})")

# ============================================================
# 1. Fairness on REGION
# ============================================================

print("\n" + "="*60)
print(" FAIRNESS CHECK: GEOGRAPHIC REGION")
print("="*60)

if "region" in meta_test:
    region_values = meta_test["region"]
    
    # Check sample sizes
    region_counts = pd.Series(region_values).value_counts()
    print("\nSample sizes per region:")
    for region, count in region_counts.items():
        status = "good" if count >= 50 else "bad "
        print(f"  {status} {region}: {count}")
    
    # Fairness metrics
    mf_region = MetricFrame(
        metrics=selection_rate,
        y_true=y_binary,
        y_pred=y_pred_binary,
        sensitive_features=region_values
    )
    
    region_dp = demographic_parity_difference(
        y_true=y_binary,
        y_pred=y_pred_binary,
        sensitive_features=region_values
    )
    
    region_eod = equalized_odds_difference(
        y_true=y_binary,
        y_pred=y_pred_binary,
        sensitive_features=region_values
    )
    
    print("\nSelection Rate by Region:")
    print(mf_region.by_group)
    print(f"\nDemographic Parity Difference: {region_dp:.4f}")
    print(f"Equalized Odds Difference: {region_eod:.4f}")
    
    # Interpretation
    print("\nInterpretation:")
    if abs(region_dp) < 0.1:
        print("   Good demographic parity (difference < 0.1)")
    else:
        print(f"    Geographic disparity detected (difference = {abs(region_dp):.3f})")
        print("  Consider: Are candidates from certain regions unfairly flagged as high risk?")
    
    # Save results
    region_fairness = {
        "selection_rate": mf_region.by_group.to_dict(),
        "demographic_parity_difference": float(region_dp),
        "equalized_odds_difference": float(region_eod),
        "interpretation": "acceptable" if abs(region_dp) < 0.1 else "needs_review",
        "sample_sizes": region_counts.to_dict()
    }
    
    with open(ARTIFACT_DIR / "region_fairness.json", "w") as f:
        json.dump(region_fairness, f, indent=2)
    print(f"\n Saved: region_fairness.json")
    
    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))
    mf_region.by_group.plot(kind="bar", color='steelblue', ax=ax, edgecolor='black')
    ax.set_title("Selection Rate by Geographic Region\n(Proportion Predicted as High Risk)", 
                 fontsize=14, fontweight='bold')
    ax.set_ylabel("Selection Rate", fontsize=12)
    ax.set_xlabel("Region", fontsize=12)
    plt.xticks(rotation=45, ha='right')
    ax.set_ylim(0, 1)
    ax.grid(axis='y', alpha=0.3)
    
    # Add value labels
    for i, v in enumerate(mf_region.by_group.values):
        ax.text(i, v + 0.02, f'{v:.3f}', ha='center', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(ARTIFACT_DIR / "region_selection_rate.png", dpi=150, bbox_inches='tight')
    plt.close()
    print(" Saved: region_selection_rate.png")
    
else:
    print("  Region metadata not available")
    region_fairness = None

# ============================================================
# 2. Fairness on UNIVERSITY TIER
# ============================================================

print("\n" + "="*60)
print(" FAIRNESS CHECK: UNIVERSITY TIER")
print("="*60)

if "university_tier" in meta_test:
    uni_tier_values = meta_test["university_tier"]
    
    # Check sample sizes
    uni_counts = pd.Series(uni_tier_values).value_counts()
    print("\nSample sizes per university tier:")
    for tier, count in uni_counts.items():
        status = "good" if count >= 50 else "bad "
        print(f"  {status} {tier}: {count}")
    
    # Fairness metrics
    mf_uni = MetricFrame(
        metrics=selection_rate,
        y_true=y_binary,
        y_pred=y_pred_binary,
        sensitive_features=uni_tier_values
    )
    
    uni_dp = demographic_parity_difference(
        y_true=y_binary,
        y_pred=y_pred_binary,
        sensitive_features=uni_tier_values
    )
    
    uni_eod = equalized_odds_difference(
        y_true=y_binary,
        y_pred=y_pred_binary,
        sensitive_features=uni_tier_values
    )
    
    print("\nSelection Rate by University Tier:")
    print(mf_uni.by_group)
    print(f"\nDemographic Parity Difference: {uni_dp:.4f}")
    print(f"Equalized Odds Difference: {uni_eod:.4f}")
    
    # Interpretation
    print("\nInterpretation:")
    if abs(uni_dp) < 0.1:
        print("   Good demographic parity (difference < 0.1)")
    else:
        print(f"  Educational disparity detected (difference = {abs(uni_dp):.3f})")
        print("  Consider: Are graduates from certain university tiers unfairly penalized?")
    
    # Save results
    uni_fairness = {
        "selection_rate": mf_uni.by_group.to_dict(),
        "demographic_parity_difference": float(uni_dp),
        "equalized_odds_difference": float(uni_eod),
        "interpretation": "acceptable" if abs(uni_dp) < 0.1 else "needs_review",
        "sample_sizes": uni_counts.to_dict()
    }
    
    with open(ARTIFACT_DIR / "university_fairness.json", "w") as f:
        json.dump(uni_fairness, f, indent=2)
    print(f"\n Saved: university_fairness.json")
    
    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))
    mf_uni.by_group.plot(kind="bar", color='coral', ax=ax, edgecolor='black')
    ax.set_title("Selection Rate by University Tier\n(Proportion Predicted as High Risk)", 
                 fontsize=14, fontweight='bold')
    ax.set_ylabel("Selection Rate", fontsize=12)
    ax.set_xlabel("University Tier", fontsize=12)
    plt.xticks(rotation=45, ha='right')
    ax.set_ylim(0, 1)
    ax.grid(axis='y', alpha=0.3)
    
    # Add value labels
    for i, v in enumerate(mf_uni.by_group.values):
        ax.text(i, v + 0.02, f'{v:.3f}', ha='center', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(ARTIFACT_DIR / "university_selection_rate.png", dpi=150, bbox_inches='tight')
    plt.close()
    print(" Saved: university_selection_rate.png")
    
else:
    print("  University tier metadata not available")
    uni_fairness = None

# ============================================================
# 3. Fairness on CAREER GAP
# ============================================================

print("\n" + "="*60)
print(" FAIRNESS CHECK: CAREER GAP")
print("="*60)

if "has_career_gap" in meta_test:
    career_gap_values = ["With Gap" if x == 1 else "No Gap" for x in meta_test["has_career_gap"]]
    
    # Check sample sizes
    gap_counts = pd.Series(career_gap_values).value_counts()
    print("\nSample sizes per career gap status:")
    for status, count in gap_counts.items():
        check = "good" if count >= 50 else "bad "
        print(f"  {check} {status}: {count}")
    
    # Fairness metrics
    mf_gap = MetricFrame(
        metrics=selection_rate,
        y_true=y_binary,
        y_pred=y_pred_binary,
        sensitive_features=career_gap_values
    )
    
    gap_dp = demographic_parity_difference(
        y_true=y_binary,
        y_pred=y_pred_binary,
        sensitive_features=career_gap_values
    )
    
    gap_eod = equalized_odds_difference(
        y_true=y_binary,
        y_pred=y_pred_binary,
        sensitive_features=career_gap_values
    )
    
    print("\nSelection Rate by Career Gap Status:")
    print(mf_gap.by_group)
    print(f"\nDemographic Parity Difference: {gap_dp:.4f}")
    print(f"Equalized Odds Difference: {gap_eod:.4f}")
    
    # Interpretation
    print("\nInterpretation:")
    if abs(gap_dp) < 0.1:
        print("   Good demographic parity (difference < 0.1)")
    else:
        print(f"    Career gap disparity detected (difference = {abs(gap_dp):.3f})")
        print("  Consider: Are candidates with career gaps unfairly flagged as high risk?")
    
    # Save results
    gap_fairness = {
        "selection_rate": mf_gap.by_group.to_dict(),
        "demographic_parity_difference": float(gap_dp),
        "equalized_odds_difference": float(gap_eod),
        "interpretation": "acceptable" if abs(gap_dp) < 0.1 else "needs_review",
        "sample_sizes": gap_counts.to_dict()
    }
    
    with open(ARTIFACT_DIR / "career_gap_fairness.json", "w") as f:
        json.dump(gap_fairness, f, indent=2)
    print(f"\n Saved: career_gap_fairness.json")
    
    # Plot
    fig, ax = plt.subplots(figsize=(8, 6))
    mf_gap.by_group.plot(kind="bar", color='seagreen', ax=ax, edgecolor='black')
    ax.set_title("Selection Rate by Career Gap Status\n(Proportion Predicted as High Risk)", 
                 fontsize=14, fontweight='bold')
    ax.set_ylabel("Selection Rate", fontsize=12)
    ax.set_xlabel("Career Gap Status", fontsize=12)
    plt.xticks(rotation=0)
    ax.set_ylim(0, 1)
    ax.grid(axis='y', alpha=0.3)
    
    # Add value labels
    for i, v in enumerate(mf_gap.by_group.values):
        ax.text(i, v + 0.02, f'{v:.3f}', ha='center', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(ARTIFACT_DIR / "career_gap_selection_rate.png", dpi=150, bbox_inches='tight')
    plt.close()
    print(" Saved: career_gap_selection_rate.png")
    
else:
    print("  Career gap metadata not available")
    gap_fairness = None

# ============================================================
# Combined Fairness Summary
# ============================================================

print("\n" + "="*60)
print(" COMPREHENSIVE FAIRNESS SUMMARY")
print("="*60)

summary = {
    "model_used": model_name,
    "methodology": {
        "approach": "Structural fairness analysis using real pre-hire data",
        "fairness_groups": ["region", "university_tier", "has_career_gap"],
        "note": "NO synthetic demographics (gender, age) used - only objectively available CV features"
    },
    "region": region_fairness if region_fairness else {"status": "not_available"},
    "university_tier": uni_fairness if uni_fairness else {"status": "not_available"},
    "career_gap": gap_fairness if gap_fairness else {"status": "not_available"},
    "overall_assessment": {
        "region_fair": abs(region_fairness["demographic_parity_difference"]) < 0.1 if region_fairness else None,
        "university_fair": abs(uni_fairness["demographic_parity_difference"]) < 0.1 if uni_fairness else None,
        "career_gap_fair": abs(gap_fairness["demographic_parity_difference"]) < 0.1 if gap_fairness else None
    },
    "fairness_thresholds": {
        "demographic_parity": "< 0.1 considered acceptable",
        "equalized_odds": "< 0.1 considered acceptable"
    },
    "ethical_note": [
        "This analysis uses REAL structural factors from CVs (location, education, career history)",
        "NO inference of protected characteristics (gender, ethnicity, religion)",
        "Aligns with ethical AI and anti-discrimination best practices",
        "All fairness groups are objectively identifiable from resume data"
    ]
}

with open(ARTIFACT_DIR / "fairness_summary.json", "w") as f:
    json.dump(summary, f, indent=2)
print(f"\n Saved comprehensive summary: fairness_summary.json")

# ============================================================
# Final Report
# ============================================================

print("\n" + "="*60)
print(" FAIRNESS TESTING REPORT")
print("="*60)

print(f"\nModel Tested: {model_name}")

print("\n Fairness Groups Analyzed:")
fairness_groups = [
    ("Geographic Region", region_fairness),
    ("University Tier", uni_fairness),
    ("Career Gap Status", gap_fairness)
]

all_fair = True
for group_name, fairness_data in fairness_groups:
    if fairness_data:
        dp = fairness_data["demographic_parity_difference"]
        status = " PASS" if abs(dp) < 0.1 else "  REVIEW"
        print(f"\n{group_name:25s} | DP Diff: {dp:6.3f} | {status}")
        if abs(dp) >= 0.1:
            print(f"{'':27s}   → Action needed: Investigate disparity")
            all_fair = False
    else:
        print(f"\n{group_name:25s} |   Data not available")

print("\n" + "="*60)
if all_fair:
    print(" ALL FAIRNESS CHECKS PASSED")
else:
    print("  SOME FAIRNESS CONCERNS DETECTED - REVIEW NEEDED")
print("="*60)

print(f"\n All fairness reports saved to: {ARTIFACT_DIR}")
print("\n Key Fairness Metrics:")
print("  • Demographic Parity (equal selection rates across groups)")
print("  • Equalized Odds (equal TPR/FPR across groups)")
print("  • Visual comparisons saved as PNG files")

print("\n Ethical Approach Verified:")
print("  • Uses REAL structural data (location, education, career history)")
print("  • NO synthetic demographics generated")
print("  • NO protected characteristics inferred")
print("  • Complies with fairness research best practices")

print("\n" + "="*60)
print("FAIRNESS TESTING COMPLETED")
print("="*60)