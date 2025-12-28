# app/services/skill_extraction_service.py

from typing import Dict, Set
from app.models.article_model import articles_collection
from app.ml_models.hybrid_extractor import hybrid_detect

def extract_skills_from_articles() -> Dict:
    """
    Extract skills from unprocessed articles in MongoDB.
    Marks articles as processed and saves extracted skills.
    Returns processed article count and unique skills.
    """

    processed_articles = 0
    all_skills: Set[str] = set()

    # Fetch articles that haven't been processed yet
    unprocessed_articles = articles_collection.find({"processed": {"$ne": True}})

    for article in unprocessed_articles:
        text_to_analyze = f"{article.get('title', '')} {article.get('full_text', '')}"

        # Run hybrid skill extraction
        try:
            skills = hybrid_detect(text_to_analyze)
        except Exception as e:
            print(f"[WARN] Skill extraction failed for article {article['_id']}: {e}")
            continue

        # Update article in MongoDB
        articles_collection.update_one(
            {"_id": article["_id"]},
            {"$set": {"skills": skills, "processed": True}}
        )

        all_skills.update(skills)
        processed_articles += 1

    return {
        "processed_articles": processed_articles,
        "unique_skills": sorted(all_skills)
    }
