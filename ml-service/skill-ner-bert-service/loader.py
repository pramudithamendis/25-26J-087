from transformers import BertTokenizerFast, BertForTokenClassification
import torch
from pathlib import Path
from functools import lru_cache

# ============================================================
# Model Path 
# ============================================================
MODEL_DIR = Path(__file__).parent / "model"

# Device setup
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Label mapping (MUST match training)
id2label = {
    0: "O",
    1: "B-SKILL",
    2: "I-SKILL"
}

BAD_PUNCT = set(['.', ',', ':', ';', '"', "'", '(', ')', '[', ']'])

# ============================================================
# Lazy Load Model 
# ============================================================
@lru_cache(maxsize=1)
def get_model():
    tokenizer = BertTokenizerFast.from_pretrained(str(MODEL_DIR))
    model = BertForTokenClassification.from_pretrained(str(MODEL_DIR))
    
    model.to(device)
    model.eval()

    return tokenizer, model

# ============================================================
# Cleaning
# ============================================================
def clean_skill(skill: str) -> str:
    if skill.lower().endswith("'s") or skill.lower().endswith("’s"):
        skill = skill[:-2]

    skill = skill.replace("—", " ").replace("–", " ")
    skill = ''.join(c for c in skill if c not in BAD_PUNCT)

    return skill.strip().lower()

# ============================================================
# Main Extraction Function
# ============================================================
def extract_skills(text: str):
    if not text or not text.strip():
        return []

    tokenizer, model = get_model()

    tokens = text.split()

    inputs = tokenizer(
        tokens,
        is_split_into_words=True,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=256
    )

    word_ids = inputs.word_ids(batch_index=0)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)
        predictions = torch.argmax(outputs.logits, dim=-1)[0].cpu().numpy()

    # Align tokens back to words
    predicted_labels = []
    prev_word_idx = None
    for i, word_idx in enumerate(word_ids):
        if word_idx is None:
            continue
        if word_idx != prev_word_idx:
            predicted_labels.append(predictions[i])
            prev_word_idx = word_idx

    # Build skills
    skills = []
    current = []

    for token, label_id in zip(tokens, predicted_labels):
        label = id2label[label_id]

        if label == "B-SKILL":
            if current:
                skills.append(" ".join(current))
            current = [token]

        elif label == "I-SKILL":
            if current:
                current.append(token)

        else:
            if current:
                skills.append(" ".join(current))
                current = []

    if current:
        skills.append(" ".join(current))

    # Normalize + deduplicate
    skills = list(set(clean_skill(s) for s in skills if len(s.strip()) > 1))

    return skills

# ============================================================
# Health Check 
# ============================================================
def model_health_check():
    try:
        tokenizer, model = get_model()
        return {
            "status": "ok",
            "device": str(device),
            "model_path": str(MODEL_DIR)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }