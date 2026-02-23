# backend/app/services/hirebase_skill_count_service.py

from typing import Dict
from collections import defaultdict
from datetime import datetime
from app.models.hirebase_job_model import hirebase_jobs_collection
from app.models.hirebase_skill_stats_model import hirebase_skill_stats_collection
from app.utils.date_utils import current_week_id, current_month_id

def count_hirebase_skills()-> Dict:
    """
    Count how many job postings mention each skill.
    Each job contributes at most 1 count per skill.
    Also stores a weekly snapshot in `hirebase_skill_stats_collection`.
    """
    week_id = current_week_id()
    month_id = current_month_id()

    # Fetch jobs for the current week/month
    jobs = hirebase_jobs_collection.find({
        "week_id": week_id,
        "month_id": month_id
    })

    skill_counts = defaultdict(int)
    total_jobs = 0

    for job in jobs:
        total_jobs += 1

        # Merge all skill sources
        raw_skills = set()

        for field in ["skills","technologies"]:
            for s in job.get(field, []):
                if isinstance(s, str):
                    raw_skills.add(s.lower().strip())

        # Count each skill ONCE per job
        for skill in raw_skills:
            skill_counts[skill] += 1

    # Prepare snapshot
    snapshot = {
       "sourece":"hirebase",
       "week_id": week_id,
       "month_id": month_id,
       "total_jobs": total_jobs,
       "skill_counts": dict(skill_counts),
       "created_at": datetime.utcnow()
    }

    # Upsert the snapshot to avoid duplicates for the same week
    hirebase_skill_stats_collection.update_one(
        {"source": "hirebase", "week_id": week_id, "month_id": month_id},
        {"$set": snapshot},
        upsert=True
    )

    return snapshot