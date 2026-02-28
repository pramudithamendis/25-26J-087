"""
============================================================
Label Generation with BALANCED Labels
============================================================
Generates attrition risk labels using weak supervision
Produces balanced label distribution using percentile-based thresholds
============================================================
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')

print("="*60)
print("LABEL GENERATION WITH WEAK SUPERVISION (BALANCED)")
print("="*60)

# ============================================================
# Path Configuration
# ============================================================

SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
INPUT_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "processed"

FEATURES_FILE = INPUT_DIR / "cv_jd_pairs_features.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"\n Input folder: {INPUT_DIR}")
print(f" Output folder: {OUTPUT_DIR}")

# ============================================================
# Load Data
# ============================================================

print("\n Loading features...")

try:
    df = pd.read_csv(FEATURES_FILE)
    print(f" Loaded {len(df)} CV-JD pairs")
    print(f"Features: {len(df.columns)}")
except FileNotFoundError:
    print(f" Error: {FEATURES_FILE} not found. Run 02_feature_engineering.py first.")
    exit(1)

# ============================================================
# BALANCED Weak Supervision Rules
# ============================================================

def rule_job_hopping(row):
    """Job switching rate"""
    rate = row.get("job_hopping_rate", 0)
    if rate >= 0.6:  # Very high hopping
        return 0
    elif rate >= 0.4:
        return 1
    return 2

def rule_tenure_pattern(row):
    """Average tenure"""
    avg_tenure = row.get("avg_tenure_months", 0)
    if avg_tenure < 8:  # Less than 8 months average
        return 0
    elif avg_tenure < 18:  # Less than 1.5 years
        return 1
    return 2

def rule_current_job_tenure(row):
    """Current job tenure"""
    current_tenure = row.get("current_job_tenure", 0)
    if current_tenure < 6:
        return 0
    elif current_tenure < 15:
        return 1
    return 2

def rule_skill_match(row):
    """Skill-job match"""
    score = row.get("skill_match_score", 0)
    if score < 0.25:  # Very poor match
        return 0
    elif score < 0.5:  # Moderate match
        return 1
    return 2

def rule_title_match(row):
    """Title similarity"""
    score = row.get("title_match_score", 0)
    if score < 0.3:
        return 0
    elif score < 0.55:
        return 1
    return 2

def rule_experience_match(row):
    """Experience alignment"""
    if row.get("is_overqualified", 0) == 1:
        return 1  # Overqualified = medium risk (not high)
    elif row.get("is_underqualified", 0) == 1:
        return 1  # Underqualified = medium risk
    
    exp_match = row.get("exp_match_score", 0)
    if exp_match < 0.4:
        return 0
    elif exp_match < 0.7:
        return 1
    return 2

def rule_overall_match(row):
    """Overall job fit"""
    score = row.get("overall_match_score", 0)
    if score < 0.4:
        return 0
    elif score < 0.6:
        return 1
    return 2

def rule_career_gap(row):
    """Career gap impact (reduced weight)"""
    if row.get("has_career_gap", 0) == 1:
        gap_months = row.get("career_gap_months", 0)
        if gap_months > 9:  # Only very long gaps are high risk
            return 0
        return 1  # Moderate gaps = medium risk
    return 2

def rule_work_mode(row):
    """Work mode mismatch (minor factor)"""
    if row.get("work_mode_mismatch", 0) == 1:
        return 1  # Only medium risk, not high
    return 2

# ============================================================
# Calculate Risk Scores for All Rows
# ============================================================

def calculate_weighted_risk(row):
    """Calculate weighted average risk score for a row"""
    risk_scores = [
        (rule_job_hopping(row), 1.5),        # Higher weight (key indicator)
        (rule_tenure_pattern(row), 1.5),     # Higher weight
        (rule_skill_match(row), 1.2),        # Important
        (rule_title_match(row), 1.2),        # Important
        (rule_experience_match(row), 1.0),
        (rule_overall_match(row), 1.3),      # Important
        (rule_current_job_tenure(row), 1.0),
        (rule_career_gap(row), 0.7),         # Lower weight (less critical)
        (rule_work_mode(row), 0.5)           # Lowest weight
    ]
    
    # Calculate weighted average
    weighted_sum = sum(score * weight for score, weight in risk_scores)
    total_weight = sum(weight for _, weight in risk_scores)
    avg_risk = weighted_sum / total_weight
    
    return avg_risk

print("\n Calculating risk scores for all samples...")

# Calculate risk scores for all rows
temp_risks = []
for idx, row in df.iterrows():
    risk_score = calculate_weighted_risk(row)
    temp_risks.append(risk_score)

# Convert to numpy array for easier manipulation
temp_risks = np.array(temp_risks)

print(f" Calculated {len(temp_risks)} risk scores")

# ============================================================
# Calculate Optimal Thresholds Using Percentiles
# ============================================================

print("\n Calculating optimal thresholds using percentiles...")

# Use 33rd and 67th percentiles for balanced 3-class split
threshold_low = np.percentile(temp_risks, 33)
threshold_high = np.percentile(temp_risks, 67)

print(f" Auto-calculated thresholds:")
print(f"   Low threshold (33rd percentile): {threshold_low:.4f}")
print(f"   High threshold (67th percentile): {threshold_high:.4f}")

# Show distribution of risk scores
print(f"\n Risk Score Statistics:")
print(f"   Min: {temp_risks.min():.4f}")
print(f"   25th percentile: {np.percentile(temp_risks, 25):.4f}")
print(f"   Median (50th): {np.percentile(temp_risks, 50):.4f}")
print(f"   75th percentile: {np.percentile(temp_risks, 75):.4f}")
print(f"   Max: {temp_risks.max():.4f}")
print(f"   Mean: {temp_risks.mean():.4f}")
print(f"   Std Dev: {temp_risks.std():.4f}")

# ============================================================
# Apply Labels Using Calculated Thresholds
# ============================================================

def generate_attrition_label_balanced(row):
    """
    Generate label using WEIGHTED AVERAGE with PERCENTILE-BASED thresholds
    
    Produces balanced labels:
    - 0 = High Risk (leaves within 6 months)
    - 1 = Medium Risk (leaves 6-12 months)
    - 2 = Low Risk (stays >1 year)
    """
    
    avg_risk = calculate_weighted_risk(row)
    
    # Map continuous risk to 3 classes using calculated thresholds
    if avg_risk <= threshold_low:
        return 0  # High Risk
    elif avg_risk <= threshold_high:
        return 1  # Medium Risk
    else:
        return 2  # Low Risk

# ============================================================
# Generate Labels
# ============================================================

print("\n  Generating balanced attrition risk labels...")

df["attrition_risk"] = df.apply(generate_attrition_label_balanced, axis=1)

# Map to human-readable labels
risk_labels = {
    0: "High Risk (0-6 months)",
    1: "Medium Risk (6-12 months)",
    2: "Low Risk (>1 year)"
}

df["attrition_risk_label"] = df["attrition_risk"].map(risk_labels)

print("\n Labels generated!")
print(f"\n Label Distribution:")
print(df["attrition_risk"].value_counts().sort_index())
print(f"\nPercentages:")
for label, count in df["attrition_risk"].value_counts().sort_index().items():
    pct = count / len(df) * 100
    print(f"  {risk_labels[label]}: {count} ({pct:.1f}%)")

# ============================================================
# Check Balance
# ============================================================

label_counts = df["attrition_risk"].value_counts()
min_class = label_counts.min()
max_class = label_counts.max()
imbalance_ratio = max_class / min_class

print(f"\n Balance Check:")
print(f"  Min class size: {min_class}")
print(f"  Max class size: {max_class}")
print(f"  Imbalance ratio: {imbalance_ratio:.2f}:1")

if imbalance_ratio > 5:
    print("    WARNING: Severe class imbalance (>5:1)")
    print("     Consider adjusting rules or using class weights in training")
elif imbalance_ratio > 3:
    print("    Moderate class imbalance (3-5:1)")
    print("     Use class_weight='balanced' in model training")
else:
    print("   Good class balance (<3:1)")

# ============================================================
# Fairness Metadata Check
# ============================================================

print("\n" + "="*60)
print("FAIRNESS METADATA VERIFICATION")
print("="*60)

fairness_cols = ["region", "university_tier", "has_career_gap"]

print(f"\n Using REAL fairness metadata from CV generator:")
print(f"\nRegion Distribution:")
print(df["region"].value_counts())

print(f"\nUniversity Tier Distribution:")
print(df["university_tier"].value_counts())

print(f"\nCareer Gap Distribution:")
print(df["has_career_gap"].value_counts())

# Check subgroup sample sizes
print(f"\n🔍 Checking Fairness Subgroup Sample Sizes:")
print(f"(Minimum recommended: 100 per subgroup)")

subgroups = {
    "Region": df.groupby("region")["attrition_risk"].count(),
    "University Tier": df.groupby("university_tier")["attrition_risk"].count(),
    "Career Gap": df.groupby("has_career_gap")["attrition_risk"].count()
}

all_sufficient = True
for subgroup_name, counts in subgroups.items():
    print(f"\n{subgroup_name}:")
    for group, count in counts.items():
        status = "-okay" if count >= 100 else "-error "
        print(f"  {status} {group}: {count}")
        if count < 100:
            all_sufficient = False

if all_sufficient:
    print(f"\n All subgroups have sufficient samples for fairness analysis!")
else:
    print(f"\n  Some subgroups have <100 samples. Consider this limitation in analysis.")

# ============================================================
# Label Distribution by Fairness Groups
# ============================================================

print("\n" + "="*60)
print("LABEL DISTRIBUTION BY FAIRNESS GROUPS")
print("="*60)

print("\n Labels by Region:")
region_dist = pd.crosstab(df["region"], df["attrition_risk"], normalize='index') * 100
print(region_dist.round(1))

print("\n Labels by University Tier:")
uni_dist = pd.crosstab(df["university_tier"], df["attrition_risk"], normalize='index') * 100
print(uni_dist.round(1))

print("\n Labels by Career Gap:")
gap_dist = pd.crosstab(df["has_career_gap"], df["attrition_risk"], normalize='index') * 100
print(gap_dist.round(1))

# ============================================================
# Save Labeled Data
# ============================================================

print("\n Saving labeled data...")

output_labeled = OUTPUT_DIR / "features_labeled.csv"
df.to_csv(output_labeled, index=False)
print(f" Saved: {output_labeled}")

# Save fairness metadata separately
fairness_metadata = df[["cv_id", "jd_id"] + fairness_cols + ["attrition_risk"]].copy()
output_fairness = OUTPUT_DIR / "fairness_metadata.csv"
fairness_metadata.to_csv(output_fairness, index=False)
print(f" Saved: {output_fairness}")

# ============================================================
# Summary Statistics
# ============================================================

print("\n" + "="*60)
print("LABEL GENERATION SUMMARY")
print("="*60)
print(f"Total samples: {len(df)}")
print(f"Features: {len(df.columns)}")
print(f"Target column: attrition_risk")

print(f"\n Label Distribution:")
for label in [0, 1, 2]:
    count = (df["attrition_risk"] == label).sum()
    pct = count / len(df) * 100
    print(f"  {risk_labels[label]}: {count} ({pct:.1f}%)")

print(f"\n Fairness Metadata:")
print(f"   Region: {df['region'].nunique()} categories")
print(f"   University Tier: {df['university_tier'].nunique()} categories")
print(f"   Career Gaps: {df['has_career_gap'].sum()} with gaps")

print(f"\n📋 Feature Columns ({len(df.columns)} total):")
for i, col in enumerate(df.columns, 1):
    print(f"  {i}. {col}")

print("="*60)
print("\n Label Generation Completed")
print("="*60)