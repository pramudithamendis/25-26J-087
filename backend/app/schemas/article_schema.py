from pydantic import BaseModel
from typing import List, Optional

class ArticleFetchRequest(BaseModel):
    topics: Optional[List[str]] = ["technology"]
    max_articles_per_topic: Optional[int] = 50


class ArticleResponse(BaseModel):
    title: str
    topic: str
    source_type: str
    published_date: str
