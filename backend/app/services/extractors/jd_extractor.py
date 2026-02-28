import re
import logging
from typing import Dict, List, Optional
from app.config import settings

logger = logging.getLogger(__name__)

def extract_from_jd(jd_text: str, job_id: Optional[str] = None) -> Dict:
    """
    Extract structured data from job description text
    
    Uses LLM-based extraction by default, falls back to regex if OpenAI is unavailable.
    
    Args:
        jd_text: Full job description text
        job_id: Optional job ID for caching (ensures same job always extracts same skills)
    
    Returns:
        Dictionary with title, must_have, nice_to_have, min_years, jd_text
    """
    # Try LLM-based extraction first (if OpenAI is configured)
    if settings.OPENAI_API_KEY:
        try:
            from .jd_extractor_openai import extract_from_jd_openai
            logger.info("Using LLM-based JD extraction")
            return extract_from_jd_openai(jd_text, job_id=job_id)
        except Exception as e:
            logger.warning(f"LLM-based JD extraction failed: {str(e)}, falling back to regex")
    
    # Fallback to regex-based extraction
    logger.info("Using regex-based JD extraction (fallback)")
    
    # Fix common data issues
    jd_text = jd_text.strip()
    # Fix "ob Description" -> "Job Description"
    if jd_text.startswith("ob Description"):
        jd_text = "Job Description" + jd_text[14:]  # Replace "ob Description" with "Job Description"
    
    # Extract job title
    title = extract_title(jd_text)
    if title:
        logger.info(f"Extracted job title: {title}")
    else:
        logger.warning("Could not extract job title from JD")
    
    # Extract required/must-have skills
    must_have = extract_must_have_skills(jd_text)
    logger.info(f"Extracted {len(must_have)} must-have skills: {must_have[:5]}{'...' if len(must_have) > 5 else ''}")
    
    # Extract nice-to-have skills
    nice_to_have = extract_nice_to_have_skills(jd_text)
    logger.info(f"Extracted {len(nice_to_have)} nice-to-have skills")
    
    # Extract minimum years of experience
    min_years = extract_min_years(jd_text)
    if min_years > 0:
        logger.info(f"Extracted minimum years: {min_years}")
    
    return {
        "title": title,
        "must_have": must_have,
        "nice_to_have": nice_to_have,
        "min_years": min_years,
        "jd_text": jd_text  # Preserve original JD text for semantic analysis
    }

def extract_title(jd_text: str) -> str:
    """Extract job title from JD"""
    # Priority 1: Look for "looking for" patterns (most common)
    # Handle optional words like "passionate", "a", "an", etc.
    looking_for_patterns = [
        r'(?:looking\s+for|seeking|hiring)\s+(?:a\s+)?(?:passionate\s+)?(?:an?\s+)?((?:entry-level|junior|senior|mid-level|experienced)\s+[A-Z][A-Za-z\s&()]+(?:Engineer|Developer|Scientist|Analyst|Manager|Architect|Specialist|Consultant))',
        r'(?:looking\s+for|seeking|hiring)\s+(?:a\s+)?(?:passionate\s+)?(?:an?\s+)?([A-Z][A-Za-z\s&()]+(?:Engineer|Developer|Scientist|Analyst|Manager|Architect|Specialist|Consultant))',
    ]
    
    for pattern in looking_for_patterns:
        match = re.search(pattern, jd_text, re.IGNORECASE | re.MULTILINE)
        if match:
            title = match.group(1).strip()
            # Clean up title
            title = re.sub(r'\s+', ' ', title)
            # Remove common prefixes
            title = re.sub(r'^(?:an?\s+|the\s+)', '', title, flags=re.IGNORECASE)
            # Capitalize properly
            if title:
                # Capitalize first letter of each word, but preserve existing caps for acronyms
                words = title.split()
                # Handle special cases
                title_parts = []
                for word in words:
                    word_lower = word.lower()
                    # Handle common job title qualifiers
                    if word_lower in ['entry-level', 'entry', 'level', 'junior', 'senior', 'mid-level', 'experienced']:
                        if word_lower == 'entry-level':
                            title_parts.append('Entry-Level')
                        elif word_lower == 'mid-level':
                            title_parts.append('Mid-Level')
                        else:
                            title_parts.append(word.capitalize())
                    # Handle common tech acronyms
                    elif word_lower in ['devops', 'devsecops', 'aws', 'api', 'ui', 'ux']:
                        if word_lower == 'devops':
                            title_parts.append('DevOps')
                        elif word_lower == 'devsecops':
                            title_parts.append('DevSecOps')
                        else:
                            title_parts.append(word.upper())
                    # Preserve acronyms (all caps)
                    elif word.isupper():
                        title_parts.append(word)
                    # Regular word
                    else:
                        title_parts.append(word.capitalize())
                title = ' '.join(title_parts)
            
            # Handle parentheses in title (e.g., "Mobile Application Developer (Flutter)")
            if '(' in title and not title.endswith(')'):
                # Try to find the closing parenthesis
                paren_match = re.search(r'\([^)]*\)', title)
                if paren_match:
                    # Keep the parentheses content
                    pass
                else:
                    # Remove incomplete parentheses
                    title = re.sub(r'\([^)]*$', '', title).strip()
            
            if len(title) < 80 and len(title) > 3:  # Increased max length to handle longer titles
                return title
    
    # Priority 2: Look for explicit title markers
    explicit_patterns = [
        r'(?:Position|Role|Title|Job\s+Title)\s*:?\s*([A-Z][^\n]+)',
        r'#\s*([A-Z][^\n]+)',  # Markdown heading
    ]
    
    for pattern in explicit_patterns:
        match = re.search(pattern, jd_text, re.IGNORECASE | re.MULTILINE)
        if match:
            title = match.group(1).strip()
            # Clean up title
            title = re.sub(r'\s+', ' ', title)
            if len(title) < 60 and len(title) > 3:
                return title
    
    # Priority 3: Look for title at start of line (common format)
    start_patterns = [
        r'^([A-Z][A-Za-z\s&]+(?:Engineer|Developer|Scientist|Analyst|Manager|Architect))',
    ]
    
    for pattern in start_patterns:
        match = re.search(pattern, jd_text, re.MULTILINE)
        if match:
            title = match.group(1).strip()
            title = re.sub(r'\s+', ' ', title)
            if len(title) < 60 and len(title) > 3:
                return title
    
    # Fallback: first line if it looks like a title
    first_line = jd_text.split('\n')[0].strip()
    # Remove common prefixes
    first_line = re.sub(r'^(?:Job\s+Description|Position|Role)\s*[:\-]?\s*', '', first_line, flags=re.IGNORECASE)
    if len(first_line) < 60 and len(first_line) > 3 and not first_line.lower().startswith(('we are', 'looking for', 'our company')):
        return first_line
    
    return ""

def extract_must_have_skills(jd_text: str) -> List[str]:
    """Extract must-have/required skills"""
    skills = []
    
    # Look for "Required Skills", "Must have", "Essential" sections
    # Improved pattern to capture the actual skills section
    required_patterns = [
        r'(?:Required\s+Skills?\s*(?:&|and)?\s*Experience|Must\s+have|Essential|Mandatory|Prerequisites?)\s*:?\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*(?:Nice|Preferred|Bonus|Optional|What\s+We\s+Offer)|$)',
        r'Required\s+Skills?\s*(?:&|and)?\s*Experience\s*:?\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*(?:Nice|Preferred|Bonus|Optional|What\s+We\s+Offer)|$)',
        r'Requirements?[:\s]+([^\n]+(?:\n[^\n]+)*?)(?=\n\s*(?:Nice|Preferred|Bonus|Optional|What\s+We\s+Offer)|$)',
    ]
    
    for pattern in required_patterns:
        matches = re.finditer(pattern, jd_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        for match in matches:
            required_text = match.group(1)
            # Skip if it's just a section header
            if required_text.strip().lower() in ['skills & experience', 'skills and experience', 'skills', 'experience']:
                continue
            # Extract skills from this section
            extracted = extract_skills_from_text(required_text)
            if extracted:
                skills.extend(extracted)
    
    # If no specific section found, look for bullet points with required indicators
    if not skills:
        bullet_pattern = r'[•\-\*]\s*(?:Required|Must|Essential)[:\s]+([^\n]+)'
        matches = re.finditer(bullet_pattern, jd_text, re.IGNORECASE)
        for match in matches:
            extracted = extract_skills_from_text(match.group(1))
            if extracted:
                skills.extend(extracted)
    
    # Also extract technology names mentioned in the JD (common tech stack)
    tech_keywords = [
        # Cloud/DevOps
        'AWS', 'EC2', 'S3', 'Lambda', 'CloudFront', 'Route53', 'Route 53', 'IAM', 'VPC',
        'Docker', 'Kubernetes', 'Jenkins', 'CI/CD', 'CI/CD Pipelines', 'Git', 'Linux',
        'Terraform', 'Ansible', 'Chef', 'Puppet',
        'Azure', 'GCP', 'Google Cloud',
        # Backend
        'Python', 'Java', 'JavaScript', 'Node.js', 'React', 'Angular', 'Vue',
        'MongoDB', 'PostgreSQL', 'MySQL', 'Redis',
        # Mobile
        'Flutter', 'Dart', 'React Native', 'Android', 'iOS', 'Swift', 'Kotlin',
        'Firebase', 'REST API', 'REST APIs', 'RESTful', 'GraphQL', 'HTTP',
        'SQLite', 'Hive', 'Provider', 'Bloc', 'GetX', 'Riverpod',
        # Frontend
        'HTML', 'CSS', 'TypeScript', 'Webpack', 'npm'
    ]
    
    jd_lower = jd_text.lower()
    for tech in tech_keywords:
        if tech.lower() in jd_lower and tech not in skills:
            # Check if it's in the required section
            required_section = re.search(r'(?:Required|Must\s+have|Essential).*?(?:Nice|Preferred|What\s+We\s+Offer|$)', jd_text, re.IGNORECASE | re.DOTALL)
            if required_section:
                section_text = required_section.group(0).lower()
                if tech.lower() in section_text:
                    skills.append(tech)
    
    # Clean up skills - remove incomplete entries and duplicates
    cleaned_skills = []
    seen = set()
    for skill in skills:
        # Remove incomplete entries like "AWS core services (EC2"
        if '(' in skill and not skill.endswith(')'):
            # Try to extract the skill from parentheses
            match = re.search(r'\(([^)]+)\)', skill)
            if match:
                extracted = match.group(1).strip()
                if extracted and extracted not in seen:
                    cleaned_skills.append(extracted)
                    seen.add(extracted.lower())
            # Also try to get the part before the parenthesis
            before_paren = skill.split('(')[0].strip()
            if before_paren and before_paren.lower() not in seen:
                cleaned_skills.append(before_paren)
                seen.add(before_paren.lower())
        else:
            # Normalize skill name for duplicate detection
            skill_normalized = skill.strip()
            if skill_normalized and skill_normalized.lower() not in seen:
                cleaned_skills.append(skill_normalized)
                seen.add(skill_normalized.lower())
    
    return cleaned_skills

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
    
    # Skip section headers
    text_lower = text.lower().strip()
    if text_lower in ['skills & experience', 'skills and experience', 'skills', 'experience', 'required skills & experience']:
        return []
    
    # Split by common delimiters (including & for "Flutter & Dart")
    skill_items = re.split(r'[,;•\n&]', text)
    
    for item in skill_items:
        item = item.strip()
        # Skip empty items
        if not item:
            continue
        
        # Remove common prefixes
        item = re.sub(r'^(?:Experience\s+with|Knowledge\s+of|Proficient\s+in|Strong\s+(?:understanding|knowledge)\s+of|Familiarity\s+with|Practical\s+knowledge\s+of|Understanding\s+of)\s*', '', item, flags=re.IGNORECASE)
        item = item.strip()
        
        # Remove common suffixes
        item = re.sub(r'\s+(?:for|in|with|on|using|development|applications?).*$', '', item, flags=re.IGNORECASE)
        item = item.strip()
        
        # Filter out section headers and non-skill text
        if item.lower() in ['skills & experience', 'skills and experience', 'required skills', 'must have', 'required']:
            continue
        
        # Filter out very short or very long items
        if item and 2 < len(item) < 50:
            # Remove trailing punctuation
            item = re.sub(r'[.,;]+$', '', item)
            # Remove leading/trailing parentheses (but keep content inside)
            item = re.sub(r'^[\(\)]+|[\(\)]+$', '', item)
            item = item.strip()
            
            # Only add if it looks like a skill (not a full sentence)
            if item and not item.endswith('.') and len(item.split()) < 8:
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

