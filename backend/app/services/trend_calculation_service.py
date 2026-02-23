# backend/app/services/trend_calculation_service.py
from datetime import datetime
from app.models.hirebase_skill_stats_model import hirebase_skill_stats_collection
from app.models.google_trends_model import google_trends_collection
from app.models.skill_trend_model import skill_trend_collection
from app.utils.date_utils import current_week_id, current_month_id

MAX_WEEKS = 4

def get_previous_week_ids(week_id:str, num_weeks:int)-> list[str]:
    year, week = map(int, week_id.split("-W"))
    weeks = []
    for i in range(num_weeks):
        w = week - i
        y = year
        if w < 1:
            y -= 1
            w = 52 + w
        weeks.append(f"{y}-W{w:02d}")
    return weeks

def calculate_skill_trends():
    week_id = current_week_id()
    month_id = current_month_id()

    previous_weeks = get_previous_week_ids(week_id,MAX_WEEKS)

    # Get the weekly snapshot
    job_docs = list(hirebase_skill_stats_collection.find({"week_id":{"$in":previous_weeks}}))

    trend_docs = list(google_trends_collection.find({"week_id":{"$in":previous_weeks}}))

    if not job_docs or not trend_docs:
        return {"message": "Missing job or trend data"}
    
    job_map = {}
    
    for doc in job_docs:
        for skill,count in doc.get("skill_counts",{}).items():
            job_map[skill] = job_map.get(skill,0) + count

    trend_map = {}
    
    for doc in trend_docs:
        skill = doc.get("skill")
        score = doc.get("interest_score", 0)
        if skill:
            trend_map[skill] = trend_map.get(skill, 0) + score

    max_job = max(job_map.values(),default=1)
    max_trend = max(trend_map.values(),default=1)

    stored = []

    for skill in set(job_map.keys())| set(trend_map.keys()):
        job_count = job_map.get(skill,0)
        interest = trend_map.get(skill,0)

        # Normalise
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
