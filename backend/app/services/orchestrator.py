from bson import ObjectId
from app.models.user_model import users_collection
from app.models.job_model import jobs_collection
from app.services.preprocessing import preprocess_pdf
from app.services.extractors.cv_extractor import extract_from_cv, extract_handle_from_url
from app.services.extractors.linkedin_extractor import extract_from_linkedin
from app.services.extractors.github_analyzer import analyze_github
from app.services.extractors.jd_extractor import extract_from_jd
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def run_evaluation(user_id: str, job_id: str) -> dict:
    """
    Orchestrate the evaluation pipeline
    
    Loads user and job data, preprocesses PDFs, calls extractors,
    and merges all outputs into unified JSON
    
    Args:
        user_id: MongoDB user document ID
        job_id: MongoDB job document ID
    
    Returns:
        Merged JSON with candidate and job_description keys
    """
    # 1. Load user and job from MongoDB
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise ValueError(f"User {user_id} not found")
    
    # Map user to candidate structure for compatibility with existing pipeline
    candidate = {
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "github_handle": user.get("github_handle", ""),
        "github_url": user.get("github_url", ""),
        "cv_file_path": user.get("cv_file_path"),
        "linkedin_file_path": user.get("linkedin_file_path")
    }
    
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
    
    # 4. Call GitHub analyzer - prioritize handle from CV, then extract from github_url, then use github_handle
    github_handle = ""
    source = ""
    
    # First, use handle from CV if available
    if extracted_github_handle:
        github_handle = extracted_github_handle
        source = "CV"
    else:
        # Second, try to extract from github_url
        github_url = candidate.get("github_url", "")
        if github_url:
            extracted_handle = extract_handle_from_url(github_url)
            if extracted_handle:
                github_handle = extracted_handle
                source = "user.github_url"
            else:
                logger.debug(f"Could not extract handle from github_url: {github_url}")
        
        # Third, fallback to github_handle from user
        if not github_handle:
            user_handle = candidate.get("github_handle", "")
            if user_handle:
                github_handle = user_handle.strip()
                source = "user.github_handle"
    
    if github_handle:
        logger.info(f"Using GitHub handle: {github_handle} (source: {source})")
        github_data = analyze_github(github_handle)
    else:
        logger.info("No GitHub handle found in CV, user.github_url, or user.github_handle")
        github_data = {
            "repos": [],
            "commits_last_12m": 0,
            "external_prs_merged": 0
        }
    
    # 5. Call JD extractor
    jd_text = job.get("jd_text", "")
    # Fix "ob Description" -> "Job Description" if needed
    if jd_text.startswith("ob Description"):
        jd_text = "Job Description" + jd_text[14:]
    # Pass job_id for caching to ensure same job always extracts same skills
    jd_data = extract_from_jd(jd_text, job_id=job_id)
    # Ensure jd_text is preserved in jd_data for semantic analysis (use fixed version)
    if "jd_text" not in jd_data:
        jd_data["jd_text"] = jd_text
    
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

