# backend/app/services/cv_trend_score_service.py
from datetime import datetime
from app.models.cv_model import cv_collection
from app.models.skill_trend_model import skill_trend_collection
from app.models.cv_trend_score_model import cv_trend_scores_collection
from app.utils.date_utils import current_month_id, current_week_id
import re

def extract_skills_from_section(skills_text: str) -> list[str]:
    if not skills_text:
        return []

    # lowercase + split
    tokens = re.split(r"[•,\n|:]", skills_text.lower())
    return [t.strip() for t in tokens if len(t.strip()) > 2]


def calculate_all_cv_trend_score() -> float:
    week_id = current_week_id()
    month_id = current_month_id()

    trend_docs = list(skill_trend_collection.find({"week_id": week_id, "month_id": month_id}))
    trend_map = {d["skill"]: d["trend_score"] for d in trend_docs}

    cvs = cv_collection.find({})

    results = []

    for cv in cvs:
        skill_text = cv.get("sections", {}).get("skills", "")
        skills = extract_skills_from_section(skill_text)

        matched = [
            trend_map[s] for s in skills if s in trend_map
        ]

        if not matched:
            score = 0.0
        else:
            score = round(sum(matched) / len(matched),4)

        doc = {
            "cv_id": cv["_id"],
            "candidate_id": cv.get("candidate_id"),
            "week_id": week_id,
            "month_id": month_id,
            "cv_trend_score": score,
            "total_matched_skills": len(matched),
            "created_at": datetime.utcnow(),
        }

        cv_trend_scores_collection.update_one(
            {"cv_id": cv["_id"], "week_id": week_id, "month_id": month_id},
            {"$set": doc},
            upsert=True,
        )

        results.append(doc)

    return{
        "week_id": week_id,
        "cv_processed": len(results),
    }
    

