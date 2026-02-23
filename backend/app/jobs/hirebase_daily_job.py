from app.services.hirebase_service import fetch_hirebase_jobs

def hirebase_daily_job():
    print("[JOB] Hirebase Daily Job started.")
    count = fetch_hirebase_jobs()
    print(f"[JOB] Hirebase Daily Job completed. {len(count)} jobs fetched.")