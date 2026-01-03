# backend/app/services/hirebase_service.py
import requests
from datetime import datetime
from typing import List, Dict
from app.models.hirebase_job_model import hirebase_jobs_collection
import json
from pathlib import Path
from app.config import settings
from app.utils.date_utils import current_week_id, current_month_id  

HIREBASE_API_KEY = settings.HIREBASE_API_KEY
HIREBASE_URL = "https://api.hirebase.org/v2/jobs/search"

JOB_TITLES_FILE = Path("app/data/job_titles.json")

def load_job_titles() -> list[str]:
    with open(JOB_TITLES_FILE, "r") as f:
        return json.load(f)["job_titles"]
    
def fetch_hirebase_jobs(
    limit: int = 10,
    page: int = 1
) -> List[Dict]:
    headers = {
        "Content-Type": "application/json",
        "x-api-key": HIREBASE_API_KEY
    }

    job_titles = load_job_titles()

    payload = {
        "job_titles": job_titles,
        "limit": limit,
        "page": page
    }

    response = requests.post(
        HIREBASE_URL,
        headers=headers,
        json=payload,
        timeout=10
    )
    response.raise_for_status()

    jobs = response.json().get("jobs", [])
    today = datetime.utcnow().date().isoformat()

    stored_jobs = []

    for job in jobs:
        job_doc = {
            "job_id": job.get("_id"),
            "job_title": job.get("job_title"),
            "company_name": job.get("company_name"),
            "description": job.get("description", ""),
            "skills": job.get("skills", []),
            "technologies": job.get("technologies", []),
            "source": "hirebase",

            "fetch_date": today,
            "week_id": current_week_id(),
            "month_id": current_month_id(),
            
            "processed": False
        }

        # Avoid duplicates (important for free tier)
        hirebase_jobs_collection.update_one(
            {"job_id": job_doc["job_id"]},
            {"$setOnInsert": job_doc},
            upsert=True
        )

        stored_jobs.append(job_doc)

    return stored_jobs
