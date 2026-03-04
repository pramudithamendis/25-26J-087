# backend/app/services/cv_trend_score_service.py
from datetime import datetime
from app.models.cv_model import cv_collection
from app.models.skill_trend_model import skill_trend_collection
from app.models.cv_trend_score_model import cv_trend_scores_collection
from app.utils.date_utils import current_week_id
from bson import ObjectId
import re

def normalize_text(text: str) -> str:
    # Accept non-string inputs gracefully
    if not isinstance(text, str):
        if text is None:
            return ""
        text = str(text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s+.#-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_matching_skills_from_text(
    cv_text: str,
    trending_skills: list[str]
) -> list[str]:
    if not cv_text:
        return []

    normalized_cv = normalize_text(cv_text)

    matched = []
    for skill in trending_skills:
        skill_norm = normalize_text(skill)
        if skill_norm in normalized_cv:
            matched.append(skill)

    return list(set(matched))


def calculate_single_cv_trend_score(cv_id: str) -> dict:
    """Calculate trend score for a single CV by its ID."""
    week_id = current_week_id()

    cv = cv_collection.find_one({"_id": ObjectId(cv_id)})
    if not cv:
        raise ValueError(f"CV not found: {cv_id}")

    trend_docs = list(skill_trend_collection.find({"week_id": week_id}))
    trend_map = {d["skill"]: d["trend_score"] for d in trend_docs}
    skills_list = cv.get("skills", [])
    keywords = []

    for skill_item in skills_list:
        if isinstance(skill_item, dict):
            skill_keywords = skill_item.get("keywords", [])
            if isinstance(skill_keywords, list):
                keywords.extend(skill_keywords)

    print(f"[DEBUG] Extracted Keywords for {cv_id}: {keywords}")
    cv_text = " ".join(keywords)

    matched_skills = extract_matching_skills_from_text(
        cv_text,
        [d["skill"] for d in trend_docs]
    )
    print(f"[DEBUG] Matched Skills for {cv_id}: {matched_skills}")

    matched = [{"skill": s, "score": trend_map[s]} for s in matched_skills]

    if not matched:
        score = 0.0
    else:
        score = round(sum([s["score"] for s in matched]) / len(matched), 4)

    doc = {
        "cv_id": cv["_id"],
        "week_id": week_id,
        "cv_trend_score": score,
        "skills_matched": matched,
        "email": cv.get("user_email", ""),
        "created_at": datetime.utcnow(),
    }

    cv_trend_scores_collection.update_one(
        {"cv_id": cv["_id"], "week_id": week_id},
        {"$set": doc},
        upsert=True,
    )

    return serialize_doc(doc)


def calculate_all_cv_trend_score() -> dict:
    week_id = current_week_id()

    trend_docs = list(skill_trend_collection.find({"week_id": week_id}))
    trend_map = {d["skill"]: d["trend_score"] for d in trend_docs}

    cvs = cv_collection.find({})
    
    results = []

    for cv in cvs:
        skills_list = cv.get("skills", [])
        keywords = []

        for skill_item in skills_list:
            if isinstance(skill_item, dict):
                skill_keywords = skill_item.get("keywords", [])
                if isinstance(skill_keywords, list):
                    keywords.extend(skill_keywords)

        print(f"[DEBUG] Extracted Keywords for CV {cv.get('_id')}: {keywords}")
        cv_text = " ".join(keywords)

        # pass only skill names (strings) to the extractor
        matched_skills = extract_matching_skills_from_text(
            cv_text,
            [d["skill"] for d in trend_docs]
        )
        print(f"[DEBUG] Matched Skills for CV {cv.get('_id')}: {matched_skills}")

        matched = [{"skill": s, "score": trend_map[s]} for s in matched_skills]

        if not matched:
            score = 0.0
        else:
            score = round(sum([s["score"] for s in matched]) / len(matched),4)

        doc = {
            "cv_id": cv["_id"],
            "week_id": week_id,
            "cv_trend_score": score,
            "skills_matched": matched,
            "email": cv.get("user_email", ""),
            "created_at": datetime.utcnow(),
        }


        cv_trend_scores_collection.update_one(
            {"cv_id": cv["_id"], "week_id": week_id},
            {"$set": doc},
            upsert=True,
        )

        results.append(doc)

    serialized_results = [serialize_doc(doc) for doc in results]
    return{
        "week_id": week_id,
        "resumes_processed": len(results),
        "cv_processed": serialized_results,
    }


# Private helper functions

def serialize_doc(doc):
    return {
        "cv_id": str(doc["cv_id"]),  # convert ObjectId to string
        "week_id": doc["week_id"],
        "skills_matched": doc["skills_matched"],
        "cv_trend_score": doc["cv_trend_score"],
        "email": doc["email"],
        "created_at": doc["created_at"].isoformat() if isinstance(doc["created_at"], datetime) else doc["created_at"]
    }

    

