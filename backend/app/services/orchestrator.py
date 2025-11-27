from bson import ObjectId
from app.models.candidate_model import candidates_collection
from app.models.job_model import jobs_collection
from app.services.preprocessing import preprocess_pdf
from app.services.extractors.cv_extractor import extract_from_cv
from app.services.extractors.linkedin_extractor import extract_from_linkedin
from app.services.extractors.github_analyzer import analyze_github
from app.services.extractors.jd_extractor import extract_from_jd
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def run_evaluation(candidate_id: str, job_id: str) -> dict:
    """
    Orchestrate the evaluation pipeline
    
    Loads candidate and job data, preprocesses PDFs, calls extractors,
    and merges all outputs into unified JSON
    
    Args:
        candidate_id: MongoDB candidate document ID
        job_id: MongoDB job document ID
    
    Returns:
        Merged JSON with candidate and job_description keys
    """
    # 1. Load candidate and job from MongoDB
    candidate = candidates_collection.find_one({"_id": ObjectId(candidate_id)})
    if not candidate:
        raise ValueError(f"Candidate {candidate_id} not found")
    
    job = jobs_collection.find_one({"_id": ObjectId(job_id)})
    if not job:
        raise ValueError(f"Job {job_id} not found")
    
    # 2. Preprocess CV PDF (if exists)
    cv_data = None
    extracted_github_handle = None  # Track GitHub handle from CV
    if candidate.get("cv_file_path"):
        try:
            cv_preprocessed = preprocess_pdf(candidate["cv_file_path"])
            # Use OpenAI extraction if configured, otherwise use regex
            if settings.CV_EXTRACTION_METHOD == "openai" and settings.OPENAI_API_KEY:
                from app.services.extractors.cv_extractor_openai import extract_from_cv_openai
                cv_data = extract_from_cv_openai(cv_preprocessed)
            else:
                cv_data = extract_from_cv(cv_preprocessed)
            
            # Extract GitHub handle from CV
            extracted_github_handle = cv_data.get("github_handle", "").strip()
            if extracted_github_handle:
                logger.info(f"GitHub handle extracted from CV: {extracted_github_handle}")
        except Exception as e:
            # If CV processing fails, continue with empty data
            cv_data = {
                "skills_raw": [],
                "experience": [],
                "education": [],
                "github_handle": ""
            }
    else:
        cv_data = {
            "skills_raw": [],
            "experience": [],
            "education": [],
            "github_handle": ""
        }
    
    # 3. Preprocess LinkedIn PDF (if exists)
    linkedin_data = None
    if candidate.get("linkedin_file_path"):
        try:
            linkedin_preprocessed = preprocess_pdf(candidate["linkedin_file_path"])
            # Use OpenAI extraction if configured, otherwise use regex
            if settings.CV_EXTRACTION_METHOD == "openai" and settings.OPENAI_API_KEY:
                from app.services.extractors.linkedin_extractor_openai import extract_from_linkedin_openai
                linkedin_data = extract_from_linkedin_openai(linkedin_preprocessed)
            else:
                linkedin_data = extract_from_linkedin(linkedin_preprocessed)
        except Exception as e:
            # If LinkedIn processing fails, continue with empty data
            linkedin_data = {
                "skills_raw": [],
                "experience": [],
                "education": [],
                "certifications": [],
                "endorsements": []
            }
    else:
        linkedin_data = {
            "skills_raw": [],
            "experience": [],
            "education": [],
            "certifications": [],
            "endorsements": []
        }
    
    # 4. Call GitHub analyzer - prioritize handle from CV, fallback to database
    github_handle = extracted_github_handle or candidate.get("github_handle", "")
    if github_handle:
        logger.info(f"Using GitHub handle: {github_handle} (source: {'CV' if extracted_github_handle else 'database'})")
        github_data = analyze_github(github_handle)
    else:
        logger.info("No GitHub handle found in CV or database")
        github_data = {
            "repos": [],
            "commits_last_12m": 0,
            "external_prs_merged": 0
        }
    
    # 5. Call JD extractor
    jd_text = job.get("jd_text", "")
    jd_data = extract_from_jd(jd_text)
    
    # 6. Merge all outputs into unified JSON
    # Combine skills from CV and LinkedIn
    all_skills = list(set(cv_data.get("skills_raw", []) + linkedin_data.get("skills_raw", [])))
    
    # Combine experience (prefer CV, supplement with LinkedIn)
    all_experience = cv_data.get("experience", [])
    if not all_experience:
        all_experience = linkedin_data.get("experience", [])
    
    # Combine education
    all_education = list(set(cv_data.get("education", []) + linkedin_data.get("education", [])))
    
    # Build merged candidate structure
    merged_candidate = {
        "skills_raw": all_skills,
        "experience": all_experience,
        "education": all_education,
        "certifications": linkedin_data.get("certifications", []),
        "publications": linkedin_data.get("publications", []),
        "projects": linkedin_data.get("projects", []),
        "linkedin": {
            "endorsements": linkedin_data.get("endorsements", []),
            "summary": linkedin_data.get("summary", "")
        },
        "github": github_data
    }
    
    # Build merged JSON
    merged_json = {
        "candidate": merged_candidate,
        "job_description": jd_data
    }
    
    return merged_json

