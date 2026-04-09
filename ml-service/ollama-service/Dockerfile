# Base image with Ollama preinstalled
FROM ollama/ollama:latest

# Set work directory
WORKDIR /app

# Copy service code
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Pull the Ollama model
RUN ollama serve & sleep 5 && ollama pull gameAssistantGeneral

# Expose FastAPI port
EXPOSE 8002

# Start FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]