from typing import Dict
from app.config import settings
import logging
import json
from openai import OpenAI

logger = logging.getLogger(__name__)

_openai_client = None

def get_openai_client():
    """Get or create OpenAI client"""
    global _openai_client
    if _openai_client is None and settings.OPENAI_API_KEY:
        try:
            _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("OpenAI client initialized for LinkedIn extraction")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    return _openai_client

def extract_from_linkedin_openai(preprocessed_linkedin: Dict) -> Dict:
    """
    Extract structured data from LinkedIn PDF using OpenAI
    
    Uses OpenAI to intelligently parse LinkedIn profile text and extract structured information
    
    Args:
        preprocessed_linkedin: Dictionary with full_text and sections
    
    Returns:
        Dictionary with skills_raw, experience, education, certifications, endorsements
    """
    full_text = preprocessed_linkedin.get("full_text", "")
    
    if not full_text:
        logger.warning("No text found in LinkedIn PDF")
        return {
            "skills_raw": [],
            "experience": [],
            "education": [],
            "certifications": [],
            "endorsements": [],
            "summary": "",
            "publications": [],
            "projects": []
        }
    
    if not settings.OPENAI_API_KEY:
        logger.warning("OpenAI API key not configured, falling back to regex extraction")
        from .linkedin_extractor import extract_from_linkedin
        return extract_from_linkedin(preprocessed_linkedin)
    
    try:
        client = get_openai_client()
        if not client:
            from .linkedin_extractor import extract_from_linkedin
            return extract_from_linkedin(preprocessed_linkedin)
        
        # Truncate if too long (keep first 12000 chars for context)
        linkedin_text = full_text[:12000] if len(full_text) > 12000 else full_text
        
        prompt = f"""Extract structured information from this LinkedIn profile/resume text. Parse it EXTREMELY carefully and extract ALL information with 100% accuracy.

LINKEDIN TEXT:
{linkedin_text}

CRITICAL EXTRACTION RULES:

1. SKILLS: Extract ONLY skills that are explicitly listed in a "Skills", "Top Skills", or similar section. Do NOT infer or add skills from other sections. Return as a list of individual skill strings.

2. EXPERIENCE: Extract ALL work experience entries. CRITICAL RULES:
   - If someone has MULTIPLE roles at the same company, you MUST extract EACH role as a SEPARATE entry
   - Example: If the text shows "Decryptogen" with "Software Engineer (Jan 2025 - Present)" AND "Associate Full Stack Developer (Apr 2024 - Jan 2025)", create TWO separate entries
   - title: Job title/position (exact as written, no modifications)
   - company: Company name (exact as written in the experience section, NO additions like "Publications", "Ltd", "LLC" unless they are actually part of the company name in the text)
   - start: Start date in YYYY-MM format
   - end: End date in YYYY-MM format or "Present" if current job
   - location: Location (city, state/province, country) if mentioned
   - highlights: List of ACTUAL job responsibilities, duties, achievements, or bullet points that describe what the person DID in that role. 
     * DO NOT include: certifications, publications, projects, skills, or any information not directly related to job duties
     * ONLY include: actual work responsibilities, achievements, tasks performed, technologies used in that role
     * If no clear job responsibilities are listed, use empty array []

3. EDUCATION: Extract all education entries. For each entry, provide:
   - institution: School/University name (exact as written)
   - degree: Degree name (e.g., "Bachelor's degree", "BSc", "BTech")
   - field: Field of study/specialization if mentioned
   - start: Start date in YYYY-MM format
   - end: End date in YYYY-MM format or "Present" if ongoing
   - location: Location if mentioned

4. CERTIFICATIONS: Extract ALL certifications, licenses, or professional credentials mentioned. Include ALL instances even if the same certification appears multiple times in the document.

5. PUBLICATIONS: Extract all publications, research papers, articles, or academic works mentioned. These are typically listed in a "Publications" section or similar.

6. PROJECTS: Extract all projects mentioned if there is a dedicated projects section.

7. SUMMARY: Extract the summary/about section if present (usually at the top of the profile).

8. ENDORSEMENTS: Extract skill endorsements if mentioned (skills with endorsement counts or mentions).

Return the response in this EXACT JSON format (no markdown, no code blocks):
{{
  "skills_raw": ["skill1", "skill2", ...],
  "experience": [
    {{
      "title": "Job Title",
      "company": "Company Name",
      "start": "2024-01",
      "end": "2024-12",
      "location": "City, State, Country",
      "highlights": ["Actual job responsibility 1", "Actual job responsibility 2"]
    }}
  ],
  "education": [
    {{
      "institution": "University Name",
      "degree": "Degree Name",
      "field": "Field of Study",
      "start": "2021-02",
      "end": "2024-11",
      "location": "City, Country"
    }}
  ],
  "certifications": ["Certification 1", "Certification 2", ...],
  "publications": ["Publication 1", "Publication 2", ...],
  "projects": ["Project 1", "Project 2", ...],
  "summary": "Summary text if present",
  "endorsements": ["Skill 1", "Skill 2", ...]
}}

ABSOLUTE REQUIREMENTS:
- Extract EVERY experience entry, even if multiple roles at the same company - create separate entries for each role
- Company names must be EXACTLY as written - if it says "Ovinway", use "Ovinway" NOT "Ovinway Publications"
- Highlights must ONLY contain actual job responsibilities - NO certifications, NO publications, NO projects
- If you see publications or projects in the experience section, extract them to the publications/projects arrays, NOT in highlights
- Extract ALL certifications mentioned anywhere in the document
- Extract publications if mentioned
- Extract projects if mentioned
- Be 100% accurate - extract exactly what is written, do not infer, do not add, do not modify
"""

        logger.info("Calling OpenAI for LinkedIn extraction...")
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at parsing LinkedIn profiles and resumes. Always extract accurate, structured information and return ONLY valid JSON, no markdown formatting."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,  # Low temperature for consistent extraction
            response_format={"type": "json_object"},
            max_tokens=4000
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()
        
        result = json.loads(result_text)
        
        # Validate and clean the result
        skills_raw = result.get("skills_raw", [])
        experience = result.get("experience", [])
        education = result.get("education", [])
        certifications = result.get("certifications", [])
        endorsements = result.get("endorsements", [])
        summary = result.get("summary", "")
        publications = result.get("publications", [])
        projects = result.get("projects", [])
        
        # Clean skills: remove empty strings, deduplicate
        skills_raw = [s.strip() for s in skills_raw if s and s.strip()]
        skills_raw = list(dict.fromkeys(skills_raw))
        
        # Validate experience entries and filter highlights
        validated_experience = []
        for exp in experience:
            if isinstance(exp, dict) and exp.get("title") and exp.get("company"):
                # Filter highlights to remove certifications, publications, and projects
                raw_highlights = exp.get("highlights", []) if isinstance(exp.get("highlights"), list) else []
                filtered_highlights = []
                
                # Keywords that indicate non-job-responsibility content
                exclude_keywords = ["certified", "certification", "publication", "published", "paper", "article", "research"]
                
                for highlight in raw_highlights:
                    if isinstance(highlight, str):
                        highlight_lower = highlight.lower()
                        # Check if highlight is actually a job responsibility
                        # Exclude if it contains certification/publication keywords or matches known patterns
                        is_certification = any(keyword in highlight_lower for keyword in exclude_keywords)
                        is_publication = ":" in highlight and len(highlight) > 50  # Publications often have colons and long titles
                        
                        # Only include if it looks like an actual job responsibility
                        if not is_certification and not is_publication:
                            # Check if it's a meaningful job responsibility (not too short, not a title)
                            if len(highlight.strip()) > 10 and not highlight.strip().endswith("Tool"):
                                filtered_highlights.append(highlight.strip())
                
                validated_experience.append({
                    "title": exp.get("title", "").strip(),
                    "company": exp.get("company", "").strip(),
                    "start": exp.get("start", "").strip(),
                    "end": exp.get("end", "").strip(),
                    "location": exp.get("location", "").strip(),
                    "highlights": filtered_highlights
                })
        
        # Validate education entries - convert to string format for compatibility
        validated_education = []
        for edu in education:
            if isinstance(edu, dict) and edu.get("institution"):
                parts = []
                if edu.get("degree"):
                    parts.append(edu["degree"])
                if edu.get("field"):
                    parts.append(edu["field"])
                if edu.get("institution"):
                    parts.append(edu["institution"])
                
                edu_str = ", ".join(parts)
                
                if edu.get("start") or edu.get("end"):
                    start = edu.get("start", "")
                    end = edu.get("end", "Present")
                    edu_str += f" ({start} - {end})"
                
                validated_education.append(edu_str)
        
        # Clean certifications and endorsements
        certifications = [c.strip() for c in certifications if c and c.strip()]
        endorsements = [e.strip() for e in endorsements if e and e.strip()]
        
        # Clean publications and projects
        publications = [p.strip() for p in publications if p and p.strip()]
        projects = [p.strip() for p in projects if p and p.strip()]
        
        # Clean summary
        summary = summary.strip() if summary else ""
        
        logger.info(f"OpenAI LinkedIn extraction successful: {len(skills_raw)} skills, {len(validated_experience)} experiences, {len(validated_education)} education entries, {len(certifications)} certifications, {len(publications)} publications")
        
        return {
            "skills_raw": skills_raw,
            "experience": validated_experience,
            "education": validated_education,
            "certifications": certifications,
            "endorsements": endorsements,
            "summary": summary,
            "publications": publications,
            "projects": projects
        }
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from OpenAI response: {str(e)}")
        # Fallback to regex extraction
        from .linkedin_extractor import extract_from_linkedin
        return extract_from_linkedin(preprocessed_linkedin)
    except Exception as e:
        logger.error(f"OpenAI LinkedIn extraction error: {str(e)}, falling back to regex")
        # Fallback to regex extraction
        from .linkedin_extractor import extract_from_linkedin
        return extract_from_linkedin(preprocessed_linkedin)

