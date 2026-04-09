from ollama import Client

client = Client()
MODEL_NAME = "gameAssistantGeneral"

def generate_questions_with_ollama(prompt: str):
    response = client.generate(model=MODEL_NAME, prompt=prompt)
    return response.response