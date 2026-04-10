# Base image with Ollama preinstalled
FROM ollama/ollama:latest

# Pull the Ollama model
RUN ollama serve & sleep 5 && ollama pull gameAssistantGeneral

# Expose the Ollama API port
EXPOSE 11434

# Start Ollama serve when container runs
CMD ["ollama", "serve"]