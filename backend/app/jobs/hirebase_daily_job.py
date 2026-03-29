from app.services.hirebase_service import fetch_hirebase_jobs

def hirebase_daily_job():
    print("[JOB] Hirebase Daily Job started.")
    count = fetch_hirebase_jobs()
    count_display = count if isinstance(count, int) else (len(count) if count else 0)
    print(f"[JOB] Hirebase Daily Job completed. {count_display} jobs fetched.")