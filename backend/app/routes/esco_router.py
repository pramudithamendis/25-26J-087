import logging
from fastapi import APIRouter
from app.services.esco_mapper import get_esco_mapper

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/esco", tags=["ESCO"])

# ============================================================
# ESCO SKILL AND OCCUPATION MAPPING ENDPOINTS
# ============================================================

@router.get("/map-job-title")
async def map_job_title(job_title: str):
    """
    Map a free-text job title to its closest ESCO occupation concept.

    Used internally during feature engineering to standardise job titles
    before computing title match scores between CV and job description.

    Returns the matched ESCO occupation or an error if unavailable.
    """
    esco = get_esco_mapper()

    if not esco:
        logger.warning("ESCO mapper unavailable for job title mapping")
        return {"error": "ESCO not available"}

    result = esco.map_job_title(job_title)
    if not result:
        logger.info(f"No ESCO match found for job title: '{job_title}'")
        return {"error": "No match found"}

    logger.info(f"Mapped job title '{job_title}' to ESCO occupation")
    return result


@router.get("/map-skill")
async def map_skill(skill: str):
    """
    Map a free-text skill to its closest ESCO skill concept.

    Used internally during skill match score computation to normalise
    skill names from CV text before comparing against job description
    requirements. Enables partial credit for semantically related skills.

    Returns the matched ESCO skill concept or an error if unavailable.
    """
    esco = get_esco_mapper()

    if not esco:
        logger.warning("ESCO mapper unavailable for skill mapping")
        return {"error": "ESCO not available"}

    result = esco.map_skill(skill)
    if not result:
        logger.info(f"No ESCO match found for skill: '{skill}'")
        return {"error": "No match found"}

    logger.info(f"Mapped skill '{skill}' to ESCO concept")
    return result