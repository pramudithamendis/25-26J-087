# backend/app/services/forecast_dataset_service.py
import pandas as pd
from datetime import datetime
from app.models.skill_trend_model import skill_trend_collection
from app.models.article_model import articles_collection
from app.utils.date_utils import current_week_id, current_month_id
from pytrends.request import TrendReq
import time
from pymongo import DESCENDING

pytrends = TrendReq(hl='en-US', tz=360)

def clean_skill_name(skill):
    return "".join(char for char in skill if char.isprintable()).strip()

def get_article_skills():
    """Get all unique skills from articles."""
    week_id = current_week_id()
    month_id = current_month_id()
    kw_list = {
        s.lower().strip()
        for a in articles_collection.find({"week_id": week_id, "month_id": month_id})
        for s in a.get("skills", [])
    }
    return list(kw_list)

def fetch_cold_start_data(month_limit: int = 3, batch_size: int = 5):
    """Fetch Google Trends data and save to skill_trend_collection consistently."""
    
    raw_skills = get_article_skills()
    if not raw_skills:
        print("[WARN] No article skills found.")
        return []

    skills = [clean_skill_name(s) for s in raw_skills if s]
    print(f"[INFO] Total skills after cleaning: {len(skills)}")

    # Find max google_interest from last N months for normalization
    recent_records = list(skill_trend_collection.find()
                          .sort("google_interest", -1)
                          .limit(100))  # adjust limit if needed
    max_google = max((r.get("google_interest", 0) for r in recent_records), default=1)

    stored = []

    for i in range(0, len(skills), batch_size):
        batch = skills[i:i + batch_size]
        print(f"\n[DEBUG] Processing batch {i//batch_size + 1}: {batch}")

        try:
            pytrends.build_payload(
                kw_list=batch,
                timeframe=f"today {month_limit}-m",
                geo=""
            )
            data = pytrends.interest_over_time()
            if data.empty:
                print(f"[WARN] No Google Trends data found for batch: {batch}")
                continue

            weekly_df = data.resample('W').mean()

            for date, row in weekly_df.iterrows():
                year = date.year
                week_num = date.isocalendar()[1]
                week_id = f"{year}-W{week_num:02d}"
                month_id = date.strftime("%Y-%m")

                for skill in batch:
                    google_interest = int(row.get(skill, 0)) # TODO: make this google interest per week
                    
                    # Normalized trend score (job_count=0 for cold start)
                    trend_score = round((google_interest / max_google) * 0.5, 4)

                    doc = {
                        "month_id": month_id,
                        "week_id": week_id,
                        "skill": skill,
                        "google_interest": google_interest,
                        "job_count": 0,
                        "trend_score": trend_score,
                        "created_at": datetime.utcnow()
                    }

                    skill_trend_collection.update_one(
                        {"skill": skill, "week_id": week_id, "month_id": month_id},
                        {"$set": doc},
                        upsert=True
                    )
                    stored.append(doc)

        except Exception as e:
            print(f"[ERROR] Failed for batch {batch}: {e}")
            continue

        # Reduce 429 risk
        time.sleep(5)

    print(f"[INFO] Saved {len(stored)} cold-start records to skill_trend_collection.")
    return stored

def build_forecast_dataset(weeks_limit: int = 12):
    # 1. Get distinct week_ids sorted descending
    week_ids = skill_trend_collection.distinct("week_id")
    week_ids = sorted(week_ids, reverse=True)[:weeks_limit]  # last N weeks

    # Trigger cold-start if weeks < weeks_limit
    if len(week_ids) < weeks_limit:
        print(f"[INFO] Only {len(week_ids)} weeks found, fetching cold-start data...")
        fetch_cold_start_data()
        week_ids = skill_trend_collection.distinct("week_id")
        week_ids = sorted(week_ids, reverse=True)

    week_ids = week_ids[:weeks_limit]  # last N weeks

    dataset = []

    # 2. Fetch all skill records for each week
    for week_id in reversed(week_ids):  # chronological order
        records = list(skill_trend_collection.find({"week_id": week_id}))
        max_job = max((r.get("job_count", 0) for r in records), default=1)
        max_google = max((r.get("google_interest", 0) for r in records), default=1)

        for r in records:
            job_count = r.get("job_count", 0)
            google_interest = r.get("google_interest", 0)

            job_norm = job_count / max_job if max_job > 0 else 0
            trend_norm = google_interest / max_google if max_google > 0 else 0
            trend_value = round((job_norm * 0.5 + trend_norm * 0.5), 4)

            dataset.append({
                "ds": r.get("week_id"),
                "skill": r.get("skill"),
                "job_count": job_count,
                "google_interest": google_interest,
                "y": trend_value
            })

    import pandas as pd
    return pd.DataFrame(dataset)