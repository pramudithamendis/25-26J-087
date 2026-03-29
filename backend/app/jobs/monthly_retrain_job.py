# backend/app/jobs/monthly_retrain_job.py

from app.services.monthly_retrain_service import monthly_retrain

def monthly_retrain_job():
    print("[JOB] Monthly retrain job started")
    model = monthly_retrain(forecast_weeks=12)
    if model:
        print("[JOB] Model retrained successfully")
    else:
        print("[JOB] Model retrain skipped or failed")