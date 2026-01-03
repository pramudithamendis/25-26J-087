from app.agents.trend_agent import trend_agent

def weekly_trend_job():
    print("[JOB] Weekly trend job started")
    trend_agent()
    print("[JOB] Weekly trend job finished")