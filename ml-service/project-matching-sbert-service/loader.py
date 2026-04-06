# ml-service/project-matching-sbert/loader.py
from sentence_transformers import SentenceTransformer

MODEL_DIR = "./model"  # folder containing the cached SBERT model

# Load once, can be imported anywhere
model = SentenceTransformer(MODEL_DIR)

def encode_text(texts, convert_to_tensor=True):
    return model.encode(texts, convert_to_tensor=convert_to_tensor)