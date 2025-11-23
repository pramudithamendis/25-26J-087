from .cv_extractor import extract_from_cv, extract_skills, extract_experience, extract_education
import re
from typing import Dict, List

def extract_from_linkedin(preprocessed_linkedin: Dict) -> Dict:
    """
    Extract structured data from preprocessed LinkedIn PDF
    
    Similar to CV extractor but also extracts certifications and endorsements
    
    Args:
        preprocessed_linkedin: Dictionary with full_text and sections
    
    Returns:
        Dictionary with skills_raw, experience, education, certifications, endorsements
    """
    # Use CV extractor for basic fields
    base_data = extract_from_cv(preprocessed_linkedin)
    
    sections = preprocessed_linkedin.get("sections", {})
    full_text = preprocessed_linkedin.get("full_text", "")
    
    # Extract additional LinkedIn-specific fields
    certifications = extract_certifications(sections, full_text)
    endorsements = extract_endorsements(sections, full_text)
    
    return {
        **base_data,
        "certifications": certifications,
        "endorsements": endorsements
    }

def extract_certifications(sections: Dict, full_text: str) -> List[str]:
    """Extract certifications from LinkedIn profile"""
    certifications = []
    
    # Look for certifications section
    cert_section = sections.get("certifications", "")
    if not cert_section:
        # Try to find in other sections or full text
        cert_patterns = [
            r'(?:Certification|Certificate|Certified)\s*:?\s*([^\n]+)',
            r'([A-Z][^•\n]+?)\s*[-–—]\s*(?:Issued|Certified|Valid)',
        ]
        for pattern in cert_patterns:
            matches = re.finditer(pattern, full_text, re.IGNORECASE)
            for match in matches:
                cert = match.group(1).strip()
                if cert and len(cert) > 5:
                    certifications.append(cert)
    else:
        # Parse certifications from section
        cert_lines = re.split(r'[•\n]', cert_section)
        for line in cert_lines:
            cert = line.strip()
            if cert and len(cert) > 5:
                certifications.append(cert)
    
    return list(set(certifications))  # Remove duplicates

def extract_endorsements(sections: Dict, full_text: str) -> List[str]:
    """Extract skill endorsements from LinkedIn profile"""
    endorsements = []
    
    # LinkedIn endorsements are often listed as skills with numbers
    # Pattern: "Java (15)" or "Spring Boot - 20 endorsements"
    endorsement_patterns = [
        r'([A-Z][A-Za-z\s+]+?)\s*\((\d+)\)',
        r'([A-Z][A-Za-z\s+]+?)\s*[-–—]\s*(\d+)\s*(?:endorsement|people)',
    ]
    
    for pattern in endorsement_patterns:
        matches = re.finditer(pattern, full_text, re.IGNORECASE)
        for match in matches:
            skill = match.group(1).strip()
            count = match.group(2)
            if skill and int(count) > 0:
                endorsements.append(skill)
    
    # Also check skills section for endorsed skills
    skills_section = sections.get("skills", "")
    if skills_section:
        # Look for skills with endorsement indicators
        skill_lines = re.split(r'[,;•\n]', skills_section)
        for line in skill_lines:
            # Remove endorsement counts if present
            skill = re.sub(r'\s*\([^)]*\)\s*$', '', line).strip()
            if skill and len(skill) > 1:
                endorsements.append(skill)
    
    return list(set(endorsements))  # Remove duplicates

