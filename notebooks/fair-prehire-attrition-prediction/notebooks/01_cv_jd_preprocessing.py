"""
============================================================
CV and JD Preprocessing with Fairness Metadata
============================================================
Compatible with enhanced CV and JD generators
Extracts features + fairness metadata from synthetic data
============================================================
"""

import os
import re
import json
import glob
from pathlib import Path
from datetime import datetime
from dateutil import parser as date_parser
import pandas as pd
from tqdm import tqdm

print("="*60)
print("CV & JD PREPROCESSING WITH FAIRNESS METADATA")
print("="*60)

# ============================================================
# Path Configuration
# ============================================================

SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

CV_FOLDER = DATA_DIR / "synthetic_cvs"
JD_FOLDER = DATA_DIR / "jd_data"
OUTPUT_DIR = DATA_DIR / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"\n CV folder: {CV_FOLDER}")
print(f" JD folder: {JD_FOLDER}")
print(f" Output folder: {OUTPUT_DIR}")

# Load CV metadata (contains fairness info)
CV_METADATA_FILE = CV_FOLDER / "cv_metadata.json"

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def calculate_tenure(start_str, end_str):
    """Calculate tenure in months between two dates"""
    try:
        start = date_parser.parse(start_str)
        if end_str.lower() == "present":
            end = datetime(2025, 11, 1)
        else:
            end = date_parser.parse(end_str)
        
        months = (end.year - start.year) * 12 + (end.month - start.month)
        return max(0, months)
    except:
        return 0


def get_region_category(region):
    """Map region to broader category for fairness analysis"""
    if region in ["colombo_metro"]:
        return "colombo_metro"
    elif region in ["western_other"]:
        return "western_other"
    elif region in ["central"]:
        return "central"
    elif region in ["southern"]:
        return "southern"
    else:
        return "other_provinces"


def get_university_category(tier):
    """Map university tier to category"""
    if tier == "top_state":
        return "top_state_university"
    elif tier == "other_state":
        return "other_state_university"
    elif tier in ["private_affiliated", "other_private"]:
        return "private_university"
    return "other"


# ============================================================
# CV PARSING
# ============================================================

def parse_synthetic_cv(filepath):
    """Parse a synthetic CV with known structure"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    lines = text.strip().split('\n')
    
    cv_data = {
        "file": os.path.basename(filepath),
        "cv_id": os.path.basename(filepath).replace(".txt", ""),
        "current_title": None,
        "location": None,
        "summary": None,
        "experience": [],
        "education": [],
        "skills": [],
        "certifications": []
    }
    
    current_section = None
    current_job = {}
    current_edu = {}
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # First non-empty line is title
        if cv_data["current_title"] is None and line:
            cv_data["current_title"] = line
            i += 1
            continue
        
        # Second non-empty line is location
        if cv_data["location"] is None and line and cv_data["current_title"]:
            cv_data["location"] = line
            i += 1
            continue
        
        # Third content line is summary
        if cv_data["summary"] is None and line and "Work Experience" not in line:
            if cv_data["location"] and not line.startswith("Work"):
                cv_data["summary"] = line
                i += 1
                continue
        
        # Section headers
        if line == "Work Experience":
            current_section = "experience"
            i += 1
            continue
        elif line == "Education":
            if current_job and current_job.get("title"):
                cv_data["experience"].append(current_job)
                current_job = {}
            current_section = "education"
            i += 1
            continue
        elif line == "Skills":
            if current_edu and current_edu.get("degree"):
                cv_data["education"].append(current_edu)
                current_edu = {}
            current_section = "skills"
            i += 1
            continue
        elif line == "Certifications":
            current_section = "certifications"
            i += 1
            continue
        
        # Parse sections
        if current_section == "experience" and line:
            if not line.startswith("•") and " to " not in line and " - " not in line:
                if current_job and current_job.get("title"):
                    cv_data["experience"].append(current_job)
                current_job = {
                    "title": line, "company": "", "location": "", 
                    "start_date": "", "end_date": "", "tenure_months": 0,
                    "responsibilities": []
                }
            elif " - " in line and not line.startswith("•"):
                parts = line.split(" - ")
                if len(parts) >= 2:
                    current_job["company"] = parts[0].strip()
                    current_job["location"] = parts[1].strip()
            elif " to " in line and not line.startswith("•"):
                dates = line.split(" to ")
                if len(dates) >= 2:
                    current_job["start_date"] = dates[0].strip()
                    current_job["end_date"] = dates[1].strip()
                    current_job["tenure_months"] = calculate_tenure(
                        current_job["start_date"], 
                        current_job["end_date"]
                    )
            elif line.startswith("•"):
                current_job["responsibilities"].append(line[1:].strip())
        
        elif current_section == "education" and line:
            if line.startswith("Bachelor") or line.startswith("Master") or \
               line.startswith("Associate") or line.startswith("PhD"):
                if current_edu and current_edu.get("degree"):
                    cv_data["education"].append(current_edu)
                current_edu = {"degree": "", "field": "", "university": "", "year": ""}
                if " in " in line:
                    parts = line.split(" in ", 1)
                    current_edu["degree"] = parts[0].strip()
                    current_edu["field"] = parts[1].strip() if len(parts) > 1 else ""
                else:
                    current_edu["degree"] = line
            elif current_edu and not current_edu.get("university") and line:
                current_edu["university"] = line
            elif current_edu and line.startswith("Graduated"):
                year_match = re.search(r'\d{4}', line)
                if year_match:
                    current_edu["year"] = year_match.group()
        
        elif current_section == "skills" and line:
            skills = [s.strip() for s in line.split(",")]
            cv_data["skills"].extend(skills)
        
        elif current_section == "certifications" and line:
            if line.startswith("•"):
                cv_data["certifications"].append(line[1:].strip())
        
        i += 1
    
    # Save last items
    if current_job and current_job.get("title"):
        cv_data["experience"].append(current_job)
    if current_edu and current_edu.get("degree"):
        cv_data["education"].append(current_edu)
    
    return cv_data


def extract_cv_features(cv_data, metadata_row=None):
    """Extract ML features from parsed CV + fairness metadata"""
    
    experiences = cv_data.get("experience", [])
    education = cv_data.get("education", [])
    skills = cv_data.get("skills", [])
    certs = cv_data.get("certifications", [])
    
    # Basic counts
    total_jobs = len(experiences)
    tenures = [e.get("tenure_months", 0) for e in experiences]
    
    # Tenure statistics
    avg_tenure = sum(tenures) / max(len(tenures), 1)
    min_tenure = min(tenures) if tenures else 0
    max_tenure = max(tenures) if tenures else 0
    current_tenure = tenures[0] if tenures else 0
    
    # Job hopping indicators
    short_stints = sum(1 for t in tenures if t < 12)
    very_short_stints = sum(1 for t in tenures if t < 6)
    
    # Total experience
    total_exp_months = sum(tenures)
    total_exp_years = total_exp_months / 12
    
    # Career progression
    titles = [e.get("title", "").lower() for e in experiences]
    has_progression = any("senior" in t or "lead" in t for t in titles[:2])
    
    # Education level
    degrees = [e.get("degree", "").lower() for e in education]
    has_masters = any("master" in d for d in degrees)
    has_bachelors = any("bachelor" in d for d in degrees)
    highest_edu = "masters" if has_masters else ("bachelors" if has_bachelors else "other")
    
    # Skills & certs
    n_skills = len(skills)
    n_certs = len(certs)
    
    # Location
    location = cv_data.get("location", "Unknown")
    is_remote = "remote" in location.lower() or "hybrid" in location.lower()
    
    # Base features
    features = {
        "cv_id": cv_data.get("cv_id", ""),
        "file": cv_data.get("file", ""),
        "current_title": cv_data.get("current_title", ""),
        "location": location,
        "is_remote": 1 if is_remote else 0,
        
        # Experience features
        "total_jobs": total_jobs,
        "total_exp_months": total_exp_months,
        "total_exp_years": round(total_exp_years, 1),
        "avg_tenure_months": round(avg_tenure, 1),
        "min_tenure_months": min_tenure,
        "max_tenure_months": max_tenure,
        "current_job_tenure": current_tenure,
        
        # Job hopping indicators
        "short_stints_count": short_stints,
        "very_short_stints_count": very_short_stints,
        "job_hopping_rate": round(short_stints / max(total_jobs, 1), 2),
        
        # Career indicators
        "has_progression": 1 if has_progression else 0,
        
        # Education
        "highest_education": highest_edu,
        "has_masters": 1 if has_masters else 0,
        
        # Skills & Certs
        "n_skills": n_skills,
        "n_certifications": n_certs,
        
        # Raw data
        "skills_list": ",".join(skills),
        "current_company": experiences[0].get("company", "") if experiences else ""
    }
    
    # Add fairness metadata if available
    if metadata_row is not None:
        features["region"] = get_region_category(metadata_row.get("region", "other_provinces"))
        features["university_tier"] = get_university_category(metadata_row.get("university_tier", "other"))
        features["has_career_gap"] = int(metadata_row.get("has_career_gap", False))
        features["career_gap_months"] = metadata_row.get("career_gap_months", 0)
        features["is_remote_preference"] = int(metadata_row.get("is_remote_preference", False))
    else:
        # Defaults if metadata missing
        features["region"] = "unknown"
        features["university_tier"] = "unknown"
        features["has_career_gap"] = 0
        features["career_gap_months"] = 0
        features["is_remote_preference"] = 0
    
    return features


# ============================================================
# JD PARSING
# ============================================================

def parse_synthetic_jd(filepath):
    """Parse a synthetic JD with structured format"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    jd_data = {
        "file": os.path.basename(filepath),
        "jd_id": os.path.basename(filepath).replace(".txt", ""),
        "title": "",
        "level": "",
        "company": "",
        "location": "",
        "work_mode": "",
        "required_skills": [],
        "required_experience": "",
        "required_education": ""
    }
    
    lines = text.strip().split('\n')
    current_section = None
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Title and level from header
        if i < 10 and "=" not in line and " - " in line and not jd_data["title"]:
            # Format: "SOFTWARE ENGINEER - JUNIOR"
            parts = line.split(" - ")
            if len(parts) >= 2:
                jd_data["title"] = parts[0].strip().title()
                jd_data["level"] = parts[1].strip().title()
        
        # Company
        if line.startswith("Company:"):
            jd_data["company"] = line.replace("Company:", "").strip()
        
        # Location
        if line.startswith("Location:"):
            jd_data["location"] = line.replace("Location:", "").strip().split(",")[0]
        
        # Work Mode
        if line.startswith("Work Mode:"):
            jd_data["work_mode"] = line.replace("Work Mode:", "").strip()
        
        # Section detection
        if "REQUIRED QUALIFICATIONS" in line:
            current_section = "requirements"
        elif "Technical Skills" in line:
            current_section = "skills"
        elif "WHAT WE OFFER" in line or "NICE TO HAVE" in line:
            current_section = None
        
        # Extract skills
        if current_section in ["requirements", "skills"]:
            if line.startswith("•") or line.startswith("-"):
                skill = line[1:].strip()
                # Filter out non-skill lines
                skip_words = ["years", "experience", "degree", "bachelor", "master", 
                             "education", "self-motivated", "excellent", "strong",
                             "ability", "good", "proficiency", "understanding"]
                if not any(w in skill.lower() for w in skip_words):
                    if len(skill) < 50:
                        jd_data["required_skills"].append(skill)
        
        # Experience requirement
        if "experience" in line.lower() and ("year" in line.lower() or "years" in line.lower()):
            exp_match = re.search(r'(\d+[-–]\d+|\d+\+?)\s*years?', line.lower())
            if exp_match:
                jd_data["required_experience"] = exp_match.group(1)
        
        # Education requirement
        if "bachelor" in line.lower() or "master" in line.lower():
            if "master" in line.lower() and not jd_data["required_education"]:
                jd_data["required_education"] = "masters"
            elif "bachelor" in line.lower() and not jd_data["required_education"]:
                jd_data["required_education"] = "bachelors"
    
    return jd_data


def extract_jd_features(jd_data):
    """Extract features from parsed JD"""
    
    # Parse experience requirement
    exp_req = jd_data.get("required_experience", "0")
    if "-" in exp_req or "–" in exp_req:
        parts = re.split(r'[-–]', exp_req)
        min_exp = int(parts[0]) if parts[0].isdigit() else 0
        max_exp = int(parts[1].replace("+", "")) if parts[1].replace("+", "").isdigit() else min_exp + 2
    elif "+" in exp_req:
        min_exp = int(exp_req.replace("+", ""))
        max_exp = min_exp + 5
    elif exp_req.isdigit():
        min_exp = int(exp_req)
        max_exp = min_exp + 2
    else:
        min_exp, max_exp = 0, 0
    
    location = jd_data.get("location", "")
    work_mode = jd_data.get("work_mode", "")
    is_remote = "remote" in location.lower() or work_mode.lower() == "remote" or "hybrid" in work_mode.lower()
    
    return {
        "jd_id": jd_data.get("jd_id", ""),
        "file": jd_data.get("file", ""),
        "title": jd_data.get("title", ""),
        "level": jd_data.get("level", ""),
        "company": jd_data.get("company", ""),
        "location": location,
        "work_mode": work_mode,
        "is_remote": 1 if is_remote else 0,
        "min_exp_years": min_exp,
        "max_exp_years": max_exp,
        "required_education": jd_data.get("required_education", ""),
        "n_required_skills": len(jd_data.get("required_skills", [])),
        "required_skills_list": ",".join(jd_data.get("required_skills", []))
    }


# ============================================================
# MAIN PROCESSING
# ============================================================

def main():
    # Load CV metadata (fairness info)
    print("\n Loading CV metadata (fairness info)...")
    cv_metadata = {}
    if CV_METADATA_FILE.exists():
        with open(CV_METADATA_FILE, 'r') as f:
            metadata_list = json.load(f)
            # Create lookup dict by cv_id
            for item in metadata_list:
                cv_id = item.get("cv_id", "")
                cv_metadata[cv_id] = item
        print(f" Loaded metadata for {len(cv_metadata)} CVs")
    else:
        print(f"  Warning: {CV_METADATA_FILE} not found. Fairness metadata will be missing.")
    
    # Process CVs
    print("\n📄 Processing CVs...")
    cv_files = sorted(glob.glob(str(CV_FOLDER / "*.txt")))
    print(f"Found {len(cv_files)} CV files")
    
    cv_features_list = []
    for filepath in tqdm(cv_files, desc="Parsing CVs"):
        try:
            cv_data = parse_synthetic_cv(filepath)
            cv_id = cv_data.get("cv_id", "")
            
            # Get metadata for this CV
            metadata_row = cv_metadata.get(cv_id)
            
            features = extract_cv_features(cv_data, metadata_row)
            cv_features_list.append(features)
        except Exception as e:
            print(f"\n Error processing {filepath}: {e}")
    
    cv_df = pd.DataFrame(cv_features_list)
    cv_path = OUTPUT_DIR / "cv_features.csv"
    cv_df.to_csv(cv_path, index=False)
    print(f" Saved {len(cv_df)} CVs to: {cv_path}")
    
    # Process JDs
    print("\n Processing JDs...")
    jd_files = sorted(glob.glob(str(JD_FOLDER / "*.txt")))
    print(f"Found {len(jd_files)} JD files")
    
    jd_features_list = []
    for filepath in tqdm(jd_files, desc="Parsing JDs"):
        try:
            jd_data = parse_synthetic_jd(filepath)
            features = extract_jd_features(jd_data)
            jd_features_list.append(features)
        except Exception as e:
            print(f"\n Error processing {filepath}: {e}")
    
    jd_df = pd.DataFrame(jd_features_list)
    jd_path = OUTPUT_DIR / "jd_features.csv"
    jd_df.to_csv(jd_path, index=False)
    print(f" Saved {len(jd_df)} JDs to: {jd_path}")
    
    # Summary
    print("\n" + "="*60)
    print("PREPROCESSING SUMMARY")
    print("="*60)
    print(f"CVs processed: {len(cv_df)}")
    print(f"JDs processed: {len(jd_df)}")
    
    print(f"\n CV Statistics:")
    print(f"  Avg experience: {cv_df['total_exp_years'].mean():.1f} years")
    print(f"  Avg tenure: {cv_df['avg_tenure_months'].mean():.1f} months")
    print(f"  Avg jobs: {cv_df['total_jobs'].mean():.1f}")
    
    print(f"\n Fairness Metadata Coverage:")
    print(f"  Region distribution:")
    print(cv_df['region'].value_counts())
    print(f"\n  University tier distribution:")
    print(cv_df['university_tier'].value_counts())
    print(f"\n  Career gaps: {cv_df['has_career_gap'].sum()} / {len(cv_df)}")
    
    print("="*60)


if __name__ == "__main__":
    main()
