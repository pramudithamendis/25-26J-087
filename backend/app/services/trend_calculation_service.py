# backend/app/services/trend_calculation_service.py

from datetime import datetime

from sklearn.preprocessing import normalize
from app.models.hirebase_skill_stats_model import hirebase_skill_stats_collection
from app.models.google_trends_model import google_trends_collection
from app.services.monthly_retrain_service import predict_future_skills
from app.models.skill_trend_model import skill_trend_collection
from app.utils.date_utils import current_week_id, current_month_id

MAX_WEEKS = 4


def get_previous_week_ids(week_id: str, num_weeks: int) -> list[str]:
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

def safe_min_max(values: dict):
    if not values:
        return 0.0, 1.0
    vmin = min(values.values())
    vmax = max(values.values())
    if vmin == vmax:
        return vmin, vmin + 1  # avoid division by zero
    return vmin, vmax

def normalize(x, xmin, xmax):
    return (x - xmin) / (xmax - xmin)


# =========================================================
# MAIN TREND CALCULATION
# =========================================================
def calculate_skill_trends():
    week_id = current_week_id()
    month_id = current_month_id()

    previous_weeks = get_previous_week_ids(week_id, MAX_WEEKS)

    # Fetch 4 weeks job count
    job_docs = list(
        hirebase_skill_stats_collection.find({"week_id": {"$in": previous_weeks}})
    )

    # Fetch 4 weeks google interest 
    trend_docs = list(
        google_trends_collection.find({"week_id": {"$in": previous_weeks}})
    )

    # Error handling 
    if not job_docs or not trend_docs:
        return {"message": "Missing job or trend data"}
    
    # Create week index map for easy access
    week_index_map = {week: idx for idx, week in enumerate(previous_weeks)}

    # =====================================================
    # JOB AGGREGATION
    # =====================================================
    job_map = {}

    # Add job counts from previous 4 weeks
    for doc in job_docs:
        week_id_doc = doc.get("week_id")
        if week_id_doc not in week_index_map:
            continue  # skip if week_id is not in the expected list

        idx = week_index_map[week_id_doc]
        
        for item in doc.get("skills", []):
            skill = item.get("skill")
            count = item.get("count", 0)

            if not skill:
                continue

            if skill not in job_map:
                job_map[skill] = [0] * MAX_WEEKS  # initialize with zeros

            job_map[skill][idx] = count  # place count in correct week index

    # get the rolling avg
    job_avg_map = {
        skill: sum(values) / MAX_WEEKS
        for skill, values in job_map.items()
        if values
    }
 
    # =====================================================
    # TREND AGGREGATION (list-based)
    # =====================================================
    trend_map = {}

    # Add google interest from previous 4 weeks
    for doc in trend_docs:
        week_id_doc = doc.get("week_id")
        if week_id_doc not in week_index_map:
            continue  # skip if week_id is not in the expected list

        idx = week_index_map[week_id_doc]

        skill = doc.get("skill")
        score = (
            doc.get("interest_score")
            or doc.get("interest")
            or doc.get("score")
            or 0
        )

        if not skill:
            continue

        if skill not in trend_map:
            trend_map[skill] = [0] * MAX_WEEKS  # initialize with zeros

        trend_map[skill][idx] = score  # place score in correct week index


    # get the rolling avg
    trend_avg_map = {
        skill: sum(values) / MAX_WEEKS
        for skill, values in trend_map.items()
        if values
    }

    # Safe normalization denominators
    J_min, J_max = safe_min_max(job_avg_map)
    G_min, G_max = safe_min_max(trend_avg_map)

 
    stored = []
    # get the full skill list from both ways 
    all_skills = set(job_avg_map.keys()) | set(trend_avg_map.keys())

    # =====================================================
    # FINAL SCORING LOOP
    # =====================================================
    for skill in all_skills:

        job_count = job_avg_map.get(skill)
        interest = trend_avg_map.get(skill)

        # Forecast (safe fallback)
        forecast_score = predict_future_skills(skill, job_count, interest)

        if forecast_score is None:
            forecast_score = 0.0


        # Normalize safely
        job_norm = normalize(job_count, J_min, J_max) if job_count is not None else 0.0
        trend_norm = normalize(interest, G_min, G_max) if interest is not None else 0.0

        # Final score 
        trend_score = round((job_norm * 0.5 + trend_norm * 0.5), 4)

        doc = {
            "skill": skill,
            "week_id": week_id,
            "month_id": month_id,
            "job_count": job_count,
            "google_interest": interest,
            "trend_score": trend_score,
            "forecast_score": forecast_score,
            "created_at": datetime.utcnow()
        }

        skill_trend_collection.update_one(
            {"skill": skill, "week_id": week_id},
            {"$set": doc},
            upsert=True
        )

        stored.append(doc)

    return {
        "week_id": week_id,
        "month_id": month_id,
        "skills_processed": len(stored),
        "results": stored
    }


# =========================================================
# SKILL HISTORY
# =========================================================
def get_skill_history(skill: str, num_weeks: int = 8):

    latest_doc = skill_trend_collection.find_one(
        {},
        sort=[("week_id", -1)]
    )

    week_id = latest_doc["week_id"] if latest_doc else current_week_id()

    prev_weeks = get_previous_week_ids(week_id, num_weeks)

    docs = list(
        skill_trend_collection.find(
            {
                "skill": skill,
                "week_id": {"$in": prev_weeks}
            },
            {
                "_id": 0,
                "week_id": 1,
                "trend_score": 1,
                "job_count": 1,
                "google_interest": 1,
                "forecast_score": 1
            }
        ).sort("week_id", 1)
    )

    return {
        "skill": skill,
        "history": docs
    }


# =========================================================
# TOP SKILLS + HISTORY
# =========================================================
def get_top_skills_history(limit: int = 10, num_weeks: int = 8):

    latest_doc = skill_trend_collection.find_one(
        {},
        sort=[("week_id", -1)]
    )

    week_id = latest_doc["week_id"] if latest_doc else current_week_id()

    prev_weeks = get_previous_week_ids(week_id, num_weeks)

    # Top skills this week
    top = list(
        skill_trend_collection.find(
            {"week_id": week_id},
            {
                "_id": 0,
                "skill": 1,
                "trend_score": 1,
                "job_count": 1,
                "google_interest": 1,
                "forecast_score": 1
            }
        ).sort("trend_score", -1).limit(limit)
    )

    skill_names = [d["skill"] for d in top]

    # History for those skills
    history = list(
        skill_trend_collection.find(
            {
                "skill": {"$in": skill_names},
                "week_id": {"$in": prev_weeks}
            },
            {
                "_id": 0,
                "skill": 1,
                "week_id": 1,
                "trend_score": 1,
                "job_count": 1,
                "google_interest": 1,
                "forecast_score": 1
            }
        ).sort("week_id", 1)
    )

    return {
        "week_id": week_id,
        "top_skills": top,
        "history": history
    }