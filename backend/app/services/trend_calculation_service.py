# backend/app/services/trend_calculation_service.py
from datetime import datetime
from app.models.hirebase_skill_stats_model import hirebase_skill_stats_collection
from app.models.google_trends_model import google_trends_collection
from app.models.skill_trend_model import skill_trend_collection

def current_week_id():
    year, week, _ = datetime.utcnow().isocalendar()
    return f"{year}-W{week:02d}"

def current_month_id():
    return datetime.utcnow().strftime("%Y-%m")

def calculate_skill_trends():
    week_id = current_week_id()
    month_id = current_month_id()

    # Get the weekly snapshot
    job_doc = hirebase_skill_stats_collection.find_one({
        "source": "hirebase",
        "week_id": week_id,
        "month_id": month_id

    })

    trend_docs = list(google_trends_collection.find({"week_id":week_id, "month_id":month_id}))

    if not job_doc or not trend_docs:
        return {"message": "Missing job or trend data"}
    
    job_map = job_doc.get("skill_counts", {})

    trend_map = {d["skill"]:d["interest_score"] for d in trend_docs}

    max_job = max(job_map.values(),default=1)
    max_trend = max(trend_map.values(),default=1)

    stored = []

    for skill in set(job_map.keys())| set(trend_map.keys()):
        job_count = job_map.get(skill,0)
        interest = trend_map.get(skill,0)

        job_norm = job_count / max_job
        trend_norm = interest / max_trend

        trend_score = round((job_norm*0.5 + trend_norm*0.5),4)

        doc={
            "skill":skill,
            "week_id":week_id,
            "month_id":month_id,
            "job_count":job_count,
            "google_interest":interest,
            "trend_score":trend_score,
            "created_at":datetime.utcnow()
        }

        skill_trend_collection.update_one(
            {"skill":skill, "week_id":week_id, "month_id":month_id},
            {"$set":doc},
            upsert=True
        )

        stored.append(doc)

    return{
        "week_id":week_id,
        "month_id":month_id,
        "skills_processed":len(stored),
        "results":stored
    }
