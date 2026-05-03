"""
Internal router — endpoints consumed only by sibling services (API → ML).

All routes require the X-Internal-Secret header matching INTERNAL_SERVICE_SECRET.
When INTERNAL_SERVICE_SECRET is empty (local dev / single-service mode), the
check is skipped so local development works without extra configuration.
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/internal", tags=["internal"])


def _verify_secret(x_internal_secret: str | None) -> None:
    """Reject requests that don't carry the shared internal secret."""
    expected = settings.INTERNAL_SERVICE_SECRET.strip()
    if not expected:
        return  # no secret configured — open (local dev)
    if x_internal_secret != expected:
        raise HTTPException(status_code=403, detail="Forbidden")


class ExtractSkillsRequest(BaseModel):
    text: str


class ExtractSkillsResponse(BaseModel):
    skills: list[str]


@router.post("/extract-skills", response_model=ExtractSkillsResponse)
async def extract_skills_endpoint(
    body: ExtractSkillsRequest,
    x_internal_secret: str | None = Header(default=None),
):
    """
    Extract skills from raw text using the BERT NER model.
    Called by the lightweight API service when it needs skill extraction.
    """
    _verify_secret(x_internal_secret)

    try:
        from app.ml_models.hybrid_extractor import hybrid_detect
        skills = hybrid_detect(body.text)
    except Exception:
        # Fallback to BERT-only extraction if hybrid extractor unavailable
        from app.ml_models.skill_ner_loader import extract_skills
        skills = extract_skills(body.text)

    return ExtractSkillsResponse(skills=skills)


@router.get("/warmup")
async def warmup(x_internal_secret: str | None = Header(default=None)):
    """
    Pre-load all ML models into memory.
    Cloud Run calls this after container startup to eliminate cold-start latency
    on the first real request.
    """
    _verify_secret(x_internal_secret)

    results = {}

    try:
        from app.services.model_loader import get_model, get_preprocessor
        get_model()
        get_preprocessor()
        results["ensemble"] = "loaded"
    except Exception as exc:
        results["ensemble"] = f"error: {exc}"

    try:
        from app.services.turnover_service import get_shap_explainer
        get_shap_explainer()
        results["shap"] = "loaded"
    except Exception as exc:
        results["shap"] = f"error: {exc}"

    try:
        from app.ml_models.skill_ner_loader import extract_skills
        extract_skills("Python machine learning")
        results["bert_ner"] = "loaded"
    except Exception as exc:
        results["bert_ner"] = f"error: {exc}"

    return {"status": "warm", "models": results}
