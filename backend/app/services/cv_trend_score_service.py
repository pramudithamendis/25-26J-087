# backend/app/services/cv_trend_score_service.py
from datetime import datetime
from app.models.cv_model import cv_collection
from app.models.skill_trend_model import skill_trend_collection
from app.models.cv_trend_score_model import cv_trend_scores_collection
from app.utils.date_utils import current_week_id
from app.services.monthly_retrain_service import predict_future_skills
from app.models.application_model import applications_collection
from app.models.user_model import users_collection
from bson import ObjectId
import re

# ------------------------------
# Text normalization & skill matching
# ------------------------------
def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s+.#-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_matching_skills_from_text(cv_text: str, trending_skills: list[str]) -> list[str]:
    normalized_cv_words = set(normalize_text(cv_text).split())
    matched = []
    for skill in trending_skills:
        skill_words = set(normalize_text(skill).split())
        if skill_words <= normalized_cv_words:  # all words in CV must exist
            matched.append(skill)
    return matched

# ------------------------------
# CV Trend Score Calculation
# ------------------------------
def calculate_single_cv_trend_score(cv_id: str) -> dict:
    week_id = current_week_id()
    cv = cv_collection.find_one({"_id": ObjectId(cv_id)})
    if not cv:
        raise ValueError(f"CV not found: {cv_id}")

    trend_docs = list(skill_trend_collection.find({"week_id": week_id}))
    trend_map = {d["skill"]: d for d in trend_docs}  # full doc to get forecast

    # Extract keywords from CV
    skills_list = cv.get("skills", [])
    keywords = []
    for skill_item in skills_list:
        if isinstance(skill_item, dict):
            skill_keywords = skill_item.get("keywords", [])
            if isinstance(skill_keywords, list):
                keywords.extend(skill_keywords)
    cv_text = " ".join(keywords)

    # Match trending skills
    matched_skills = extract_matching_skills_from_text(cv_text, [d["skill"] for d in trend_docs])

    # Calculate combined score per skill
    matched = []
    for s in matched_skills:
        skill_doc = trend_map[s]
        trend_score = skill_doc.get("trend_score", 0)
        forecast_score = skill_doc.get("forecast_score", 0) or predict_future_skills(
            s, skill_doc.get("job_count", 0), skill_doc.get("google_interest", 0)
        ) or 0.0
        combined_score = round(0.7 * trend_score + 0.3 * forecast_score, 4)
        matched.append({
            "skill": s,
            "trend_score": trend_score,
            "forecast_score": forecast_score,
            "combined_score": combined_score
        })

    # Final CV trend score = average of combined scores
    cv_score = round(sum([m["combined_score"] for m in matched]) / len(matched), 4) if matched else 0.0

    doc = {
        "cv_id": cv["_id"],
        "week_id": week_id,
        "cv_trend_score": cv_score,
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
    trend_map = {d["skill"]: d for d in trend_docs}

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
        cv_text = " ".join(keywords)

        matched_skills = extract_matching_skills_from_text(cv_text, [d["skill"] for d in trend_docs])

        matched = []
        for s in matched_skills:
            skill_doc = trend_map[s]
            trend_score = skill_doc.get("trend_score", 0)
            forecast_score = skill_doc.get("forecast_score", 0) or predict_future_skills(
                s, skill_doc.get("job_count", 0), skill_doc.get("google_interest", 0)
            ) or 0.0
            combined_score = round(0.7 * trend_score + 0.3 * forecast_score, 4)
            matched.append({
                "skill": s,
                "trend_score": trend_score,
                "forecast_score": forecast_score,
                "combined_score": combined_score
            })

        cv_score = round(sum([m["combined_score"] for m in matched]) / len(matched), 4) if matched else 0.0

        doc = {
            "cv_id": cv["_id"],
            "week_id": week_id,
            "cv_trend_score": cv_score,
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

    return {
        "week_id": week_id,
        "resumes_processed": len(results),
        "cv_processed": [serialize_doc(d) for d in results],
    }

# ------------------------------
# Helper to serialize ObjectId and datetime
# ------------------------------
def serialize_doc(doc):
    return {
        "cv_id": str(doc["cv_id"]),
        "week_id": doc["week_id"],
        "skills_matched": doc["skills_matched"],
        "cv_trend_score": doc["cv_trend_score"],
        "email": doc["email"],
        "created_at": doc["created_at"].isoformat() if isinstance(doc["created_at"], datetime) else doc["created_at"]
    }

def get_job_applicants_scores(job_id: str, week_id: str):
    # 1. Fetch applications for the job
    applications = list(applications_collection.find({"job_id": job_id}))
    if not applications:
        return {
            "week_id": week_id,
            "job_id": job_id,
            "average_score": 0.0,
            "applicant_count": 0,
            "scores": []
        }

    # 2. Extract user_ids and map them to applications
    user_ids = [ObjectId(app["user_id"]) for app in applications if "user_id" in app]
    applicant_count = len(user_ids)

    # 3. Fetch user emails from users_collection
    users = list(users_collection.find({"_id": {"$in": user_ids}}, {"email": 1}))
    user_email_map = {str(u["_id"]): u["email"] for u in users if "email" in u}

    # 4. Fetch trend scores for these emails for the given week
    emails = list(user_email_map.values())
    cv_scores_docs = list(cv_trend_scores_collection.find({
        "email": {"$in": emails},
        "week_id": week_id
    }))

    # 5. Create a map of email -> score
    # Note: If multiple scores exist for an email in a week, we take the latest by created_at
    email_score_map = {}
    for doc in sorted(cv_scores_docs, key=lambda x: x.get("created_at", datetime.min)):
        email_score_map[doc["email"]] = {
            "cv_id": str(doc["cv_id"]),
            "cv_trend_score": doc.get("cv_trend_score", 0.0)
        }

    # 6. Build the final scores list based on applications
    scores_list = []
    numeric_scores = []
    for app in applications:
        u_id = str(app["user_id"])
        email = user_email_map.get(u_id)
        if email and email in email_score_map:
            score_data = email_score_map[email]
            scores_list.append(score_data)
            numeric_scores.append(score_data["cv_trend_score"])

    avg_score = round(sum(numeric_scores) / len(numeric_scores), 4) if numeric_scores else 0.0

    return {
        "week_id": week_id,
        "job_id": job_id,
        "average_score": avg_score,
        "applicant_count": applicant_count,
        "scores": scores_list
    }