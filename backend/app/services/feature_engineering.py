import re
import numpy as np
from typing import Dict, Any, List, Tuple
from datetime import datetime
from dateutil import parser as date_parser
from difflib import SequenceMatcher

def extract_location_from_jd_enhanced(jd_text: str) -> str:
    """Enhanced JD location extraction"""
    if not jd_text:
        return "Colombo, Sri Lanka"  # Default
    
    # Look for common patterns
    location_patterns = [
        r'Location:\s*([^\n]+)',
        r'Based in:\s*([^\n]+)',
        r'Office:\s*([^\n]+)',
        r'Work Location:\s*([^\n]+)',
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, jd_text, re.IGNORECASE)
        if match:
            location = match.group(1).strip()
            # Clean up common suffixes
            location = location.split(',')[0].strip()  # Get first part
            if location and len(location) > 2:
                return f"{location}, Sri Lanka"
    
    # Fallback: search for Sri Lankan cities anywhere in text
    sl_cities = [
        'Colombo', 'Kandy', 'Galle', 'Jaffna', 'Negombo', 'Moratuwa',
        'Maharagama', 'Nugegoda', 'Dehiwala', 'Kelaniya', 'Gampaha'
    ]
    
    for city in sl_cities:
        if city.lower() in jd_text.lower():
            return f"{city}, Sri Lanka"
    
    return "Colombo, Sri Lanka"  # Ultimate default

# ============================================================
# EXPERIENCE PARSING
# ============================================================

def parse_experience_from_sections(sections: Dict[str, str]) -> List[Dict]:
    experience_text = sections.get("experience", "")
    if not experience_text:
        return []

    jobs = []
    # Stop words to prevent bleeding into Education/Projects
    stop_keywords = ['education', 'certifications', 'projects', 'languages', 'skills']
    
    lines = experience_text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Check if a new section header is found
        if any(stop in line.lower() for stop in stop_keywords) and len(line.strip()) < 25:
            break
        if line.strip():
            cleaned_lines.append(line.strip())

    # Use a flexible regex to find "Month Year" date ranges
    date_pattern = r'(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\s*(?:–|-|to|—)?\s*(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}|Present|Current)'

    for i, line in enumerate(cleaned_lines):
        date_match = re.search(date_pattern, line, re.IGNORECASE)
        if date_match:
            # Capture the line above or the current line for the job title
            header_text = line
            if i > 0 and len(cleaned_lines[i-1]) < 100:
                header_text = cleaned_lines[i-1] + " " + line

            start_date_str = date_match.group(1)
            end_date_str = date_match.group(2)
            
            # Use your existing calculate_tenure function
            tenure = calculate_tenure(start_date_str, end_date_str)
            
            jobs.append({
                'title': header_text.split('-')[0].strip(),
                'tenure_months': tenure,
                'start_date': start_date_str,
                'end_date': end_date_str
            })

    return jobs

def parse_date_range(date_text: str) -> tuple:
    """
    Parse date ranges like:
    - "May 2018 – Jan 2021"
    - "Jan 2020 to Present"
    - "2019 - 2021"
    - "Mar 2020"
    
    Returns: (start_date_str, end_date_str)
    """
    # Common separators: –, -, to, --, —
    separators = ['–', '—', ' to ', ' - ', '--']
    
    for sep in separators:
        if sep in date_text:
            parts = date_text.split(sep, 1)
            start = parts[0].strip()
            end = parts[1].strip() if len(parts) > 1 else "Present"
            return (start, end)

    # No separator found - single date (assume it's the start, end is Present)
    return (date_text.strip(), "Present")

def calculate_tenure(start_str: str, end_str: str) -> int:
    """Calculate tenure in months"""
    try:
        # Clean up the strings
        start_str = start_str.strip()
        end_str = end_str.strip()
        
        # Parse start date
        start = date_parser.parse(start_str, fuzzy=True)

        # Parse end date
        if end_str.lower() in ['present', 'current', 'now', '']:
            end = datetime.now()
        else:
            end = date_parser.parse(end_str, fuzzy=True)
        
        months = (end.year - start.year) * 12 + (end.month - start.month)
        return max(0, months)
    except Exception as e:
        print(f" Date parsing error: {start_str} to {end_str}")
        return 12


# ============================================================
# INDUSTRY SWITCH DETECTION
# ============================================================

INDUSTRY_KEYWORDS = {
    'fintech': ['bank', 'financial', 'trading', 'payment', 'fintech', 'insurance'],
    'healthcare': ['health', 'medical', 'hospital', 'pharma', 'biotech'],
    'ecommerce': ['ecommerce', 'retail', 'marketplace', 'shopping', 'e-commerce'],
    'edtech': ['education', 'learning', 'university', 'edtech', 'training'],
    'gaming': ['game', 'gaming', 'entertainment', 'esports'],
    'consulting': ['consulting', 'advisory', 'consultancy', 'services'],
    'enterprise': ['enterprise', 'saas', 'b2b', 'software'],
}


def detect_industry(company_name: str, job_title: str, responsibilities: List[str]) -> str:
    """Detect industry from job context"""
    text = f"{company_name} {job_title} {' '.join(responsibilities)}".lower()
    
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return industry
    
    return 'general_tech'


def calculate_industry_switches(jobs: List[Dict]) -> int:
    """Count industry switches"""
    if len(jobs) <= 1:
        return 0
    
    industries = [detect_industry(j.get('company', ''), j.get('title', ''), j.get('responsibilities', [])) for j in jobs]
    
    switches = 0
    for i in range(1, len(industries)):
        if industries[i] != industries[i-1]:
            switches += 1
    
    return switches


# ============================================================
# TENURE ANALYSIS
# ============================================================

def calculate_tenure_slope(jobs: List[Dict]) -> float:
    """Calculate tenure trend"""
    if len(jobs) < 2:
        return 0.0
    
    tenures = [job.get('tenure_months', 0) for job in jobs]
    tenures = tenures[::-1]
    
    n = len(tenures)
    x = np.arange(n)
    y = np.array(tenures)
    
    if n < 2:
        return 0.0
    
    x_mean = x.mean()
    y_mean = y.mean()
    
    numerator = np.sum((x - x_mean) * (y - y_mean))
    denominator = np.sum((x - x_mean) ** 2)
    
    if denominator == 0:
        return 0.0
    
    slope = numerator / denominator
    return round(float(slope), 2)


def count_short_stints(jobs: List[Dict], threshold_months: int = 12) -> int:
    """Count short tenure jobs"""
    return sum(1 for job in jobs if job.get('tenure_months', 0) < threshold_months)


def calculate_job_hopping_rate(jobs: List[Dict]) -> float:
    """Calculate job hopping rate"""
    total_jobs = len(jobs)
    if total_jobs <= 1:
        return 0.0
    
    short_stints = count_short_stints(jobs, threshold_months=12)
    return round(short_stints / total_jobs, 2)

# ============================================================
# CAREER PROGRESSION
# ============================================================

SENIORITY_LEVELS = {
    'intern': 0, 'trainee': 0, 'junior': 1, 'associate': 1,
    'mid': 2, 'senior': 3, 'lead': 4, 'principal': 4,
    'staff': 4, 'manager': 5, 'director': 6, 'head': 6,
    'vp': 7, 'cto': 8, 'ceo': 8
}


def get_seniority_level(job_title: str) -> int:
    """Extract seniority level"""
    title_lower = job_title.lower()
    
    for keyword, level in SENIORITY_LEVELS.items():
        if keyword in title_lower:
            return level
    
    return 2


def detect_career_progression(jobs: List[Dict]) -> Tuple[bool, int]:
    """Detect career progression"""
    if len(jobs) < 2:
        return False, 0
    
    levels = [get_seniority_level(job.get('title', '')) for job in jobs]
    levels = levels[::-1]
    
    progression_jumps = 0
    has_progression = False
    
    for i in range(1, len(levels)):
        if levels[i] > levels[i-1]:
            progression_jumps += 1
            has_progression = True
    
    return has_progression, progression_jumps


# ============================================================
# SKILL MATCHING
# ============================================================

def extract_skills_from_jd(jd_text: str) -> list:
    """Extract skills from JD"""
    if not jd_text:
        return []
    
    jd_lower = jd_text.lower()
    
    common_skills = [
        'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust',
        'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring boot',
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform',
        'sql', 'mysql', 'postgresql', 'mongodb', 'redis',
        'machine learning', 'deep learning', 'data science', 'nlp',
        'devops', 'ci/cd', 'jenkins', 'gitlab', 'github actions',
        'git', 'linux', 'agile', 'scrum'
    ]
    
    return [skill for skill in common_skills if skill in jd_lower]


def compute_skill_match_traditional(cv_skills: str, jd_text: str) -> float:
    """Traditional skill matching"""
    common_skills = [
        'python', 'java', 'javascript', 'sql', 'react', 'node',
        'aws', 'azure', 'docker', 'kubernetes', 'terraform',
        'machine learning', 'data analysis', 'devops', 'git', 'linux'
    ]
    
    cv_lower = cv_skills.lower() if cv_skills else ""
    jd_lower = jd_text.lower() if jd_text else ""
    
    if not cv_lower or not jd_lower:
        return 0.5
    
    cv_skills_set = {skill for skill in common_skills if skill in cv_lower}
    jd_skills_set = {skill for skill in common_skills if skill in jd_lower}
    
    if not jd_skills_set:
        return 0.5
    
    intersection = len(cv_skills_set & jd_skills_set)
    union = len(cv_skills_set | jd_skills_set)
    
    if union == 0:
        return 0.3
    
    return round(intersection / union, 3)


def compute_skill_match_with_esco(cv_skills: str, jd_text: str) -> float:
    """Compute skill match with ESCO fallback"""
    if not cv_skills or not jd_text:
        return 0.5
    
    try:
        from app.services.esco_mapper import get_esco_mapper
        
        esco = get_esco_mapper()
        
        if esco is None:
            return compute_skill_match_traditional(cv_skills, jd_text)
        
        cv_skills_list = [s.strip() for s in cv_skills.split(',') if s.strip()]
        jd_skills_list = extract_skills_from_jd(jd_text)
        
        if not cv_skills_list or not jd_skills_list:
            return 0.5
        
        esco_score = esco.calculate_esco_skill_match(cv_skills_list, jd_skills_list, threshold=70)
        
        if esco_score == 0:
            return compute_skill_match_traditional(cv_skills, jd_text)
        
        return float(esco_score)
        
    except Exception as e:
        return compute_skill_match_traditional(cv_skills, jd_text)


# ============================================================
# OTHER MATCHING FUNCTIONS
# ============================================================

def get_domain_keywords() -> Dict[str, List[str]]:
    """
    Domain-specific keyword sets for semantic matching
    Maps job domains to their key technical skills/responsibilities
    """
    return {
        'devops': ['CI/CD', 'Docker', 'Kubernetes', 'Jenkins', 'Terraform', 'AWS', 'Azure', 'GCP', 'Ansible', 'GitLab', 'pipeline', 'infrastructure as code'],
        'data_engineering': ['ETL', 'ELT', 'data pipeline', 'Airflow', 'Spark', 'data warehouse', 'Snowflake', 'Redshift', 'BigQuery', 'dbt'],
        'data_science': ['machine learning', 'ML', 'deep learning', 'neural network', 'TensorFlow', 'PyTorch', 'scikit-learn', 'NLP', 'computer vision', 'predictive model'],
        'backend': ['API', 'REST', 'GraphQL', 'microservices', 'Node.js', 'Django', 'Flask', 'Spring Boot', 'database', 'SQL', 'NoSQL'],
        'frontend': ['React', 'Angular', 'Vue', 'JavaScript', 'TypeScript', 'CSS', 'HTML', 'responsive design', 'UI/UX'],
        'mobile': ['iOS', 'Android', 'React Native', 'Flutter', 'Swift', 'Kotlin', 'mobile app'],
        'security': ['cybersecurity', 'penetration testing', 'vulnerability', 'security audit', 'encryption', 'firewall', 'SIEM'],
        'qa': ['testing', 'QA', 'automation', 'Selenium', 'test case', 'bug tracking', 'quality assurance']
    }


def detect_job_domain(jd_text: str) -> str:
    """
    Detect job domain from job description
    Returns the domain with the highest keyword match count
    """
    jd_lower = jd_text.lower()
    domain_keywords = get_domain_keywords()
    
    domain_scores = {}
    for domain, keywords in domain_keywords.items():
        score = sum(1 for keyword in keywords if keyword.lower() in jd_lower)
        domain_scores[domain] = score
    
    # Get domain with highest score
    if domain_scores:
        best_domain = max(domain_scores, key=domain_scores.get)
        if domain_scores[best_domain] >= 3:  # Minimum 3 keyword matches
            return best_domain
    
    return 'general'  # Default if no clear domain


def count_keywords_in_text(text: str, keywords: List[str]) -> int:
    """Count how many keywords appear in text (case-insensitive)"""
    text_lower = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in text_lower)


def compute_semantic_experience_boost(cv_sections: Dict[str, str], jd_text: str, base_exp_match: float) -> float:
    """
    Boost experience match score if CV demonstrates relevant domain experience
    even if job title doesn't match exactly
    
    Args:
        cv_sections: Parsed CV sections (experience, skills, etc.)
        jd_text: Job description text
        base_exp_match: Original experience match score
    
    Returns:
        Adjusted experience match score (0.0 to 1.0)
    """
    # Detect job domain
    job_domain = detect_job_domain(jd_text)
    
    if job_domain == 'general':
        return base_exp_match  # No boost for general jobs
    
    # Get domain keywords
    domain_keywords = get_domain_keywords().get(job_domain, [])
    
    # Check CV for domain keywords
    cv_experience = cv_sections.get('experience', '')
    cv_skills = cv_sections.get('skills', '')
    cv_projects = cv_sections.get('projects', '')
    
    combined_cv_text = f"{cv_experience} {cv_skills} {cv_projects}"
    
    keyword_matches = count_keywords_in_text(combined_cv_text, domain_keywords)
    
    # Boost logic
    if keyword_matches >= 6:
        boost = 0.25  # Strong domain match
        print(f"   Semantic boost (+0.25): {keyword_matches} {job_domain} keywords found")
    elif keyword_matches >= 4:
        boost = 0.15  # Good domain match
        print(f"   Semantic boost (+0.15): {keyword_matches} {job_domain} keywords found")
    elif keyword_matches >= 2:
        boost = 0.10  # Some domain match
        print(f"   Semantic boost (+0.10): {keyword_matches} {job_domain} keywords found")
    else:
        boost = 0.0  # No significant match
    
    # Apply boost but cap at 1.0
    adjusted_score = min(base_exp_match + boost, 1.0)
    
    return adjusted_score

def compute_title_similarity(cv_title: str, jd_text: str) -> float:
    """Calculate title similarity"""
    if not cv_title or not jd_text:
        return 0.5
    
    cv_title = str(cv_title).lower().strip()
    jd_title = jd_text[:200].lower().strip()
    
    if not cv_title or not jd_title:
        return 0.5
    
    similarity = SequenceMatcher(None, cv_title, jd_title).ratio()
    return round(float(similarity), 3)


def compute_experience_match(cv_exp: float, jd_text: str) -> float:
    """Calculate experience match"""
    try:
        cv_exp = float(cv_exp) if cv_exp is not None else 0.0
    except:
        cv_exp = 0.0
    
    exp_pattern = r'(\d+)\+?\s*(?:to|-|–)\s*(\d+)?\s*years?'
    matches = re.findall(exp_pattern, jd_text.lower())
    
    if matches:
        jd_min = int(matches[0][0])
        jd_max = int(matches[0][1]) if matches[0][1] else jd_min + 2
    else:
        jd_min, jd_max = 2, 5
    
    if cv_exp < jd_min:
        match = cv_exp / max(jd_min, 1)
        return round(float(max(0, match)), 3)
    elif cv_exp > jd_max:
        penalty = (cv_exp - jd_max) / 10
        match = 1.0 - penalty
        return round(float(max(0, match)), 3)
    else:
        return 1.0


def compute_education_match(cv_edu: str, jd_text: str) -> int:
    """Calculate education match"""
    if not cv_edu or not jd_text:
        return 1
    
    jd_lower = jd_text.lower()
    
    has_masters = 'master' in cv_edu.lower()
    has_bachelors = 'bachelor' in cv_edu.lower()
    
    if 'master' in jd_lower and 'required' in jd_lower and not has_masters:
        return 0
    
    if 'bachelor' in jd_lower and 'required' in jd_lower and not has_bachelors:
        return 0
    
    return 1


def extract_location_from_cv(raw_text: str, sections: Dict) -> str:
    """Extract location from CV"""
    if not raw_text:
        return "Colombo, Sri Lanka"
    
    lines = raw_text.split('\n')[:15]
    
    sl_cities = [
        'Colombo', 'Kandy', 'Galle', 'Jaffna', 'Negombo', 'Moratuwa',
        'Maharagama', 'Nugegoda', 'Dehiwala', 'Mount Lavinia', 'Kelaniya',
        'Gampaha', 'Kalutara', 'Panadura', 'Kaduwela', 'Battaramulla'
    ]
    
    for line in lines:
        line_clean = line.strip()
        for city in sl_cities:
            if city.lower() in line_clean.lower():
                return f"{city}, Sri Lanka"
    
    return "Colombo, Sri Lanka"


def extract_location_from_jd(jd_text: str) -> str:
    """Extract location from JD"""
    if not jd_text:
        return "Colombo, Sri Lanka"
    
    location_patterns = [
        r'Location:\s*([^\n]+)',
        r'Based in:\s*([^\n]+)',
        r'Office:\s*([^\n]+)',
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, jd_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return "Colombo, Sri Lanka"


async def compute_location_match_with_geocoding(cv_loc: str, jd_loc: str) -> float:
    """Compute location match with geocoding"""
    try:
        from app.services.geocoding_service import get_geocoding_service
        
        geocoding = get_geocoding_service()
        distance_km, risk = await geocoding.calculate_commute_distance(cv_loc, jd_loc)
        
        score = geocoding.get_location_match_score(distance_km, risk)
        return float(score)
        
    except Exception as e:
        print(f" Geocoding failed: {e}")
        return 0.7


# ============================================================
# MAIN FEATURE EXTRACTION
# ============================================================

async def create_feature_vector_from_mongo(
    cv_document: Dict, 
    jd_text: str, 
    jd_location: str = None
) -> Dict[str, float]:
    """Enhanced feature extraction"""
    
    sections = cv_document.get("sections", {})
    raw_text = cv_document.get("raw_text", "")
    
    # Parse experience
    jobs = parse_experience_from_sections(sections)
    
    # Basic stats
    n_jobs = len(jobs)
    total_exp_months = sum(job.get('tenure_months', 0) for job in jobs)
    total_exp_years = round(total_exp_months / 12, 1)
    
    avg_tenure_months = total_exp_months / max(n_jobs, 1)
    current_job_tenure = jobs[0].get('tenure_months', 0) if jobs else 0
    
    # Advanced features
    short_stints = count_short_stints(jobs, threshold_months=12)
    job_hopping_rate = calculate_job_hopping_rate(jobs)
    tenure_slope = calculate_tenure_slope(jobs)
    industry_switches = calculate_industry_switches(jobs)
    has_progression, progression_jumps = detect_career_progression(jobs)
    
    # Education
    education_text = sections.get("education", "")
    has_masters = 'master' in education_text.lower()
    n_edu = len(re.findall(r'Bachelor|Master|PhD|Diploma', education_text, re.IGNORECASE))
    
    # Skills
    skills_text = sections.get("skills", "")
    skill_list = [s.strip() for s in skills_text.split(',') if s.strip()]
    n_skills = len(skill_list)
    
    # Matching scores
    skill_match = compute_skill_match_with_esco(skills_text, jd_text)
    title_match = compute_title_similarity(jobs[0].get('title', '') if jobs else '', jd_text)
    exp_match = compute_experience_match(total_exp_years, jd_text)
    edu_match = compute_education_match(education_text, jd_text)
    
    exp_match = compute_semantic_experience_boost(sections, jd_text, exp_match)
    edu_match = compute_education_match(education_text, jd_text)

    # Location
    cv_location = extract_location_from_cv(raw_text, sections)
    jd_location_extracted = extract_location_from_jd_enhanced(jd_text) if not jd_location else jd_location
    loc_match = await compute_location_match_with_geocoding(cv_location, jd_location_extracted)
    
    overall_match = (skill_match + title_match + exp_match + edu_match + loc_match) / 5
    
    # Qualification flags
    exp_matches = re.findall(r'(\d+)\+?\s*(?:to|-)\s*(\d+)?\s*years?', jd_text.lower())
    if exp_matches:
        jd_min = int(exp_matches[0][0])
        jd_max = int(exp_matches[0][1]) if exp_matches[0][1] else jd_min + 2
    else:
        jd_min, jd_max = 2, 5
    
    is_overqualified = 1 if total_exp_years > jd_max + 2 else 0
    is_underqualified = 1 if total_exp_years < jd_min - 0.5 else 0
    
    # Complete feature dictionary
    features = {
        'skill_match_score': skill_match,
        'title_match_score': title_match,
        'exp_match_score': exp_match,
        'edu_match_score': float(edu_match),
        'location_match_score': loc_match,
        'overall_match_score': overall_match,
        
        'is_overqualified': is_overqualified,
        'is_underqualified': is_underqualified,
        
        'total_jobs': float(n_jobs),
        'total_exp_years': float(total_exp_years),
        'avg_tenure_months': float(avg_tenure_months),
        'current_job_tenure': float(current_job_tenure),
        
        'short_stints_count': float(short_stints),
        'job_hopping_rate': float(job_hopping_rate),
        'tenure_slope': float(tenure_slope),
        'industry_switches': float(industry_switches),
        
        'has_progression': 1.0 if has_progression else 0.0,
        'progression_jumps': float(progression_jumps),
        
        'has_masters': 1.0 if has_masters else 0.0,
        'n_education': float(n_edu),
        'n_skills': float(n_skills),
        'n_certifications': 0.0,
        
        'is_remote_cv': 0.0,
        'is_remote_jd': 1.0 if 'remote' in jd_text.lower() else 0.0,
        'work_mode_mismatch': 0.0,
        
        'region': 'colombo_metro',
        'university_tier': 'other_state_university',
        'has_career_gap': 0.0,
        'career_gap_months': 0.0,
        'is_remote_preference': 0.0
    }
    
    return features