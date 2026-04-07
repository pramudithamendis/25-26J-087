import logging
import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Tuple

import numpy as np
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

# ============================================================
# CONSTANTS
# ============================================================

# Minimum fuzzy match threshold for ESCO skill matching
ESCO_SKILL_MATCH_THRESHOLD = 70

# Minimum keyword matches required to classify a job domain
DOMAIN_MIN_KEYWORD_MATCHES = 3

# Semantic boost values based on domain keyword match count
SEMANTIC_BOOST_STRONG = 0.25   # 6+ keyword matches
SEMANTIC_BOOST_GOOD = 0.15     # 4-5 keyword matches
SEMANTIC_BOOST_SOME = 0.10     # 2-3 keyword matches

# Short stint threshold (jobs below this duration count as short stints)
SHORT_STINT_THRESHOLD_MONTHS = 12

# Default tenure assigned when date parsing fails
DEFAULT_TENURE_MONTHS = 12

# Default location used when CV or JD location cannot be determined
DEFAULT_LOCATION = "Colombo, Sri Lanka"

# Number of header lines to scan when extracting CV location from raw text
CV_LOCATION_SCAN_LINES = 15

# Skills that require word boundary matching due to short or ambiguous names
BOUNDARY_SKILLS = {
    'c', 'r', 'go', 'c#', 'c++', 'sql', 'git', 'iis', 'lua', 'sap',
    'ssl', 'jwt', 'xml', 'json', 'css', 'html', 'sass', 'tdd', 'bdd',
    'nlp', 'llm', 'etl', 'dbt', 'svn', 'ios', 'rag', 'k6', 'wpf',
}

# ============================================================
# SKILLS LIST
# Comprehensive list of common IT skills used for keyword-based
# skill matching between CV text and job descriptions.
# ============================================================

COMMON_SKILLS = [
    # Languages
    'python', 'java', 'javascript', 'typescript', 'c#', 'c++', 'c',
    'go', 'rust', 'ruby', 'php', 'scala', 'r', 'perl', 'haskell',
    'dart', 'kotlin', 'swift', 'objective-c',
    'bash', 'powershell', 'groovy', 'lua', 'elixir', 'clojure',
    # Web Frameworks
    'react', 'angular', 'vue', 'next.js', 'nuxt', 'svelte',
    'node.js', 'express', 'fastapi', 'django', 'flask',
    'spring boot', 'spring', 'laravel', 'rails', 'symfony',
    'asp.net', '.net core', '.net', 'blazor', 'razor', 'htmx', 'jquery',
    # Mobile
    'flutter', 'react native', 'ionic', 'xamarin',
    'android', 'ios', 'swift ui', 'jetpack compose',
    'wpf', 'maui', 'cordova', 'expo', 'capacitor',
    # Data Engineering
    'delta lake', 'apache iceberg', 'apache flink', 'apache beam',
    'google bigquery', 'azure synapse', 'duckdb', 'polars', 'plotly',
    'fivetran', 'great expectations',
    # Databases
    'sql', 'mysql', 'postgresql', 'mssql', 'ms sql server', 'sqlite',
    'mongodb', 'redis', 'cassandra', 'dynamodb', 'firestore',
    'elasticsearch', 'neo4j', 'influxdb', 'couchdb',
    'oracle', 'mariadb', 'supabase',
    'entity framework', 'hibernate', 'prisma', 'sequelize',
    'data pipeline', 'data pipelines', 'data warehouse', 'data warehousing',
    'data modeling', 'data governance', 'data quality',
    'pyspark', 'apache airflow', 'apache kafka', 'apache spark',
    'aws redshift', 'aws lambda', 'aws s3',
    'grafana', 'kibana', 'dbt', 'databricks', 'snowflake',
    # Cloud & Infrastructure
    'aws', 'azure', 'gcp', 'google cloud',
    'docker', 'kubernetes', 'terraform', 'ansible', 'puppet', 'chef',
    'helm', 'istio', 'nginx', 'apache',
    'serverless', 'lambda', 'cloud functions',
    'heroku', 'vercel', 'netlify', 'digitalocean',
    # DevOps & CI/CD
    'devops', 'ci/cd', 'jenkins', 'gitlab', 'github actions',
    'circleci', 'travis ci', 'bamboo', 'argocd',
    'git', 'github', 'bitbucket', 'svn',
    'linux', 'unix', 'windows server', 'iis',
    'azure devops', 'jira', 'confluence',
    'datadog', 'prometheus', 'opentelemetry', 'new relic', 'loki',
    # Firebase & Mobile Backend
    'firebase', 'fcm', 'push notifications',
    'google play', 'app store', 'testflight',
    # APIs & Architecture
    'rest api', 'restful', 'graphql', 'grpc', 'websocket',
    'microservices', 'event-driven', 'message queue',
    'rabbitmq', 'kafka', 'activemq',
    'soap', 'xml', 'json', 'openapi', 'swagger',
    # AI / ML / Data
    'machine learning', 'deep learning', 'data science', 'nlp',
    'computer vision', 'tensorflow', 'pytorch', 'keras',
    'scikit-learn', 'pandas', 'numpy', 'matplotlib',
    'data analysis', 'data engineering', 'etl',
    'spark', 'hadoop', 'airflow', 'dbt',
    'power bi', 'tableau', 'looker',
    'openai', 'langchain', 'llm',
    'generative ai', 'prompt engineering', 'rag', 'vector database',
    'hugging face', 'embeddings', 'fine-tuning', 'llamaindex', 'ollama',
    'pinecone', 'weaviate',
    # Security
    'cybersecurity', 'penetration testing', 'owasp',
    'oauth', 'jwt', 'ssl', 'encryption',
    'siem', 'vulnerability assessment', 'devsecops', 'sonarqube', 'snyk',
    # Testing
    'unit testing', 'integration testing', 'selenium',
    'cypress', 'jest', 'pytest', 'junit',
    'postman', 'test automation', 'tdd', 'bdd',
    'playwright', 'vitest', 'k6', 'locust',
    # Design & Frontend
    'html', 'css', 'sass', 'tailwind', 'bootstrap',
    'figma', 'adobe xd', 'ui/ux', 'responsive design', 'accessibility',
    # Methodologies
    'agile', 'scrum', 'kanban', 'waterfall',
    'solid', 'design patterns', 'clean architecture',
    'tdd', 'pair programming', 'code review',
    'domain driven design', 'event sourcing', 'cqrs', 'protobuf',
    # Other
    'blockchain', 'web3', 'solidity',
    'iot', 'embedded', 'raspberry pi', 'arduino',
    'unity', 'unreal', 'game development',
    'sap', 'salesforce', 'dynamics', 'sharepoint', 'power automate',
    # Sri Lanka specific
    'wso2', 'odoo', 'zoho',
]

# ============================================================
# INDUSTRY AND SENIORITY MAPPINGS
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

# Seniority levels ordered 0 (intern) to 8 (C-suite).
# Titles not matching any keyword default to level 2 (mid-level).
SENIORITY_LEVELS = {
    'intern': 0, 'trainee': 0, 'junior': 1, 'associate': 1,
    'mid': 2, 'senior': 3, 'lead': 4, 'principal': 4,
    'staff': 4, 'manager': 5, 'director': 6, 'head': 6,
    'vp': 7, 'cto': 8, 'ceo': 8,
}

# Sri Lankan cities used across CV and JD location extraction
SL_CITIES = [
    'Colombo', 'Kandy', 'Galle', 'Jaffna', 'Negombo', 'Moratuwa',
    'Maharagama', 'Nugegoda', 'Dehiwala', 'Mount Lavinia', 'Kelaniya',
    'Gampaha', 'Kalutara', 'Panadura', 'Kaduwela', 'Battaramulla',
]


# ============================================================
# LOCATION EXTRACTION
# ============================================================

def extract_location_from_jd_enhanced(jd_text: str) -> str:
    """
    Extract job location from a job description using pattern matching.

    Tries common location label patterns first, then scans for known
    Sri Lankan city names. Returns the default location if nothing found.

    Args:
        jd_text: Raw job description text.

    Returns:
        Location string in the format 'City, Sri Lanka'.
    """
    if not jd_text:
        return DEFAULT_LOCATION

    for pattern in [
        r'Location:\s*([^\n]+)', r'Based in:\s*([^\n]+)',
        r'Office:\s*([^\n]+)', r'Work Location:\s*([^\n]+)',
    ]:
        match = re.search(pattern, jd_text, re.IGNORECASE)
        if match:
            location = match.group(1).strip().split(',')[0].strip()
            if location and len(location) > 2:
                return f"{location}, Sri Lanka"

    for city in SL_CITIES:
        if city.lower() in jd_text.lower():
            return f"{city}, Sri Lanka"

    return DEFAULT_LOCATION


def extract_location_from_cv(raw_text: str, sections: Dict, basics: Dict = None) -> str:
    """
    Extract candidate location from CV document.

    Checks structured basics.address first, then
    scans the first lines of raw CV text for known city names.

    Args:
        raw_text: Raw CV text string.
        sections: Parsed CV sections dict.
        basics: Optional basics dict from CVParsed format.

    Returns:
        Location string in the format 'City, Sri Lanka'.
    """
    if basics:
        address = basics.get("address", "")
        if address:
            for city in SL_CITIES:
                if city.lower() in address.lower():
                    return f"{city}, Sri Lanka"
            if len(address) > 3:
                return address

    if not raw_text:
        return DEFAULT_LOCATION

    for line in raw_text.split('\n')[:CV_LOCATION_SCAN_LINES]:
        for city in SL_CITIES:
            if city.lower() in line.strip().lower():
                return f"{city}, Sri Lanka"

    return DEFAULT_LOCATION


def extract_location_from_jd(jd_text: str) -> str:
    """
    Basic JD location extraction using label patterns only.

    Args:
        jd_text: Raw job description text.

    Returns:
        Extracted location string or the default location.
    """
    if not jd_text:
        return DEFAULT_LOCATION
    for pattern in [r'Location:\s*([^\n]+)', r'Based in:\s*([^\n]+)', r'Office:\s*([^\n]+)']:
        match = re.search(pattern, jd_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return DEFAULT_LOCATION


def extract_city_from_address(address: str) -> str:
    """
    Extract a city name from a full street address string.

    Splits by comma and returns the last meaningful non-numeric part.
    Used as a fallback when the address cannot be matched to a known city.

    Args:
        address: Full address string.

    Returns:
        City string in the format 'City, Sri Lanka'.
    """
    if not address:
        return DEFAULT_LOCATION
    for part in reversed([p.strip() for p in address.split(',') if p.strip()]):
        if re.match(r'^[\d/\-]+$', part):
            continue
        if len(part) < 3:
            continue
        if re.search(r'\d', part) and len(part) < 10:
            continue
        return f"{part}, Sri Lanka"
    return DEFAULT_LOCATION


# ============================================================
# EXPERIENCE PARSING
# ============================================================

def normalize_experience_text(text: str) -> str:
    """
    Normalise PDF-extracted experience text by rejoining broken lines.

    PDF extraction often splits a single line across multiple lines due
    to page width constraints. Detects incomplete lines and joins them.

    Args:
        text: Raw experience section text from PDF extraction.

    Returns:
        Normalised text with broken lines rejoined.
    """
    lines = text.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        while i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if not next_line:
                break

            if re.search(r'(?:–|—|-)\s*$', line):
                if re.match(
                    r'^(?:Present|Current|Now|\d{4}|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)',
                    next_line, re.IGNORECASE
                ):
                    line = line.rstrip() + ' ' + next_line
                    i += 1
                    continue

            if re.match(r'^(?:Present|Current|Now)$', next_line, re.IGNORECASE):
                if re.search(r'(?:–|—|-|to)\s*$', line):
                    line = line.rstrip() + ' ' + next_line
                    i += 1
                    continue

            is_incomplete = (
                not re.search(r'[.!?|]\s*$', line)
                and not re.match(r'^[•\*\-]', next_line)
                and not re.search(r'\d{4}', line[-15:])
                and not re.search(
                    r'^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{4})',
                    next_line, re.IGNORECASE
                )
                and len(line) > 40
                and len(next_line) > 5
            )

            if is_incomplete:
                line = line + ' ' + next_line
                i += 1
                continue
            break

        result.append(line)
        i += 1

    return '\n'.join(result)


def parse_experience_from_sections(sections: Dict[str, str]) -> List[Dict]:
    """
    Parse job entries from the experience section of an old-format CV.

    Detects date ranges, extracts job titles from surrounding lines,
    and computes tenure for each position found.

    Args:
        sections: Dict of CV sections with 'experience' key.

    Returns:
        List of job dicts with 'title', 'tenure_months', 'start_date', 'end_date'.
    """
    experience_text = sections.get("experience", "")
    if not experience_text:
        return []

    experience_text = normalize_experience_text(experience_text)
    stop_keywords = ['education', 'certifications', 'projects', 'languages', 'skills']

    cleaned_lines = []
    for line in experience_text.split('\n'):
        if any(stop in line.lower() for stop in stop_keywords) and len(line.strip()) < 25:
            break
        if line.strip():
            cleaned_lines.append(line.strip())

    date_pattern = (
        r'(?:'
        r'(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec'
        r'|January|February|March|April|May|June|July|August'
        r'|September|October|November|December)\s+\d{4})'
        r'|(\b\d{4}))'
        r'\s*(?:–|-|to|—)\s*'
        r'(?:'
        r'(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec'
        r'|January|February|March|April|May|June|July|August'
        r'|September|October|November|December)\s+\d{4})'
        r'|(\b\d{4}|Present|Current))'
    )

    jobs = []
    for i, line in enumerate(cleaned_lines):
        date_match = re.search(date_pattern, line, re.IGNORECASE)
        if not date_match:
            continue

        start_date_str = date_match.group(1) or date_match.group(2)
        end_date_str = date_match.group(3) or date_match.group(4)

        if not start_date_str:
            continue
        if not end_date_str:
            end_date_str = "Present"

        if '|' in line or '–' in line.split(start_date_str)[0]:
            title_raw = re.split(r'\|', line)[0].strip()
            title_raw = re.sub(date_pattern, '', title_raw, flags=re.IGNORECASE).strip()
        else:
            title_raw = line
            for back in range(1, min(i + 1, 5)):
                prev_line = cleaned_lines[i - back]
                if prev_line == '•' or len(prev_line) <= 2:
                    continue
                if len(prev_line) > 100:
                    continue
                title_raw = prev_line
                break

        title_raw = title_raw.split('|')[0].split('–')[0].split('-')[0].strip()
        title_raw = re.sub(r'\s+', ' ', title_raw).strip()

        jobs.append({
            'title': title_raw,
            'tenure_months': calculate_tenure(start_date_str, end_date_str),
            'start_date': start_date_str,
            'end_date': end_date_str,
        })

    return jobs


def parse_date_range(date_text: str) -> tuple:
    """
    Parse a date range string into start and end date strings.

    Args:
        date_text: Raw date range string (e.g. 'May 2018 – Jan 2021').

    Returns:
        Tuple of (start_date_str, end_date_str).
    """
    for sep in ['–', '—', ' to ', ' - ', '--']:
        if sep in date_text:
            parts = date_text.split(sep, 1)
            return parts[0].strip(), parts[1].strip() if len(parts) > 1 else "Present"
    return date_text.strip(), "Present"


def calculate_tenure(start_str: str, end_str: str) -> int:
    """
    Calculate tenure in months between two date strings.

    Year-only dates default to July (mid-year) for accuracy.
    Returns DEFAULT_TENURE_MONTHS if parsing fails.

    Args:
        start_str: Start date string.
        end_str: End date string or 'Present'/'Current'/'Now'.

    Returns:
        Tenure in months as an integer.
    """
    try:
        start_str = start_str.strip()
        end_str = end_str.strip()

        if re.match(r'^\d{4}$', start_str):
            start_str = f"Jul {start_str}"
        if re.match(r'^\d{4}$', end_str) and end_str.lower() not in ['present', 'current', 'now']:
            end_str = f"Jul {end_str}"

        start = date_parser.parse(start_str, fuzzy=True)
        end = (
            datetime.now()
            if end_str.lower() in ['present', 'current', 'now', '']
            else date_parser.parse(end_str, fuzzy=True)
        )

        return max(0, (end.year - start.year) * 12 + (end.month - start.month))

    except Exception as e:
        logger.debug(f"Date parsing error: '{start_str}' to '{end_str}' — {e}")
        return DEFAULT_TENURE_MONTHS


# ============================================================
# INDUSTRY DETECTION
# ============================================================

def detect_industry(company_name: str, job_title: str, responsibilities: List[str]) -> str:
    """
    Classify a job into an industry category based on contextual keywords.

    Args:
        company_name: Name of the company.
        job_title: Job title string.
        responsibilities: List of responsibility strings.

    Returns:
        Industry category string, or 'general_tech' if no match.
    """
    text = f"{company_name} {job_title} {' '.join(responsibilities)}".lower()
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return industry
    return 'general_tech'


def calculate_industry_switches(jobs: List[Dict]) -> int:
    """
    Count the number of times a candidate switched industries across jobs.

    Args:
        jobs: List of job dicts with 'company', 'title', 'responsibilities'.

    Returns:
        Number of industry switches.
    """
    if len(jobs) <= 1:
        return 0
    industries = [
        detect_industry(j.get('company', ''), j.get('title', ''), j.get('responsibilities', []))
        for j in jobs
    ]
    return sum(1 for i in range(1, len(industries)) if industries[i] != industries[i - 1])


# ============================================================
# TENURE ANALYSIS
# ============================================================

def calculate_tenure_slope(jobs: List[Dict]) -> float:
    """
    Calculate the linear trend of job tenures across a candidate's career.

    Positive slope = tenures increasing (growing commitment).
    Negative slope = tenures decreasing (possible restlessness).

    Args:
        jobs: List of job dicts ordered most-recent first, each with 'tenure_months'.

    Returns:
        Slope value rounded to 2 decimal places, or 0.0 if fewer than 2 jobs.
    """
    if len(jobs) < 2:
        return 0.0

    tenures = [job.get('tenure_months', 0) for job in jobs][::-1]
    x = np.arange(len(tenures))
    y = np.array(tenures)
    x_mean, y_mean = x.mean(), y.mean()
    numerator = np.sum((x - x_mean) * (y - y_mean))
    denominator = np.sum((x - x_mean) ** 2)

    return 0.0 if denominator == 0 else round(float(numerator / denominator), 2)


def count_short_stints(
    jobs: List[Dict], threshold_months: int = SHORT_STINT_THRESHOLD_MONTHS
) -> int:
    """
    Count jobs where tenure was below the short stint threshold.

    Args:
        jobs: List of job dicts each with 'tenure_months'.
        threshold_months: Maximum months to classify as a short stint.

    Returns:
        Count of short-tenure jobs.
    """
    return sum(1 for job in jobs if job.get('tenure_months', 0) < threshold_months)


def calculate_job_hopping_rate(jobs: List[Dict]) -> float:
    """
    Calculate the proportion of jobs that were short stints.

    Args:
        jobs: List of job dicts.

    Returns:
        Float between 0.0 and 1.0. Returns 0.0 for single-job candidates.
    """
    total_jobs = len(jobs)
    if total_jobs <= 1:
        return 0.0
    return round(count_short_stints(jobs) / total_jobs, 2)


# ============================================================
# CAREER PROGRESSION
# ============================================================

def get_seniority_level(job_title: str) -> int:
    """
    Extract a numeric seniority level from a job title string.

    Args:
        job_title: Raw job title string.

    Returns:
        Integer seniority level (0=intern to 8=CEO). Defaults to 2 (mid).
    """
    title_lower = job_title.lower()
    for keyword, level in SENIORITY_LEVELS.items():
        if keyword in title_lower:
            return level
    return 2


def detect_career_progression(jobs: List[Dict]) -> Tuple[bool, int]:
    """
    Detect whether a candidate's career shows upward seniority progression.

    Args:
        jobs: List of job dicts ordered most-recent first, each with 'title'.

    Returns:
        Tuple of (has_progression, progression_jumps).
    """
    if len(jobs) < 2:
        return False, 0

    levels = [get_seniority_level(job.get('title', '')) for job in jobs][::-1]
    progression_jumps = sum(1 for i in range(1, len(levels)) if levels[i] > levels[i - 1])
    return progression_jumps > 0, progression_jumps


# ============================================================
# SKILL MATCHING
# ============================================================

def skill_in_text(skill: str, text_lower: str) -> bool:
    """
    Check whether a skill appears in a text string.

    Uses word boundary matching for short or ambiguous skill names
    to avoid false matches inside longer words.

    Args:
        skill: Skill string to search for.
        text_lower: Lowercased target text.

    Returns:
        True if the skill is found in the text.
    """
    if skill in BOUNDARY_SKILLS or len(skill) <= 3:
        return bool(re.search(r'\b' + re.escape(skill) + r'\b', text_lower))
    return skill in text_lower


def extract_skills_from_jd(jd_text: str) -> list:
    """
    Extract all recognised skills from job description text.

    Args:
        jd_text: Raw job description text.

    Returns:
        List of matched skill strings from COMMON_SKILLS.
    """
    if not jd_text:
        return []
    jd_lower = jd_text.lower()
    return [skill for skill in COMMON_SKILLS if skill_in_text(skill, jd_lower)]


def compute_skill_match_traditional(cv_skills: str, jd_text: str) -> float:
    """
    Compute skill match score using keyword overlap between CV and JD.

    Returns proportion of JD skills covered by CV skills (Jaccard over JD set).
    Returns 0.5 as default when either text is empty or no JD skills found.

    Args:
        cv_skills: Skills text from CV.
        jd_text: Job description text.

    Returns:
        Float between 0.0 and 1.0.
    """
    cv_lower = cv_skills.lower() if cv_skills else ""
    jd_lower = jd_text.lower() if jd_text else ""

    if not cv_lower or not jd_lower:
        return 0.5

    cv_skills_set = {skill for skill in COMMON_SKILLS if skill_in_text(skill, cv_lower)}
    jd_skills_set = {skill for skill in COMMON_SKILLS if skill_in_text(skill, jd_lower)}

    if not jd_skills_set:
        return 0.5

    return round(len(cv_skills_set & jd_skills_set) / len(jd_skills_set), 3)


def compute_skill_match_with_esco(cv_skills: str, jd_text: str) -> float:
    """
    Compute skill match score using ESCO semantic matching with keyword fallback.

    Blends ESCO-normalised matching with traditional keyword matching.
    Falls back entirely to traditional matching if ESCO is unavailable.
    Returns 0.5 if either input is empty.

    Args:
        cv_skills: Skills text from CV.
        jd_text: Job description text.

    Returns:
        Blended skill match score between 0.0 and 1.0.
    """
    if not cv_skills or not jd_text:
        return 0.5

    try:
        from app.services.esco_mapper import get_esco_mapper

        esco = get_esco_mapper()
        if esco is None:
            return compute_skill_match_traditional(cv_skills, jd_text)

        cv_skills_list = [
            s.strip()
            for s in re.split(r'[,\n•\|]+|(?:\s{2,})', cv_skills)
            if s.strip() and len(s.strip()) > 1
        ]
        jd_skills_list = extract_skills_from_jd(jd_text)

        if not cv_skills_list or not jd_skills_list:
            return 0.5

        esco_score = esco.calculate_esco_skill_match(
            cv_skills_list, jd_skills_list, threshold=ESCO_SKILL_MATCH_THRESHOLD
        )
        traditional_score = compute_skill_match_traditional(cv_skills, jd_text)

        if esco_score == 0:
            return traditional_score

        return round((float(esco_score) + traditional_score) / 2, 3)

    except Exception as e:
        logger.warning(f"ESCO skill match failed — falling back to traditional: {e}")
        return compute_skill_match_traditional(cv_skills, jd_text)


# ============================================================
# DOMAIN-BASED SEMANTIC EXPERIENCE BOOST
# ============================================================

def get_domain_keywords() -> Dict[str, List[str]]:
    """
    Return domain-specific keyword sets for semantic experience matching.

    Returns:
        Dict mapping domain name to list of representative keywords.
    """
    return {
        'devops': ['CI/CD', 'Docker', 'Kubernetes', 'Jenkins', 'Terraform', 'AWS',
                   'Azure', 'GCP', 'Ansible', 'GitLab', 'pipeline', 'infrastructure as code'],
        'data_engineering': ['ETL', 'ELT', 'data pipeline', 'Airflow', 'Spark',
                             'data warehouse', 'Snowflake', 'Redshift', 'BigQuery', 'dbt'],
        'data_science': ['machine learning', 'ML', 'deep learning', 'neural network',
                         'TensorFlow', 'PyTorch', 'scikit-learn', 'NLP', 'computer vision',
                         'predictive model'],
        'backend': ['API', 'REST', 'GraphQL', 'microservices', 'Node.js', 'Django',
                    'Flask', 'Spring Boot', 'database', 'SQL', 'NoSQL'],
        'frontend': ['React', 'Angular', 'Vue', 'JavaScript', 'TypeScript', 'CSS',
                     'HTML', 'responsive design', 'UI/UX'],
        'mobile': ['iOS', 'Android', 'React Native', 'Flutter', 'Swift', 'Kotlin', 'mobile app'],
        'security': ['cybersecurity', 'penetration testing', 'vulnerability', 'security audit',
                     'encryption', 'firewall', 'SIEM'],
        'qa': ['testing', 'QA', 'automation', 'Selenium', 'test case', 'bug tracking',
               'quality assurance'],
    }


def detect_job_domain(jd_text: str) -> str:
    """
    Detect the primary job domain from a job description.

    Args:
        jd_text: Raw job description text.

    Returns:
        Domain string, or 'general' if no clear domain is detected.
    """
    jd_lower = jd_text.lower()
    domain_scores = {
        domain: sum(1 for kw in keywords if kw.lower() in jd_lower)
        for domain, keywords in get_domain_keywords().items()
    }
    best_domain = max(domain_scores, key=domain_scores.get)
    return best_domain if domain_scores[best_domain] >= DOMAIN_MIN_KEYWORD_MATCHES else 'general'


def count_keywords_in_text(text: str, keywords: List[str]) -> int:
    """
    Count how many keywords from a list appear in a text string.

    Args:
        text: Target text string.
        keywords: List of keywords to search for.

    Returns:
        Count of matched keywords.
    """
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw.lower() in text_lower)


def compute_semantic_experience_boost(
    cv_sections: Dict[str, str],
    jd_text: str,
    base_exp_match: float,
) -> float:
    """
    Boost experience match when CV demonstrates relevant domain expertise.

    Addresses cases where a candidate has strong domain experience but their
    job title does not exactly match the JD. Boost levels by keyword count:
    6+ matches: +0.25, 4-5: +0.15, 2-3: +0.10, <2: no boost.

    Args:
        cv_sections: Dict of CV sections (experience, skills, projects).
        jd_text: Raw job description text.
        base_exp_match: Experience match score before boosting.

    Returns:
        Adjusted experience match score capped at 1.0.
    """
    job_domain = detect_job_domain(jd_text)
    if job_domain == 'general':
        return base_exp_match

    domain_keywords = get_domain_keywords().get(job_domain, [])
    combined_cv_text = ' '.join([
        cv_sections.get('experience', ''),
        cv_sections.get('skills', ''),
        cv_sections.get('projects', ''),
    ])

    keyword_matches = count_keywords_in_text(combined_cv_text, domain_keywords)

    if keyword_matches >= 6:
        boost = SEMANTIC_BOOST_STRONG
    elif keyword_matches >= 4:
        boost = SEMANTIC_BOOST_GOOD
    elif keyword_matches >= 2:
        boost = SEMANTIC_BOOST_SOME
    else:
        boost = 0.0

    if boost > 0:
        logger.debug(f"Semantic boost +{boost}: {keyword_matches} {job_domain} keywords found")

    return min(base_exp_match + boost, 1.0)


# ============================================================
# MATCHING FUNCTIONS
# ============================================================

def compute_title_similarity(cv_title: str, jd_text: str) -> float:
    """
    Compute similarity between candidate's most recent job title and the JD.

    Uses Python's SequenceMatcher for character-level string similarity.
    Returns 0.5 as default if either input is empty.

    Args:
        cv_title: Most recent job title from CV.
        jd_text: Job description text (first 200 chars used as JD title proxy).

    Returns:
        Similarity ratio between 0.0 and 1.0.
    """
    if not cv_title or not jd_text:
        return 0.5
    cv_title = str(cv_title).lower().strip()
    jd_title = jd_text[:200].lower().strip()
    if not cv_title or not jd_title:
        return 0.5
    return round(float(SequenceMatcher(None, cv_title, jd_title).ratio()), 3)


def compute_experience_match(cv_exp: float, jd_text: str) -> float:
    """
    Compute experience match score by comparing CV years against JD requirements.

    Candidates below the minimum score proportionally.
    Candidates above the maximum are penalised for overqualification.

    Args:
        cv_exp: Total years of experience from CV.
        jd_text: Job description text.

    Returns:
        Experience match score between 0.0 and 1.0.
    """
    try:
        cv_exp = float(cv_exp) if cv_exp is not None else 0.0
    except Exception:
        cv_exp = 0.0

    matches = re.findall(r'(\d+)\+?\s*(?:to|-|–)\s*(\d+)?\s*years?', jd_text.lower())
    if matches:
        jd_min = int(matches[0][0])
        jd_max = int(matches[0][1]) if matches[0][1] else jd_min + 2
    else:
        jd_min, jd_max = 2, 5

    if cv_exp < jd_min:
        return round(float(max(0, cv_exp / max(jd_min, 1))), 3)
    elif cv_exp > jd_max:
        return round(float(max(0, 1.0 - (cv_exp - jd_max) / 10)), 3)
    return 1.0


def compute_education_match(cv_edu: str, jd_text: str, gpa: float = None) -> int:
    """
    Compute education match between CV education and JD requirements.

    Returns 0 if a required degree is not met, 1 otherwise.

    Args:
        cv_edu: Education section text from CV.
        jd_text: Job description text.
        gpa: Optional GPA value from CV.

    Returns:
        Integer 0 (not matched) or 1 (matched).
    """
    if not cv_edu or not jd_text:
        return 1

    jd_lower = jd_text.lower()
    has_masters = any(kw in cv_edu.lower() for kw in ['master', 'msc', 'm.sc', 'mba'])
    has_bachelors = any(kw in cv_edu.lower() for kw in ['bachelor', 'bsc', 'b.sc'])

    if 'master' in jd_lower and 'required' in jd_lower and not has_masters:
        return 0
    if 'bachelor' in jd_lower and 'required' in jd_lower and not has_bachelors:
        return 0
    if gpa and gpa >= 3.5 and ('gpa' in jd_lower or 'grade' in jd_lower):
        return 1
    return 1


# ============================================================
# LOCATION MATCH
# ============================================================

async def compute_location_match_with_geocoding(cv_loc: str, jd_loc: str) -> float:
    """
    Compute location match score using geocoding-based commute distance.

    Returns a default moderate score (0.7) on geocoding failure.

    Args:
        cv_loc: Candidate location string.
        jd_loc: Job location string.

    Returns:
        Location match score between 0.0 and 1.0.
    """
    try:
        from app.services.geocoding_service import get_geocoding_service
        geocoding = get_geocoding_service()
        distance_km, risk = await geocoding.calculate_commute_distance(cv_loc, jd_loc)
        return float(geocoding.get_location_match_score(distance_km, risk))
    except Exception as e:
        logger.warning(f"Geocoding failed ({type(e).__name__}) — using default score: {e}")
        return 0.7


# ============================================================
# NEW FORMAT HELPERS (CVParsed schema)
# ============================================================

def _parse_jobs_from_new_format(work_list: List[Dict]) -> List[Dict]:
    """
    Parse job entries from the CVParsed work[] array format.

    Args:
        work_list: List of work dicts from CVParsed schema.

    Returns:
        List of normalised job dicts.
    """
    jobs = []
    for w in work_list:
        start_date = w.get('startDate', '')
        if not start_date:
            continue
        end_date = w.get('endDate', '') or 'Present'
        jobs.append({
            'title': w.get('position', '') or '',
            'tenure_months': calculate_tenure(str(start_date), str(end_date)),
            'start_date': str(start_date),
            'end_date': str(end_date),
            'company': w.get('name', ''),
        })
    return jobs


def _extract_skills_text_from_new_format(
    skills_list: List[Dict], work_list: List[Dict], basics: Dict
) -> str:
    """
    Flatten skills, work highlights, and summary from CVParsed format into text.

    Args:
        skills_list: List of skill dicts from CVParsed schema.
        work_list: List of work dicts from CVParsed schema.
        basics: Basics dict from CVParsed schema.

    Returns:
        Single joined text string of all skill-relevant content.
    """
    keywords = []
    for skill in skills_list:
        keywords.extend(skill.get('keywords', []))
        if skill.get('name'):
            keywords.append(skill['name'])
    for w in work_list:
        keywords.extend(w.get('highlights', []))
        if w.get('summary'):
            keywords.append(w['summary'])
    if basics.get('summary'):
        keywords.append(basics['summary'])
    return ' '.join(keywords)


def _extract_education_text_from_new_format(education_list: List[Dict]) -> str:
    """
    Flatten education entries from CVParsed format into a single text string.

    Args:
        education_list: List of education dicts from CVParsed schema.

    Returns:
        Joined text string of institution, area, study type, and courses.
    """
    parts = []
    for edu in education_list:
        parts.extend([
            edu.get('institution', ''), edu.get('area', ''),
            edu.get('studyType', ''),
        ])
        parts.extend(edu.get('courses', []))
    return ' '.join(filter(None, parts))


# ============================================================
# MAIN FEATURE EXTRACTION
# ============================================================

async def create_feature_vector_from_mongo(
    cv_document: Dict,
    jd_text: str,
    jd_location: str = None,
    job_title: str = None,
) -> Dict[str, float]:
    """
    Engineer all 22 features from a stored CV document and job description.

    Supports two CV document formats:
    - Old format: cv_document has a 'sections' dict with raw text strings
    - New format: cv_document has 'work', 'skills', 'education' lists (CVParsed schema)

    Features are grouped into four categories matching the theoretical framework:
    - Job Fit: skill_match, title_match, exp_match, edu_match, overall_match
    - Stability: job_hopping_rate, avg_tenure, current_tenure, short_stints, tenure_slope
    - Career: has_progression, progression_jumps, industry_switches, career_gap
    - Contextual: location_match, work_mode_mismatch, remote preference, education level

    Args:
        cv_document: MongoDB CV document dict.
        jd_text: Raw job description text.
        jd_location: Optional pre-extracted job location string.
        job_title: Optional job title for title match scoring.

    Returns:
        Dict of 22 float feature values keyed by feature name.
    """
    raw_text = cv_document.get("raw_text") or ""
    is_new_format = 'work' in cv_document or 'basics' in cv_document
    logger.info(f"CV format: {'NEW (CVParsed)' if is_new_format else 'OLD (sections)'}")

    # ── Parse jobs ──────────────────────────────────────────────
    jobs = (
        _parse_jobs_from_new_format(cv_document.get('work', []))
        if is_new_format
        else parse_experience_from_sections(cv_document.get("sections", {}))
    )

    n_jobs = len(jobs)
    total_exp_months = sum(job.get('tenure_months', 0) for job in jobs)
    total_exp_years = round(total_exp_months / 12, 1)
    avg_tenure_months = total_exp_months / max(n_jobs, 1)
    current_job_tenure = jobs[0].get('tenure_months', 0) if jobs else 0

    short_stints = count_short_stints(jobs)
    job_hopping_rate = calculate_job_hopping_rate(jobs)
    tenure_slope = calculate_tenure_slope(jobs)
    industry_switches = calculate_industry_switches(jobs)
    has_progression, progression_jumps = detect_career_progression(jobs)

    # ── Education ────────────────────────────────────────────────
    if is_new_format:
        education_list = cv_document.get('education', [])
        education_text = _extract_education_text_from_new_format(education_list)
        gpa_values = []
        for edu in education_list:
            gpa_raw = edu.get('gpa', '')
            if gpa_raw:
                try:
                    gpa_values.append(float(str(gpa_raw).replace(',', '.').strip()))
                except ValueError:
                    pass
        best_gpa = max(gpa_values) if gpa_values else None
    else:
        sections = cv_document.get("sections") or {}
        education_text = sections.get("education") or ""
        education_text = '\n'.join(
            line for line in education_text.split('\n')
            if not re.search(r'\+\d{2}|@|LinkedIn|GitHub|\|.*\|', line)
        )
        best_gpa = None

    has_masters = any(kw in education_text.lower() for kw in ['master', 'msc', 'm.sc', 'mba'])
    n_edu = len(re.findall(
        r'Bachelor|Master|PhD|Diploma|BSc|MSc|MBA|B\.Sc|M\.Sc',
        education_text, re.IGNORECASE
    ))

    # ── Skills ──────────────────────────────────────────────────
    if is_new_format:
        basics = cv_document.get('basics', {}) or {}
        work_list = cv_document.get('work', [])
        skills_list = cv_document.get('skills', [])
        skills_text = _extract_skills_text_from_new_format(skills_list, work_list, basics)

        all_keywords = [kw for skill in skills_list for kw in skill.get('keywords', [])]
        standalone_names = [
            skill['name'] for skill in skills_list
            if skill.get('name') and not skill.get('keywords')
        ]
        n_skills = len(set(all_keywords + standalone_names))

        projects_list = cv_document.get('projects', [])
        project_text = ' '.join([
            ' '.join(filter(None, [p.get('description', ''), ' '.join(p.get('highlights', []))]))
            for p in projects_list
        ])
        combined_cv_text_for_skills = f"{skills_text} {project_text}"

    else:
        sections = cv_document.get("sections") or {}
        skills_text = sections.get("skills") or ""
        skills_text = re.sub(r'Mr\.|Ms\.|Dr\..*', '', skills_text, flags=re.DOTALL)
        skills_text = re.sub(r'[\w\.-]+@[\w\.-]+', '', skills_text)
        skills_text = re.sub(r'\+\d[\d\s]+', '', skills_text)
        skills_text = re.sub(r'•|\*', ' ', skills_text)
        skills_text = re.sub(
            r'\b(?:Backend|Frontend|Database|DevOps|Cloud|Methodology|Languages?|Tools?|Frameworks?)\s*[:/&]\s*',
            ' ', skills_text, flags=re.IGNORECASE
        )
        skills_text = re.sub(r'\([^)]*\)', '', skills_text)
        skills_text = re.sub(r'[^\w\s,\.#\+]', ' ', skills_text)
        skills_text = ' '.join(skills_text.split())

        skills_lines = [
            part.strip()
            for part in re.split(r'[,\n]', skills_text)
            if part.strip()
            and not re.match(r'^[A-Za-z\s&]+:\s*$', part.strip())
            and len(part.strip()) > 1
            and not part.strip().endswith(':')
        ]
        n_skills = len(skills_lines)

        experience_text_for_skills = sections.get("experience", "")
        summary_text = sections.get("summary", "") or sections.get("professional_summary", "")
        combined_cv_text_for_skills = f"{skills_text} {experience_text_for_skills} {summary_text}"

    # ── Certifications ───────────────────────────────────────────
    # Note: certification extraction from old-format CVs not yet implemented
    n_certifications = float(len(cv_document.get('certificates', []))) if is_new_format else 0.0

    # ── Skill match ──────────────────────────────────────────────
    skill_match = compute_skill_match_with_esco(combined_cv_text_for_skills, jd_text)

    # ── Title match ──────────────────────────────────────────────
    cv_title = jobs[0].get('title', '') if jobs else ''
    title_match = compute_title_similarity(cv_title, job_title if job_title else jd_text[:200])

    # ── Experience and education match ───────────────────────────
    exp_match = compute_experience_match(total_exp_years, jd_text)
    edu_match = compute_education_match(education_text, jd_text, best_gpa)

    if is_new_format:
        work_list = cv_document.get('work', [])
        projects_list = cv_document.get('projects', [])
        sections_for_boost = {
            'experience': ' '.join([
                ' '.join(filter(None, [w.get('summary', ''), ' '.join(w.get('highlights', []))]))
                for w in work_list
            ]),
            'skills': skills_text,
            'projects': ' '.join([
                ' '.join(filter(None, [p.get('description', ''), ' '.join(p.get('highlights', []))]))
                for p in projects_list
            ]),
        }
    else:
        sections_for_boost = cv_document.get("sections") or {}

    exp_match = compute_semantic_experience_boost(sections_for_boost, jd_text, exp_match)
    edu_match = compute_education_match(education_text, jd_text, best_gpa)

    # ── Location match ───────────────────────────────────────────
    if is_new_format:
        basics = cv_document.get('basics', {}) or {}
        cv_location = (basics.get('address') or '').strip()
        if cv_location and (len(cv_location) > 20 or any(c.isdigit() for c in cv_location)):
            matched = False
            for city in SL_CITIES:
                if city.lower() in cv_location.lower():
                    cv_location = f"{city}, Sri Lanka"
                    matched = True
                    break
            if not matched:
                cv_location = extract_city_from_address(cv_location)
        if not cv_location:
            cv_location = extract_location_from_cv(raw_text, {})
    else:
        sections = cv_document.get("sections", {})
        cv_location = extract_location_from_cv(
            raw_text, sections, basics=cv_document.get("basics", {})
        )

    jd_location_extracted = (
        extract_location_from_jd_enhanced(jd_text) if not jd_location else jd_location
    )

    logger.info(f"CV location: '{cv_location}' | JD location: '{jd_location_extracted}'")
    loc_match = await compute_location_match_with_geocoding(cv_location, jd_location_extracted)
    logger.info(f"Location match score: {loc_match}")

    overall_match = (skill_match + title_match + exp_match + edu_match + loc_match) / 5

    # ── Qualification flags ──────────────────────────────────────
    exp_matches = re.findall(r'(\d+)\+?\s*(?:to|-)\s*(\d+)?\s*years?', jd_text.lower())
    if exp_matches:
        jd_min = int(exp_matches[0][0])
        jd_max = int(exp_matches[0][1]) if exp_matches[0][1] else jd_min + 2
    else:
        jd_min, jd_max = 2, 5

    return {
        'skill_match_score': skill_match,
        'title_match_score': title_match,
        'exp_match_score': exp_match,
        'edu_match_score': float(edu_match),
        'location_match_score': loc_match,
        'overall_match_score': overall_match,

        'is_overqualified': 1 if total_exp_years > jd_max + 2 else 0,
        'is_underqualified': 1 if total_exp_years < jd_min - 0.5 else 0,

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
        'n_certifications': n_certifications,

        'is_remote_cv': 0.0,
        'is_remote_jd': 1.0 if 'remote' in jd_text.lower() else 0.0,
        'work_mode_mismatch': 0.0,

        'region': 'colombo_metro',
        'university_tier': 'other_state_university',
        'has_career_gap': 0.0,
        'career_gap_months': 0.0,
        'is_remote_preference': 0.0,
    }