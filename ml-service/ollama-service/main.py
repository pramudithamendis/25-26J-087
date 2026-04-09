from fastapi import FastAPI, HTTPException
from loader import generate_questions_with_ollama

app = FastAPI()

@app.post("/generate")
async def generate_questions(payload: dict):
    prompt = payload.get("prompt")
    if not prompt:
        raise HTTPException(status_code=400, detail="Missing 'prompt' in request")
    
    questions = generate_questions_with_ollama(prompt)
    return {"questions": questions}