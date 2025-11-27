import pdfplumber
import re
from typing import Dict, Optional

def preprocess_pdf(file_path: str) -> Dict:
    """
    Extract and preprocess text from PDF file
    
    Args:
        file_path: Path to PDF file
    
    Returns:
        Dictionary with full_text and sections (skills, experience, education, projects)
    """
    try:
        full_text = ""
        
        # Extract text from PDF using pdfplumber
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
        
        # Clean text
        full_text = clean_text(full_text)
        
        # Detect sections
        sections = detect_sections(full_text)
        
        return {
            "full_text": full_text,
            "sections": sections
        }
    
    except Exception as e:
        # Return empty structure if PDF processing fails
        return {
            "full_text": "",
            "sections": {
                "skills": "",
                "experience": "",
                "education": "",
                "projects": ""
            },
            "error": str(e)
        }

def clean_text(text: str) -> str:
    """
    Clean extracted text: remove extra whitespace, fix line breaks
    
    Args:
        text: Raw extracted text
    
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Replace multiple whitespaces with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Fix common line break issues (preserve intentional line breaks)
    text = re.sub(r'([a-z])\s+([A-Z])', r'\1 \2', text)
    
    # Remove excessive newlines
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text

def detect_sections(text: str) -> Dict[str, str]:
    """
    Detect and extract sections from CV text
    
    Looks for common section headings: Skills, Experience, Education, Projects
    
    Args:
        text: Full text of the CV
    
    Returns:
        Dictionary with section names as keys and section content as values
    """
    sections = {
        "skills": "",
        "experience": "",
        "education": "",
        "projects": ""
    }
    
    # Common section heading patterns (case-insensitive)
    section_patterns = {
        "skills": r"(?:^|\n)\s*(?:technical\s+)?skills?\s*:?\s*(?:\n|$)",
        "experience": r"(?:^|\n)\s*(?:work\s+)?experience\s*:?\s*(?:\n|$)",
        "education": r"(?:^|\n)\s*education\s*:?\s*(?:\n|$)",
        "projects": r"(?:^|\n)\s*(?:projects?|portfolio)\s*:?\s*(?:\n|$)"
    }
    
    # Find all section positions
    section_positions = []
    for section_name, pattern in section_patterns.items():
        matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
        for match in matches:
            section_positions.append({
                "name": section_name,
                "start": match.end(),
                "priority": list(section_patterns.keys()).index(section_name)
            })
    
    # Sort by position in text
    section_positions.sort(key=lambda x: x["start"])
    
    # Extract content for each section
    for i, pos in enumerate(section_positions):
        section_name = pos["name"]
        
        # Find end position (next section or end of text)
        if i + 1 < len(section_positions):
            end_pos = section_positions[i + 1]["start"]
        else:
            end_pos = len(text)
        
        # Extract section content
        section_content = text[pos["start"]:end_pos].strip()
        
        # Only update if this section is empty or if this match is more specific
        if not sections[section_name] or len(section_content) > len(sections[section_name]):
            sections[section_name] = section_content
    
    # If no sections found, try alternative approach: split by common delimiters
    if not any(sections.values()):
        # Try to find sections by looking for ALL CAPS headings
        caps_pattern = r'(?:^|\n)([A-Z][A-Z\s&]+?)(?:\n|:)'
        caps_matches = list(re.finditer(caps_pattern, text))
        
        for i, match in enumerate(caps_matches):
            heading = match.group(1).strip().lower()
            start_pos = match.end()
            end_pos = caps_matches[i + 1].start() if i + 1 < len(caps_matches) else len(text)
            content = text[start_pos:end_pos].strip()
            
            # Map common headings to our sections
            if 'skill' in heading and not sections["skills"]:
                sections["skills"] = content
            elif 'experience' in heading or 'employment' in heading or 'work' in heading:
                if not sections["experience"] or len(content) > len(sections["experience"]):
                    sections["experience"] = content
            elif 'education' in heading or 'degree' in heading:
                if not sections["education"] or len(content) > len(sections["education"]):
                    sections["education"] = content
            elif 'project' in heading or 'portfolio' in heading:
                if not sections["projects"] or len(content) > len(sections["projects"]):
                    sections["projects"] = content
    
    return sections

