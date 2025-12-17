import re
import numpy as np
from typing import Dict, Any
from datetime import datetime
from difflib import SequenceMatcher

async def create_feature_vector_from_mongo(cv_document: Dict, jd_text: str, jd_location: str = None) -> Dict[str, float]:
    """
    Create feature vector from MongoDB CV document and JD text
    
    """
    
    # Extract from MongoDB sections
    sections = cv_document.get("sections", {})
    raw_text = cv_document.get("raw_text", "")
    
    # Experience extraction from parsed sections
    experience_text = sections.get("experience", "")
    education_text = sections.get("education", "")
    skills_text = sections.get("skills", "")
    
    # Count jobs (split by common patterns)
    job_markers = len(re.findall(r'•|\n-|\n\d+\.', experience_text))
    n_jobs = max(job_markers, 1)
    
    # Extract years of experience (look for date patterns)
    year_ranges = re.findall(r'(\d{4})\s*(?:to|-|--)\s*(\d{4}|present|current)', 
                              experience_text, re.IGNORECASE)
    total_exp_years = 0
    current_year = datetime.now().year
    
    for start, end in year_ranges:
        start_year = int(start)
        if 'present' in end.lower() or 'current' in end.lower():
            end_year = current_year 
        else:
            end_year = int(end)
        total_exp_years += max(0, end_year - start_year)
    
    total_exp_years = min(total_exp_years, 30)  # Cap at 30 years
    
    # Skills extraction
    skill_list = [s.strip() for s in skills_text.split(',') if s.strip()]
    n_skills = len(skill_list)
    
    # Education parsing
    n_edu = len(re.findall(r'Bachelor|Master|PhD|Diploma|Associate', 
                           education_text, re.IGNORECASE))
    has_masters = 'master' in education_text.lower()
    
    # Calculate derived features
    avg_tenure_months = (total_exp_years * 12) / max(n_jobs, 1)
    short_stints_count = count_short_stints(experience_text, threshold_months=12)
    job_hopping_rate = short_stints_count / max(n_jobs, 1) if n_jobs > 0 else 0.0
    
    # Matching scores
    skill_match = compute_skill_match_with_esco(skills_text, jd_text) 
    title_match = compute_title_similarity(raw_text, jd_text)
    exp_match = compute_experience_match(total_exp_years, jd_text)
    edu_match = compute_education_match(education_text, jd_text)
    
    # GEOCODING-BASED LOCATION MATCH
    cv_location = extract_location_from_cv(raw_text, sections)
    jd_location_extracted = extract_location_from_jd(jd_text) if not jd_location else jd_location
    
    loc_match = await compute_location_match_with_geocoding(cv_location, jd_location_extracted)
    overall_match = (skill_match + title_match + exp_match + edu_match + loc_match) / 5
    
    # Qualification flags
    exp_matches = re.findall(r'(\d+)\+?\s*(?:to|-)\s*(\d+)?\s*years?', 
                             jd_text.lower())
    if exp_matches:
        jd_min = int(exp_matches[0][0])
        jd_max = int(exp_matches[0][1]) if exp_matches[0][1] else jd_min + 2
    else:
        jd_min, jd_max = 2, 5
    
    is_overqualified = 1 if total_exp_years > jd_max + 2 else 0
    is_underqualified = 1 if total_exp_years < jd_min - 0.5 else 0
    
    # Complete feature dictionary matching training data (26 features)
    features = {
        # Matching scores
        'skill_match_score': skill_match,
        'title_match_score': title_match,
        'exp_match_score': exp_match,
        'edu_match_score': float(edu_match),
        'location_match_score': loc_match,
        'overall_match_score': overall_match,
        
        # Qualification flags
        'is_overqualified': is_overqualified,
        'is_underqualified': is_underqualified,
        
        # CV features (attrition predictors)
        'total_jobs': float(n_jobs),
        'total_exp_years': float(total_exp_years),
        'avg_tenure_months': float(avg_tenure_months),
        'current_job_tenure': float(avg_tenure_months),  # Approx
        'short_stints_count': float(short_stints_count),
        'job_hopping_rate': float(job_hopping_rate),
        'has_progression': 1.0 if n_jobs >= 2 else 0.0,
        'has_masters': 1.0 if has_masters else 0.0,
        'n_skills': float(n_skills),
        'n_certifications': 0.0,  # Not extracted yet
        
        # Work mode compatibility
        'is_remote_cv': 0.0,  # Default
        'is_remote_jd': 1.0 if 'remote' in jd_text.lower() else 0.0,
        'work_mode_mismatch': 0.0,  # Default
        
        # Fairness metadata (defaults)
        'region': 'colombo_metro',
        'university_tier': 'other_state_university',
        'has_career_gap': 0.0,
        'career_gap_months': 0.0,
        'is_remote_preference': 0.0
    }
    
    return features

def compute_skill_match_with_esco(cv_skills: str, jd_text: str) -> float:
    """
    Compute skill overlap between CV and JD using ESCO semantic matching
    Falls back to traditional matching if ESCO unavailable or no matches
    """
    try:
        from app.services.esco_mapper import get_esco_mapper
        
        esco = get_esco_mapper()
        
        if esco is None:
            print("  ESCO unavailable, using traditional skill matching")
            return compute_skill_match_original(cv_skills, jd_text)
        
        # Extract skills from CV
        cv_skills_list = [s.strip() for s in cv_skills.split(',') if s.strip()]
        
        # Extract skills from JD
        jd_skills_list = extract_skills_from_jd(jd_text)
        
        # Use ESCO semantic matching
        esco_score = esco.calculate_esco_skill_match(
            cv_skills_list,
            jd_skills_list,
            threshold=70 
        )
        
        # If ESCO returns 0 (no matches), fall back to traditional
        if esco_score == 0:
            print("  ESCO found no matches, using traditional matching")
            return compute_skill_match_original(cv_skills, jd_text)
        
        print(f"  ESCO Skill Match: {esco_score:.3f} (CV: {len(cv_skills_list)} skills, JD: {len(jd_skills_list)} skills)")
        return esco_score
        
    except Exception as e:
        print(f"  ESCO matching failed: {e}, using fallback")
        return compute_skill_match_original(cv_skills, jd_text)


def extract_skills_from_jd(jd_text: str) -> list:
    """
    Extract skills from job description text
    """
    jd_lower = jd_text.lower()
    
    # Common tech skills
    common_skills = [
        # Programming Languages
        'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust',
        'php', 'ruby', 'swift', 'kotlin', 'scala', 'r', 'matlab',
        
        # Web Frameworks
        'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring boot',
        'express', 'fastapi', 'asp.net', 'laravel', 'rails',
        
        # Databases
        'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
        'cassandra', 'oracle', 'sql server', 'dynamodb', 'firebase',
        
        # Cloud & DevOps
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'gitlab ci', 
        'github actions', 'terraform', 'ansible', 'ci/cd', 'devops',

        # Data Science & ML
        'machine learning', 'deep learning', 'data analysis', 'data science',
        'nlp', 'computer vision', 'tensorflow', 'pytorch', 'scikit-learn',
        'pandas', 'numpy', 'spark', 'hadoop', 'tableau', 'power bi',
        
        # Mobile
        'android', 'ios', 'react native', 'flutter', 'xamarin',
        
        # Other
        'agile', 'scrum', 'project management', 'leadership',
        'git', 'linux', 'rest api', 'graphql', 'microservices',
        'sre', 'monitoring', 'logging', 'security', 'testing',
        'etl', 'data warehouse', 'api design', 'system design'
    ]
    
    detected_skills = []
    for skill in common_skills:
        if skill in jd_lower:
            detected_skills.append(skill)
    
    return detected_skills


def compute_skill_match_original(cv_skills: str, jd_text: str) -> float:
    """
    Original skill matching method (fallback if ESCO fails)
    Uses simple keyword matching
    """
    common_skills = [
        'python', 'java', 'sql', 'javascript', 'react', 'node',
        'machine learning', 'data analysis', 'project management',
        'agile', 'docker', 'kubernetes', 'aws', 'azure', 'gcp'
    ]
    
    cv_lower = cv_skills.lower()
    jd_lower = jd_text.lower()
    
    cv_skills_set = {skill for skill in common_skills if skill in cv_lower}
    jd_skills_set = {skill for skill in common_skills if skill in jd_lower}
    
    if not jd_skills_set:
        return 0.5
    
    intersection = len(cv_skills_set & jd_skills_set)
    union = len(cv_skills_set | jd_skills_set)
    
    return intersection / union if union > 0 else 0.3


def compute_title_similarity(cv_text: str, jd_text: str) -> float:
    """Compute similarity between CV job title and JD title"""
    cv_lines = cv_text.strip().split('\n')
    cv_title = cv_lines[0] if cv_lines else ""
    jd_title = jd_text[:200].strip()
    
    if not cv_title or not jd_title:
        return 0.5
    
    return SequenceMatcher(None, cv_title.lower(), jd_title.lower()).ratio()

def count_short_stints(experience_text: str, threshold_months: int = 12) -> int:
    """Count jobs lasting less than threshold months"""
    year_ranges = re.findall(r'(\d{4})\s*(?:to|-|--)\s*(\d{4}|present|current)', 
                              experience_text, re.IGNORECASE)
    
    short_count = 0
    current_year = datetime.now().year
    
    for start, end in year_ranges:
        start_year = int(start)
        if 'present' in end.lower() or 'current' in end.lower():
            end_year = current_year
        else:
            end_year = int(end)
        
        tenure_months = (end_year - start_year) * 12
        if tenure_months < threshold_months:
            short_count += 1
    
    return short_count

def calculate_job_hopping_rate(short_stints, total_jobs):
    if total_jobs <= 1:
        return 0.0
    return short_stints / total_jobs

def compute_experience_match(cv_exp: float, jd_text: str) -> float:
    """Compute experience match score"""
    exp_pattern = r'(\d+)\+?\s*(?:to|-)\s*(\d+)?\s*years?'
    matches = re.findall(exp_pattern, jd_text.lower())
    
    if matches:
        jd_min = int(matches[0][0])
        jd_max = int(matches[0][1]) if matches[0][1] else jd_min + 2
    else:
        jd_min, jd_max = 2, 5
    
    # Calculate match
    if cv_exp < jd_min:
        return max(0, cv_exp / jd_min)
    elif cv_exp > jd_max:
        return max(0, 1 - (cv_exp - jd_max) / 10)
    else:
        return 1.0


def compute_education_match(cv_edu_text: str, jd_text: str) -> int:
    """0 = under-qualified, 1 = qualified/over-qualified"""
    jd_lower = jd_text.lower()
    
    has_masters = 'master' in cv_edu_text.lower()
    has_bachelors = 'bachelor' in cv_edu_text.lower()
    
    # Check if JD requires Master's
    if 'master' in jd_lower and not has_masters:
        return 0  # Under-qualified
    
    # Check if JD requires Bachelor's
    if 'bachelor' in jd_lower and not has_bachelors:
        return 0
    
    return 1  # Qualified


def extract_location_from_cv(raw_text: str, sections: Dict) -> str:
    """Extract candidate location from CV"""
    # Try to find location in raw text
    lines = raw_text.split('\n')[:15]  # Check first 15 lines
    
    # Expanded Sri Lankan cities list (include suburbs and towns)
    sl_cities = [
        # Major cities
        'Colombo', 'Kandy', 'Galle', 'Jaffna', 'Negombo',
        'Anuradhapura', 'Trincomalee', 'Batticaloa', 'Matara',
        
        # Colombo suburbs
        'Moratuwa', 'Maharagama', 'Nugegoda', 'Dehiwala', 'Mount Lavinia',
        'Piliyandala', 'Bokundara', 'Boralesgamuwa', 'Homagama', 'Kaduwela',
        'Battaramulla', 'Rajagiriya', 'Nawala', 'Malabe', 'Kotte',
        'Kelaniya', 'Wattala', 'Ja-Ela', 'Gampaha', 'Kadawatha',
        'Kalutara', 'Panadura', 'Horana',
        
        # Other cities
        'Kurunegala', 'Ratnapura', 'Badulla', 'Nuwara Eliya',
        'Hambantota', 'Kilinochchi', 'Vavuniya', 'Ampara'
    ]
    
    # Try to find any city mentioned in first 15 lines
    found_locations = []
    for line_num, line in enumerate(lines):
        line_clean = line.strip()
        if not line_clean:
            continue
            
        for city in sl_cities:
            if city.lower() in line_clean.lower():
                found_locations.append((city, line_num, line_clean))
                
    
    # Return the FIRST location found
    if found_locations:
        # Prefer locations found in lines 1-5 (most likely to be candidate location)
        early_locations = [loc for loc in found_locations if loc[1] <= 5]
        if early_locations:
            city = early_locations[0][0]
            print(f"   Extracted CV location: {city}")
            return f"{city}, Sri Lanka"
        else:
            city = found_locations[0][0]
            print(f"   Extracted CV location: {city}")
            return f"{city}, Sri Lanka"
    
    # Default to Colombo if not found
    print(f"  Location not found in CV, defaulting to Colombo")
    print(f"  First 5 lines were:")
    for i, line in enumerate(lines[:5]):
        print(f"    {i}: {line[:80]}")
    return "Colombo, Sri Lanka"


def extract_location_from_jd(jd_text: str) -> str:
    """Extract job location from job description"""
    # Look for location patterns
    location_patterns = [
        r'Location:\s*([^\n]+)',
        r'Based in:\s*([^\n]+)',
        r'Office:\s*([^\n]+)',
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, jd_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # Default
    return "Colombo, Sri Lanka"


async def compute_location_match_with_geocoding(cv_location: str, jd_location: str) -> float:
    """
    Compute location match score using geocoding API
    Returns score between 0.0 and 1.0
    """

    try:
        from app.services.geocoding_service import get_geocoding_service
        
        geocoding = get_geocoding_service()
        distance_km, risk = await geocoding.calculate_commute_distance(
            cv_location, 
            jd_location
        )
        
        # Convert to match score
        return geocoding.get_location_match_score(distance_km, risk)
        
    except Exception as e:
        print(f"  Geocoding failed, using default: {e}")
        return 0.7  # Default moderate match if geocoding fails