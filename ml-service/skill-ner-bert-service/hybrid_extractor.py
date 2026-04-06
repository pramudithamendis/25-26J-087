# backend/app/ml_models/hybrid_extractor.py
import re
from typing import List, Set

# Import your BERT skill extractor
from loader import extract_skills


# Regex patterns (lightweight)

REGEX_PATTERNS = [
    r"(\b[\w\s\+\#]{2,}\b)\s+programming\s+language",
    r"experience\s+with\s+([\w\s\+\#]{2,})",
    r"proficient\s+in\s+(\b[\w\+\#\.]{2,}\b)",
    r"knowledge\s+of\s+(\b[\w\+\#\.]{2,}\b)",
    r"built\s+with\s+(\b[\w\+\#\.]{2,}\b)",
    r"using\s+(\b[\w\+\#\.]{2,}\b)",
    r"(\b[\w\+\#\.]{2,}\b)\s+framework",
]

STOPWORDS = {
    "a","an","the","and","or","but","if","while","with","for","to","of","in","on",
    "is","are","was","were","be","been","being",
    "this","that","these","those",
    "it","its","as","by","from",
    "using","used","use",
    "experience","knowledge","skill","skills",
    "system","application","software","tool","tools",
    "their","our","your","we","they","you"
}


# Hybrid skill detector

def hybrid_detect(text: str) -> List[str]:
    """
    Input:
        text (str): title + summary / resume text

    Output:
        List[str]: detected skills (normalized, unique)
    """

    if not text or not text.strip():
        return []

    detected_skills: Set[str] = set()


    # 1️⃣ BERT NER MODEL (primary, learned from data)
    
    try:
        bert_skills = extract_skills(text)
        for skill in bert_skills:
            detected_skills.add(skill)
    except Exception as e:
        # Model failure should NEVER crash API
        print(f"[WARN] Skill NER failed: {e}")

    
    # 2️⃣ Regex fallback (precision boost)
    
    for pattern in REGEX_PATTERNS:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        for match in matches:
            skill = match[0] if isinstance(match, tuple) else match
            skill = skill.strip().lower()
            if skill not in STOPWORDS and len(skill) > 1:
                detected_skills.add(skill)

    return sorted(detected_skills)
