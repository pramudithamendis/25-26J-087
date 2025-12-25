# trend_analyzer.py
import requests
from pytrends.request import TrendReq
from typing import List, Dict
import time


# Hirebase API settings

HIREBASE_API_KEY = "hb_58bd3e4a-e1f9-4db0-9ab0-d12858044fea"
HIREBASE_URL = "https://api.hirebase.org/v2/jobs/search"


# Pytrends setup

pytrends = TrendReq(hl='en-US', tz=360)


# Functions

def fetch_hirebase_jobs(
    job_titles: List[str] = None,
    limit: int = 50,
    page: int = 1
) -> List[Dict]:
    """
    Fetch job postings from Hirebase ONCE.
    """
    headers = {
        "Content-Type": "application/json",
        "x-api-key": HIREBASE_API_KEY
    }

    payload = {
        "job_titles": job_titles or ["Software Engineer"],
        "limit": limit,
        "page": page
    }

    r = requests.post(
        HIREBASE_URL,
        headers=headers,
        json=payload,
        timeout=10
    )
    r.raise_for_status()

    return r.json().get("jobs", [])

def count_skills_from_jobs(
    jobs: List[Dict],
    skills: List[str]
) -> Dict[str, int]:
    """
    Count how many job postings mention each skill.
    Each skill is counted at most once per job.
    """
    counts = {skill: 0 for skill in skills}

    for job in jobs:
        text = (
            f"{job.get('job_title', '')} "
            f"{job.get('description', '')}"
        ).lower()

        for skill in skills:
            if skill.lower() in text:
                counts[skill] += 1

    return counts



def google_trend_scores_batch(skills: List[str]) -> Dict[str, float]:
    """
    Fetch Google Trends scores for up to 5 skills at once.
    Returns dict: {skill: avg_trend_score}
    """
    scores = {}

    try:
        pytrends.build_payload(skills, timeframe="today 7-d")# For the last 12 months
        data = pytrends.interest_over_time()# Get interest over time

        # when 12 values data is Nan
        if data.empty:
            return {s: 0.0 for s in skills}

        # 12 values -> 1 value
        for skill in skills:
            scores[skill] = round(float(data[skill].mean()), 2)

    except Exception as e:
        print(f"[WARN] PyTrends batch failed {skills}: {e}")
        for skill in skills:
            scores[skill] = 0.0

    time.sleep(1)  # important: avoid rate limiting
    return scores


def analyze_trends(skills: List[str], batch_size: int = 5) -> List[Dict]:
    results = []

    # 1️⃣ Fetch jobs ONCE (fail-safe)
    try:
        jobs = fetch_hirebase_jobs(limit=50)
    except Exception as e:
        print(f"[ERROR] Failed to fetch Hirebase jobs: {e}")
        jobs = []

    for i in range(0, len(skills), batch_size):
        batch = skills[i:i + batch_size]

        # 2️⃣ Google Trends (batch-safe)
        try:
            google_scores = google_trend_scores_batch(batch)
        except Exception as e:
            print(f"[WARN] Google Trends batch failed {batch}: {e}")
            google_scores = {s: 0.0 for s in batch}

        # 3️⃣ Skill-by-skill processing (NO FAIL STOP)
        for skill in batch:

            # --- Hirebase (per skill, safe) ---
            try:
                h_count = count_skills_from_jobs(jobs, [skill]).get(skill, 0)
            except Exception as e:
                print(f"[WARN] Hirebase failed for skill '{skill}': {e}")
                h_count = 0

            # --- Google Trends (already safe) ---
            g_score = google_scores.get(skill, 0.0)

            combined = round(0.5 * h_count + 0.5 * g_score, 2)

            results.append({
                "skill": skill,
                "hirebase_count": h_count,
                "google_trend_score": g_score,
                "combined_score": combined
            })

    return sorted(results, key=lambda x: x["combined_score"], reverse=True)



