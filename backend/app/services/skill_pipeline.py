
from typing import List, Dict
from app.services.article_fetcher import fetch_all_articles
from app.ml_models.skill_ner_loader import extract_skills
from app.ml_models.hybrid_extractor import hybrid_detect
import re

def normalize_skill(skill: str) -> str:
    """Normalize skill text for consistency"""
    skill = skill.lower().strip()
    skill = re.sub(r"\s+", " ", skill)
    return skill

def extract_skills_from_articles(
    topics: List[str],
    use_hybrid: bool = True
) -> List[str]:
    """
    Main skill extraction pipeline
    """

    # 1️⃣ Fetch articles
    articles = fetch_all_articles(topics, save_to_file=False)

    all_skills = set()

    # 2️⃣ Extract skills
    for art in articles:
        text = f"{art.get('title', '')}. {art.get('summary', '')}"

        if not text.strip():
            continue

        if use_hybrid:
            skills = hybrid_detect(text)
        else:
            skills = extract_skills(text)

        for skill in skills:
            norm = normalize_skill(skill)
            if len(norm) > 1:
                all_skills.add(norm)

    # 3️⃣ Return sorted list
    return sorted(all_skills)
