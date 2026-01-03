from apscheduler.schedulers.background import BackgroundScheduler
from app.jobs.hirebase_daily_job import hirebase_daily_job
from app.jobs.weekly_trend_job import weekly_trend_job

scheduler = BackgroundScheduler()

def start_scheduler():
    if scheduler.running:
        return
    print("[SCHEDULER] Starting background jobs...")
    
    scheduler.add_job(
        hirebase_daily_job,
        trigger = "cron",
        hour = 1,
        id = "hirebase_daily",
        replace_existing = True
    )

    scheduler.add_job(
        weekly_trend_job,
        trigger = "cron",
        day_of_week = "sun",
        hour = "2",
        id = "weekly_trend",
        replace_existing = True
    )

    scheduler.start()
    print("[SCHEDULER] Jobs scheduled ")