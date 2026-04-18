# Dockerfile.ml — ML-heavy service (~3.5GB image, models downloaded from GCS at startup)
# Used by Cloud Run "ml" service.
# ML model files are NOT baked into this image — they are downloaded from GCS
# at container startup via gcs_loader.py, keeping the image rebuild fast.

FROM python:3.11-slim

WORKDIR /app

# System deps: tesseract OCR, libgomp for tree-based models, poppler for PDFs
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    libgomp1 \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code — model files excluded via .dockerignore
COPY app ./app

EXPOSE 8080
ENV SERVICE_TYPE=ml

# Single worker — BERT + SHAP are not thread-safe; concurrency handled by Cloud Run scaling
CMD ["uvicorn", "app.main_ml:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
