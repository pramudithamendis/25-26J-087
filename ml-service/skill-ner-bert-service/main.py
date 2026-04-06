from fastapi import FastAPI
from pydantic import BaseModel
from hybrid_extractor import hybrid_detect
from loader import model_health_check

app = FastAPI()

class TextInput(BaseModel):
    text: str

@app.post("/extract")
def extract_skills_api(data: TextInput):
    skills = hybrid_detect(data.text)
    return {"skills": skills}

@app.get("/health")
def health():
    return model_health_check()