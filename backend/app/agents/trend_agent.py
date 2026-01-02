# backend/app/agents/trend_agent.py
from datetime import datetime
from app.services.article_service import fetch_weekly_articles
from app.services.skill_extraction_service import extract_skills_from_articles
from app.services.trend_calculation_service import calculate_skill_trends
from app.services.cv_trend_score_service import calculate_all_cv_trend_score
from app.utils.date_utils import current_week_id

def trend_agent():
    """
    Weekly autonomous intelligence agent
    """
    week_id = current_week_id()
    print(f"[AGENT] Running trend agent for week {week_id}")

    articles = fetch_weekly_articles()
    if not articles:
        print("[AGENT] No articles found. Skipping")
        return

    skills = extract_skills_from_articles()
    if not skills:
        print("[AGENT] No skills extracted. Skipping")
        return
    
    calculate_skill_trends()
    print("[AGENT] Skill trends calculated")

    results = calculate_all_cv_trend_score()
    print(f"[AGENT] CV trend scores updated: {len(results)}")
