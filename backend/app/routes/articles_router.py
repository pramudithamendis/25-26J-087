from fastapi import APIRouter, Depends
from app.schemas.article_schema import ArticleFetchRequest
from app.services.article_service import fetch_weekly_articles

router = APIRouter(prefix="/article", tags=["Articles"])

@router.post("/fetch")
def fetch_articles(payload: ArticleFetchRequest):
    articles = fetch_weekly_articles(
        topics=payload.topics,
        max_articles_per_topic=payload.max_articles_per_topic
    )
    return {
        "count": len(articles),
        "week": articles[0]["week_id"] if articles else None
    }
