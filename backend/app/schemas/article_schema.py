# backend/app/schemas/article_schema.py
from pydantic import BaseModel
from typing import List, Optional

class ArticleFetchRequest(BaseModel):
    max_articles_per_topic: Optional[int] = 50

class ArticleResponse(BaseModel):
    title: str
    topic: str
    source_type: str
    published_date: str

class SkillExtractionResponse(BaseModel):
    processed_articles: int
    unique_skills: List[str]
