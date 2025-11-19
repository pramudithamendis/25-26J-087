from pydantic import BaseModel
from typing import List, Dict, Optional

class CVSchema(BaseModel):
    id: Optional[str]
    name: Optional[str]
    emails: List[str] = []
    phones: List[str] = []
    links: Dict[str, List[str]] = {}
    sections: Dict[str, str] = {}
    raw_text: Optional[str]
