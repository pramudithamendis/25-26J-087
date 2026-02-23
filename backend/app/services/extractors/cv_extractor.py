import re
from typing import Dict, List

def extract_from_cv(preprocessed_cv: Dict) -> Dict:
    """
    Extract structured data from preprocessed CV
    
    Args:
        preprocessed_cv: Dictionary with full_text and sections
    
    Returns:
        Dictionary with skills_raw, experience, education, github_handle
    """
    sections = preprocessed_cv.get("sections", {})
    full_text = preprocessed_cv.get("full_text", "")
    
    # Extract skills
    skills_raw = extract_skills(sections.get("skills", ""), full_text)
    
    # Extract experience
    experience = extract_experience(sections.get("experience", ""), full_text)
    
    # Extract education
    education = extract_education(sections.get("education", ""), full_text)
    
    # Extract GitHub handle
    github_handle = extract_github_handle(full_text)
    
    return {
        "skills_raw": skills_raw,
        "experience": experience,
        "education": education,
        "github_handle": github_handle
    }

def extract_skills(skills_section: str, full_text: str) -> List[str]:
    """Extract skills from skills section"""
    skills = []
    
    if skills_section:
        # Split by common delimiters
        skill_lines = re.split(r'[,;•\n]', skills_section)
        for line in skill_lines:
            skill = line.strip()
            if skill and len(skill) > 1:
                skills.append(skill)
    
    # If no skills section, try to extract from full text
    if not skills and full_text:
        # Look for common skill patterns
        skill_patterns = [
            r'(?:Proficient|Experienced|Skilled|Expert)\s+in\s+([A-Za-z\s+]+)',
            r'(?:Technologies?|Skills?|Tools?):\s*([^\n]+)',
        ]
        for pattern in skill_patterns:
            matches = re.finditer(pattern, full_text, re.IGNORECASE)
            for match in matches:
                skills_text = match.group(1)
                skills.extend([s.strip() for s in re.split(r'[,;]', skills_text) if s.strip()])
    
    return list(set(skills))  # Remove duplicates

def extract_experience(experience_section: str, full_text: str) -> List[Dict]:
    """Extract work experience from experience section"""
    experience = []
    
    text_to_parse = experience_section if experience_section else full_text
    
    if not text_to_parse:
        return experience
    
    # Pattern for job entries: Title at Company (Date range)
    # Example: "Backend Developer at ABC Corp (Jan 2021 - Mar 2023)"
    job_pattern = r'([A-Z][^•\n]+?)\s+(?:at|@)\s+([A-Z][^•\n]+?)\s*\(([^)]+)\)'
    matches = re.finditer(job_pattern, text_to_parse, re.IGNORECASE | re.MULTILINE)
    
    for match in matches:
        title = match.group(1).strip()
        company = match.group(2).strip()
        date_range = match.group(3).strip()
        
        # Parse dates
        start_date, end_date = parse_date_range(date_range)
        
        # Find highlights/bullet points for this position
        highlights = extract_highlights(text_to_parse, match.start(), match.end())
        
        experience.append({
            "title": title,
            "company": company,
            "start": start_date,
            "end": end_date,
            "highlights": highlights
        })
    
    # Alternative pattern: if no matches, try simpler format
    if not experience:
        # Look for lines with dates and job titles
        lines = text_to_parse.split('\n')
        current_job = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line contains a date pattern
            date_match = re.search(r'(\d{4}|\w+\s+\d{4})', line)
            if date_match:
                # Try to extract title and company
                parts = re.split(r'[-–—]', line)
                if len(parts) >= 2:
                    title_company = parts[0].strip()
                    date_part = parts[-1].strip()
                    
                    # Try to split title and company
                    if ' at ' in title_company or ' @ ' in title_company:
                        title, company = re.split(r'\s+(?:at|@)\s+', title_company, 1, re.IGNORECASE)
                    else:
                        title = title_company
                        company = ""
                    
                    start_date, end_date = parse_date_range(date_part)
                    
                    experience.append({
                        "title": title,
                        "company": company,
                        "start": start_date,
                        "end": end_date,
                        "highlights": []
                    })
    
    return experience

def extract_highlights(text: str, start_pos: int, end_pos: int) -> List[str]:
    """Extract bullet points/highlights for a job position"""
    highlights = []
    
    # Look for bullet points after the job entry
    context = text[max(0, start_pos):min(len(text), end_pos + 500)]
    
    # Common bullet point patterns
    bullet_patterns = [
        r'[•\-\*]\s*([^\n•\-\*]+)',
        r'^\s*[-•]\s*(.+)',
    ]
    
    for pattern in bullet_patterns:
        matches = re.finditer(pattern, context, re.MULTILINE)
        for match in matches:
            highlight = match.group(1).strip()
            if highlight and len(highlight) > 10:  # Filter out very short items
                highlights.append(highlight)
    
    return highlights[:5]  # Limit to 5 highlights

def extract_education(education_section: str, full_text: str) -> List[str]:
    """Extract education information"""
    education = []
    
    text_to_parse = education_section if education_section else full_text
    
    if not text_to_parse:
        return education
    
    # Pattern for degrees: "BSc Computer Science, University Name (2020)"
    degree_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+([^,\n(]+)(?:,\s*([^,\n(]+))?(?:\s*\((\d{4})\))?'
    matches = re.finditer(degree_pattern, text_to_parse)
    
    for match in matches:
        degree_type = match.group(1).strip()
        field = match.group(2).strip()
        institution = match.group(3).strip() if match.group(3) else ""
        year = match.group(4) if match.group(4) else ""
        
        edu_str = f"{degree_type} {field}"
        if institution:
            edu_str += f", {institution}"
        if year:
            edu_str += f" ({year})"
        
        education.append(edu_str)
    
    # If no structured matches, return simple lines from education section
    if not education and education_section:
        lines = [line.strip() for line in education_section.split('\n') if line.strip()]
        education = lines[:3]  # Limit to 3 entries
    
    return education

def parse_date_range(date_str: str) -> tuple:
    """
    Parse date range string to ISO format dates
    
    Args:
        date_str: Date range like "Jan 2021 - Mar 2023" or "2021-2023"
    
    Returns:
        Tuple of (start_date, end_date) in YYYY-MM format
    """
    months = {
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
        'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
        'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
    }
    
    # Pattern: "Jan 2021 - Mar 2023" or "2021 - 2023"
    date_str = date_str.lower().strip()
    
    # Try to split by dash
    parts = re.split(r'\s*[-–—]\s*', date_str)
    
    start_date = None
    end_date = None
    
    if len(parts) >= 2:
        start_str = parts[0].strip()
        end_str = parts[1].strip()
        
        # Parse start date
        start_date = parse_single_date(start_str, months)
        
        # Parse end date (or "Present")
        if 'present' in end_str or 'current' in end_str:
            from datetime import datetime
            end_date = datetime.now().strftime("%Y-%m")
        else:
            end_date = parse_single_date(end_str, months)
    elif len(parts) == 1:
        # Single date
        start_date = parse_single_date(parts[0], months)
    
    return (start_date or "", end_date or "")

def parse_single_date(date_str: str, months: Dict) -> str:
    """Parse a single date string to YYYY-MM format"""
    date_str = date_str.strip().lower()
    
    # Pattern: "Jan 2021" or "2021"
    month_match = re.match(r'([a-z]+)\s+(\d{4})', date_str)
    if month_match:
        month_name = month_match.group(1)[:3]  # First 3 letters
        year = month_match.group(2)
        month = months.get(month_name, "01")
        return f"{year}-{month}"
    
    # Pattern: just year "2021"
    year_match = re.match(r'(\d{4})', date_str)
    if year_match:
        return f"{year_match.group(1)}-01"
    
    return ""

def extract_github_handle(full_text: str) -> str:
    """Extract GitHub handle from CV text"""
    if not full_text:
        return ""
    
    # Pattern 1: github.com/username or github.com/username/
    github_url_pattern = r'github\.com[/:]([a-zA-Z0-9]([a-zA-Z0-9]|-(?![.-])){0,38})'
    match = re.search(github_url_pattern, full_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Pattern 2: @username (if near GitHub context)
    at_pattern = r'(?:github|git)[\s:]*@([a-zA-Z0-9]([a-zA-Z0-9]|-(?![.-])){0,38})'
    match = re.search(at_pattern, full_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Pattern 3: "GitHub: username" or "GitHub username"
    explicit_pattern = r'github[\s:]+([a-zA-Z0-9]([a-zA-Z0-9]|-(?![.-])){0,38})'
    match = re.search(explicit_pattern, full_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    return ""

def extract_handle_from_url(github_url: str) -> str:
    """
    Extract GitHub handle from GitHub URL.
    
    Args:
        github_url: GitHub URL (e.g., "https://github.com/username" or "github.com/username")
    
    Returns:
        GitHub handle/username or empty string
    """
    if not github_url or not github_url.strip():
        return ""
    
    github_url = github_url.strip()
    
    # Pattern: github.com/username or github.com/username/
    # Handles: https://github.com/username, http://github.com/username, github.com/username, www.github.com/username
    github_url_pattern = r'github\.com[/:]([a-zA-Z0-9]([a-zA-Z0-9]|-(?![.-])){0,38})'
    match = re.search(github_url_pattern, github_url, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    return ""

