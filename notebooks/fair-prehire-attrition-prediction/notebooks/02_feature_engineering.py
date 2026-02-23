"""
============================================================
Feature Engineering for Attrition Prediction
============================================================
Creates CV-JD pairs with smart sampling (not full cartesian product)
Computes matching scores and attrition risk features
============================================================
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from tqdm import tqdm
from rapidfuzz import fuzz
import random

print("="*60)
print("FEATURE ENGINEERING FOR ATTRITION PREDICTION")
print("="*60)

# Set seed for reproducibility
random.seed(42)
np.random.seed(42)

# ============================================================
# Path Configuration
# ============================================================

SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
INPUT_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "processed"

CV_FILE = INPUT_DIR / "cv_features.csv"
JD_FILE = INPUT_DIR / "jd_features.csv"

print(f"\n Input folder: {INPUT_DIR}")
print(f" Output folder: {OUTPUT_DIR}")

# ============================================================
# Load Data
# ============================================================

print("\n Loading processed CV and JD features...")

try:
    cv_df = pd.read_csv(CV_FILE)
    print(f"✅ Loaded {len(cv_df)} CVs")
except FileNotFoundError:
    print(f" Error: {CV_FILE} not found. Run 01_cv_jd_preprocessing.py first.")
    exit(1)

try:
    jd_df = pd.read_csv(JD_FILE)
    print(f" Loaded {len(jd_df)} JDs")
except FileNotFoundError:
    print(f" Error: {JD_FILE} not found. Run 01_cv_jd_preprocessing.py first.")
    exit(1)

# ============================================================
# Matching Functions
# ============================================================

def calculate_skill_match(cv_skills_str, jd_skills_str):
    """Calculate skill match score between CV and JD"""
    if pd.isna(cv_skills_str) or pd.isna(jd_skills_str):
        return 0.0
    
    cv_skills = set(s.strip().lower() for s in str(cv_skills_str).split(",") if s.strip())
    jd_skills = set(s.strip().lower() for s in str(jd_skills_str).split(",") if s.strip())
    
    if not jd_skills or not cv_skills:
        return 0.0
    
    # Direct matches
    direct_matches = len(cv_skills & jd_skills)
    
    # Fuzzy matches for remaining
    fuzzy_matches = 0
    for jd_skill in jd_skills - cv_skills:
        for cv_skill in cv_skills:
            if fuzz.ratio(jd_skill, cv_skill) > 80:
                fuzzy_matches += 0.5
                break
    
    total_matches = direct_matches + fuzzy_matches
    match_score = total_matches / len(jd_skills)
    
    return round(min(match_score, 1.0), 3)


def calculate_title_similarity(cv_title, jd_title):
    """Calculate similarity between job titles"""
    if pd.isna(cv_title) or pd.isna(jd_title):
        return 0.0
    
    cv_title = str(cv_title).lower()
    jd_title = str(jd_title).lower()
    
    # Direct match
    if cv_title == jd_title:
        return 1.0
    
    # Fuzzy match
    return fuzz.ratio(cv_title, jd_title) / 100.0


def calculate_experience_match(cv_exp, jd_min, jd_max):
    """Calculate experience match score"""
    cv_exp = float(cv_exp) if not pd.isna(cv_exp) else 0
    jd_min = float(jd_min) if not pd.isna(jd_min) else 0
    jd_max = float(jd_max) if not pd.isna(jd_max) else jd_min + 2
    
    if cv_exp < jd_min:
        # Under-qualified
        return max(0, cv_exp / max(jd_min, 1))
    elif cv_exp > jd_max:
        # Over-qualified
        return max(0, 1 - (cv_exp - jd_max) / 10)
    else:
        # Perfect fit
        return 1.0


def calculate_education_match(cv_edu, jd_edu):
    """Calculate education match (0 = under-qualified, 1 = match/over-qualified)"""
    edu_levels = {
        "other": 0,
        "bachelors": 1,
        "masters": 2
    }
    
    cv_level = edu_levels.get(str(cv_edu).lower(), 0)
    jd_level = edu_levels.get(str(jd_edu).lower(), 0)
    
    if cv_level < jd_level:
        return 0  # Under-qualified
    else:
        return 1  # Qualified or over-qualified


def calculate_location_match(cv_loc, jd_loc, cv_remote, jd_remote):
    """Calculate location compatibility"""
    # If either is remote, location doesn't matter much
    if cv_remote == 1 or jd_remote == 1:
        return 1.0
    
    if pd.isna(cv_loc) or pd.isna(jd_loc):
        return 0.5
    
    cv_loc = str(cv_loc).lower()
    jd_loc = str(jd_loc).lower()
    
    # Direct match
    if cv_loc == jd_loc:
        return 1.0
    
    # Partial match (same region)
    if cv_loc in jd_loc or jd_loc in cv_loc:
        return 0.8
    
    return 0.3  # Different locations


# ============================================================
# Smart Pairing Strategy
# ============================================================

def create_smart_pairs(cv_df, jd_df, pairs_per_cv=3):
    """
    Create smart CV-JD pairs instead of full cartesian product
    
    Strategy:
    - For each CV, match with 3 JDs:
      1. One similar job (high match potential)
      2. One moderate match
      3. One dissimilar (low match, higher attrition risk)
    
    This creates 2000 CVs × 3 JDs = 6000 pairs
    """
    
    print(f"\n🔗 Creating smart CV-JD pairs ({pairs_per_cv} per CV)...")
    pairs = []
    
    for _, cv in tqdm(cv_df.iterrows(), total=len(cv_df), desc="Matching CVs"):
        cv_skills = str(cv.get("skills_list", ""))
        cv_title = str(cv.get("current_title", ""))
        
        # Calculate match scores with all JDs
        jd_scores = []
        for _, jd in jd_df.iterrows():
            jd_skills = str(jd.get("required_skills_list", ""))
            jd_title = str(jd.get("title", ""))
            
            skill_match = calculate_skill_match(cv_skills, jd_skills)
            title_match = calculate_title_similarity(cv_title, jd_title)
            overall_score = (skill_match + title_match) / 2
            
            jd_scores.append((jd, overall_score))
        
        # Sort by match score
        jd_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Select diverse matches
        selected_jds = []
        
        # 1. High match (top 10%)
        high_match_pool = jd_scores[:max(1, len(jd_scores)//10)]
        selected_jds.append(random.choice(high_match_pool)[0])
        
        # 2. Medium match (middle 40%)
        mid_start = len(jd_scores)//3
        mid_end = 2*len(jd_scores)//3
        mid_match_pool = jd_scores[mid_start:mid_end]
        if mid_match_pool:
            selected_jds.append(random.choice(mid_match_pool)[0])
        
        # 3. Low match (bottom 20%)
        low_match_pool = jd_scores[-max(1, len(jd_scores)//5):]
        selected_jds.append(random.choice(low_match_pool)[0])
        
        # Create pair features
        for jd in selected_jds:
            pair = create_pair_features(cv, jd)
            pairs.append(pair)
    
    return pd.DataFrame(pairs)


def create_pair_features(cv, jd):
    """Create feature vector for a CV-JD pair"""
    
    # Matching scores
    skill_match = calculate_skill_match(
        cv.get("skills_list", ""),
        jd.get("required_skills_list", "")
    )
    
    title_match = calculate_title_similarity(
        cv.get("current_title", ""),
        jd.get("title", "")
    )
    
    exp_match = calculate_experience_match(
        cv.get("total_exp_years", 0),
        jd.get("min_exp_years", 0),
        jd.get("max_exp_years", 10)
    )
    
    edu_match = calculate_education_match(
        cv.get("highest_education", ""),
        jd.get("required_education", "")
    )
    
    loc_match = calculate_location_match(
        cv.get("location", ""),
        jd.get("location", ""),
        cv.get("is_remote", 0),
        jd.get("is_remote", 0)
    )
    
    # Calculate over/under qualification
    cv_exp = float(cv.get("total_exp_years", 0))
    jd_min = float(jd.get("min_exp_years", 0))
    jd_max = float(jd.get("max_exp_years", 10))
    
    is_overqualified = 1 if cv_exp > jd_max + 2 else 0
    is_underqualified = 1 if cv_exp < jd_min - 0.5 else 0
    
    return {
        # Identifiers
        "cv_id": cv.get("cv_id", ""),
        "jd_id": jd.get("jd_id", ""),
        
        # Matching scores
        "skill_match_score": skill_match,
        "title_match_score": round(title_match, 3),
        "exp_match_score": round(exp_match, 3),
        "edu_match_score": edu_match,
        "location_match_score": round(loc_match, 3),
        "overall_match_score": round((skill_match + title_match + exp_match + edu_match + loc_match) / 5, 3),
        
        # Qualification flags
        "is_overqualified": is_overqualified,
        "is_underqualified": is_underqualified,
        
        # CV features (attrition predictors)
        "total_jobs": cv.get("total_jobs", 0),
        "total_exp_years": cv.get("total_exp_years", 0),
        "avg_tenure_months": cv.get("avg_tenure_months", 0),
        "current_job_tenure": cv.get("current_job_tenure", 0),
        "short_stints_count": cv.get("short_stints_count", 0),
        "job_hopping_rate": cv.get("job_hopping_rate", 0),
        "has_progression": cv.get("has_progression", 0),
        "has_masters": cv.get("has_masters", 0),
        "n_skills": cv.get("n_skills", 0),
        "n_certifications": cv.get("n_certifications", 0),
        
        # Work mode compatibility
        "is_remote_cv": cv.get("is_remote", 0),
        "is_remote_jd": jd.get("is_remote", 0),
        "work_mode_mismatch": 1 if cv.get("is_remote", 0) != jd.get("is_remote", 0) else 0,
        
        # Fairness metadata (from CV)
        "region": cv.get("region", "unknown"),
        "university_tier": cv.get("university_tier", "unknown"),
        "has_career_gap": cv.get("has_career_gap", 0),
        "career_gap_months": cv.get("career_gap_months", 0),
        "is_remote_preference": cv.get("is_remote_preference", 0)
    }


# ============================================================
# Main Processing
# ============================================================

def main():
    # Create smart pairs (3 per CV = 6000 pairs instead of 2M)
    pairs_df = create_smart_pairs(cv_df, jd_df, pairs_per_cv=3)
    
    # Save
    output_path = OUTPUT_DIR / "cv_jd_pairs_features.csv"
    pairs_df.to_csv(output_path, index=False)
    print(f"\n Saved {len(pairs_df)} pairs to: {output_path}")
    
    # Summary
    print("\n" + "="*60)
    print("FEATURE ENGINEERING SUMMARY")
    print("="*60)
    print(f"Total pairs created: {len(pairs_df)}")
    print(f"Features per pair: {len(pairs_df.columns)}")
    
    print(f"\n Matching Score Statistics:")
    print(f"  Skill match: {pairs_df['skill_match_score'].mean():.3f} (avg)")
    print(f"  Title match: {pairs_df['title_match_score'].mean():.3f} (avg)")
    print(f"  Experience match: {pairs_df['exp_match_score'].mean():.3f} (avg)")
    print(f"  Overall match: {pairs_df['overall_match_score'].mean():.3f} (avg)")
    
    print(f"\n Fairness Metadata in Pairs:")
    print(f"  Region distribution:")
    print(pairs_df['region'].value_counts())
    print(f"\n  University tier distribution:")
    print(pairs_df['university_tier'].value_counts())
    print(f"\n  Career gaps: {pairs_df['has_career_gap'].sum()} / {len(pairs_df)}")
    
    print(f"\n Feature columns:")
    for col in pairs_df.columns:
        print(f"  • {col}")
    
    print("="*60)
    print("\n Feature Engineering Completed")


if __name__ == "__main__":
    main()