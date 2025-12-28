# backend/app/routes/articles_router.py
from fastapi import APIRouter, HTTPException, Depends
from app.auth.dependencies import get_current_user
from typing import List
from app.schemas.article_schema import ArticleFetchRequest, ArticleResponse, SkillExtractionResponse
from app.services.article_service import fetch_weekly_articles
from app.services.skill_extraction_service import extract_skills_from_articles

router = APIRouter(prefix="/article", tags=["Articles"])


@router.post("/fetch", response_model=List[ArticleResponse])
def fetch_articles(payload: ArticleFetchRequest,user=Depends(get_current_user)):
    articles = fetch_weekly_articles(
        topics=payload.topics,
        max_articles_per_topic=payload.max_articles_per_topic
    )

    # Convert to ArticleResponse format
    response_articles = [
        {
            "title": art.get("title", ""),
            "topic": art.get("topic", ""),
            "source_type": art.get("source_type", ""),
            "published_date": art.get("published_date", ""),
        }
        for art in articles
    ]

    return response_articles


@router.post("/extract_skills", response_model=SkillExtractionResponse)
def extract_article_skills(user=Depends(get_current_user)):
    """
    Extract skills from stored articles
    """
    try:
        result = extract_skills_from_articles()

        return {
            "success": True,
            "processed_articles": result["processed_articles"],
            "unique_skills": result["unique_skills"]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Skill extraction failed: {str(e)}"
        )
