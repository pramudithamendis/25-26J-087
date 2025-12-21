from pydantic import BaseModel
from typing import Optional

class CloneRequest(BaseModel):
    repo_url: str
    dest: str