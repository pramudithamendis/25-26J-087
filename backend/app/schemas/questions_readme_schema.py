from pydantic import BaseModel
from typing import Optional

class QuestionReadMeBase(BaseModel):
    github_link: str
    username: str
    repo_name: str
    readme: str

class QuestionReadMeCreate(QuestionReadMeBase):
    pass

class QuestionReadMeResponse(QuestionReadMeBase):
    pass
