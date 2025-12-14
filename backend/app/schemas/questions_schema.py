from pydantic import BaseModel
from typing import Optional

class QuestionBase(BaseModel):
    name: str
    value: str

class QuestionCreate(QuestionBase):
    pass

class QuestionResponse(QuestionBase):
    pass
