from datetime import datetime

def current_week_id() -> str:
    year, week, _ = datetime.utcnow().isocalendar()
    return f"{year}-W{week:02d}"

def current_month_id() -> str:
    return datetime.utcnow().strftime("%Y-%m")