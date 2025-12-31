# /backend/app/services/google_trends_service.py

from pytrends.request import TrendReq
from datetime import datetime
from typing import List
from app.models.google_trends_model import google_trends_collection
from app.models.article_model import articles_collection

pytrends = TrendReq(hl='en-US', tz=0)

def current_week_id() -> str:
    year, week, _ = datetime.utcnow().isocalendar()
    return f"{year}-W{week:02d}"

def current_month_id() -> str:
    return datetime.utcnow().strftime("%Y-%m")

import time

def fetch_google_trends():
    """
    Fetch weekly Google Trends interest for skills in batches of 5 per request,
    with a small delay between batches to avoid rate limits.
    """
    week_id = current_week_id()
    month_id = current_month_id()

    # Get skills from this week's articles
    skills = list({
        s.lower().strip()
        for a in articles_collection.find({"week_id": week_id, "month_id": month_id})
        for s in a.get("skills", [])
    })

    if not skills:
        return {"message": "No skills found for the current week/month."}

    batch_size = 5
    stored = []

    # Process skills in batches
    for i in range(0, len(skills), batch_size):
        batch = skills[i:i+batch_size]

        try:
            pytrends.build_payload(
                kw_list=batch,
                timeframe='now 7-d',
                geo=""
            )

            df = pytrends.interest_over_time()

            for skill in batch:
                if skill in df.columns:
                    interest = int(df[skill].mean())
                else:
                    interest = 0

                doc = {
                    "skill": skill,
                    "week_id": week_id,
                    "month_id": month_id,
                    "interest_score": interest,
                    "source": "google_trends",
                    "created_at": datetime.utcnow()
                }

                google_trends_collection.update_one(
                    {"skill": skill, "week_id": week_id},
                    {"$set": doc},
                    upsert=True
                )

                stored.append(doc)

        except Exception as e:
            print(f"[WARN] Google Trends fetch failed for batch {batch}: {e}")

        # Small delay to respect Google Trends limits
        time.sleep(1.5)  # 1.5 seconds between batches

    return {
        "week_id": week_id,
        "skills_processed": len(stored),
        "results": stored
    }
