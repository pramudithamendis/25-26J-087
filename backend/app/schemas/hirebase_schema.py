from pydantic import BaseModel
from typing import List, Optional


class HirebaseFetchRequest(BaseModel):
    limit: Optional[int] = 50
    page: Optional[int] = 1


class HirebaseFetchResponse(BaseModel):
    fetched_count: int
    fetch_date: str
