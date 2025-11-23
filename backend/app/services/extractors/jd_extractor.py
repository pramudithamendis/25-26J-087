import re
from typing import Dict, List

def extract_from_jd(jd_text: str) -> Dict:
    """
    Extract structured data from job description text
    
    Args:
        jd_text: Full job description text
    
    Returns:
        Dictionary with title, must_have, nice_to_have, min_years
    """
    jd_text = jd_text.strip()
    
    # Extract job title
    title = extract_title(jd_text)
    
    # Extract required/must-have skills
    must_have = extract_must_have_skills(jd_text)
    
    # Extract nice-to-have skills
    nice_to_have = extract_nice_to_have_skills(jd_text)
    
    # Extract minimum years of experience
    min_years = extract_min_years(jd_text)
    
    return {
        "title": title,
        "must_have": must_have,
        "nice_to_have": nice_to_have,
        "min_years": min_years
    }

def extract_title(jd_text: str) -> str:
    """Extract job title from JD"""
    # Common patterns for job titles
    title_patterns = [
        r'(?:Position|Role|Title|Job)\s*:?\s*([A-Z][^\n]+)',
        r'^([A-Z][A-Za-z\s&]+(?:Engineer|Developer|Scientist|Analyst|Manager|Architect))',
        r'#\s*([A-Z][^\n]+)',  # Markdown heading
    ]
    
    for pattern in title_patterns:
        match = re.search(pattern, jd_text, re.IGNORECASE | re.MULTILINE)
        if match:
            title = match.group(1).strip()
            # Clean up title
            title = re.sub(r'\s+', ' ', title)
            if len(title) < 50:  # Reasonable title length
                return title
    
    # Fallback: first line if it looks like a title
    first_line = jd_text.split('\n')[0].strip()
    if len(first_line) < 50 and not first_line.lower().startswith(('we are', 'looking for', 'our company')):
        return first_line
    
    return ""

def extract_must_have_skills(jd_text: str) -> List[str]:
    """Extract must-have/required skills"""
    skills = []
    
    # Look for "Required", "Must have", "Essential" sections
    required_patterns = [
        r'(?:Required|Must\s+have|Essential|Mandatory|Prerequisites?)\s*:?\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*(?:Nice|Preferred|Bonus|Optional)|$)',
        r'Requirements?[:\s]+([^\n]+(?:\n[^\n]+)*?)(?=\n\s*(?:Nice|Preferred|Bonus|Optional)|$)',
    ]
    
    for pattern in required_patterns:
        matches = re.finditer(pattern, jd_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        for match in matches:
            required_text = match.group(1)
            # Extract skills from this section
            skills.extend(extract_skills_from_text(required_text))
    
    # If no specific section found, look for bullet points with required indicators
    if not skills:
        bullet_pattern = r'[•\-\*]\s*(?:Required|Must|Essential)[:\s]+([^\n]+)'
        matches = re.finditer(bullet_pattern, jd_text, re.IGNORECASE)
        for match in matches:
            skills.extend(extract_skills_from_text(match.group(1)))
    
    return list(set(skills))  # Remove duplicates

def extract_nice_to_have_skills(jd_text: str) -> List[str]:
    """Extract nice-to-have/preferred skills"""
    skills = []
    
    # Look for "Nice to have", "Preferred", "Bonus" sections
    preferred_patterns = [
        r'(?:Nice\s+to\s+have|Preferred|Bonus|Optional|Plus)\s*:?\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*[A-Z]|$)',
    ]
    
    for pattern in preferred_patterns:
        matches = re.finditer(pattern, jd_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        for match in matches:
            preferred_text = match.group(1)
            skills.extend(extract_skills_from_text(preferred_text))
    
    return list(set(skills))  # Remove duplicates

def extract_skills_from_text(text: str) -> List[str]:
    """Extract individual skills from a text block"""
    skills = []
    
    # Split by common delimiters
    skill_items = re.split(r'[,;•\n]', text)
    
    for item in skill_items:
        item = item.strip()
        # Remove common prefixes
        item = re.sub(r'^(?:Experience\s+with|Knowledge\s+of|Proficient\s+in|Strong\s+)\s*', '', item, flags=re.IGNORECASE)
        item = item.strip()
        
        # Filter out very short or very long items
        if item and 2 < len(item) < 50:
            # Remove trailing punctuation
            item = re.sub(r'[.,;]+$', '', item)
            if item:
                skills.append(item)
    
    return skills

def extract_min_years(jd_text: str) -> int:
    """Extract minimum years of experience required"""
    # Patterns for years of experience
    year_patterns = [
        r'(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)',
        r'(?:minimum|min|at\s+least)\s+(\d+)\s*(?:years?|yrs?)',
        r'(\d+)-(\d+)\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)',
    ]
    
    for pattern in year_patterns:
        match = re.search(pattern, jd_text, re.IGNORECASE)
        if match:
            # Get the first number (minimum)
            years = int(match.group(1))
            return years
    
    # Default to 0 if not specified
    return 0

