from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.auth.dependencies import get_current_user
from app.schemas.cv_schema import CVSubmitResponse, CVParsed
from app.database import cv_collection
import tempfile
from datetime import datetime
from bson import ObjectId
import os
from app.parsers.cv_parser import parse_resume  

router = APIRouter(prefix="/cv", tags=["CV Management"])


@router.post("/submit", response_model=CVSubmitResponse)
async def submit_cv(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    if not file.filename.lower().endswith(('.pdf', '.txt', '.docx')):
        raise HTTPException(400, "Only PDF, TXT, and DOCX files are supported")
    
    # Save temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        pdf_path = tmp.name
    
    try:
        # Parse CV
        parsed = parse_resume(pdf_path)

        # Safe defaults
        contacts = parsed.get("contacts") or {}
        sections = parsed.get("sections") or {}
        links = contacts.get("links") or {}

        basics = {
            "name": contacts.get("name", ""),
            "email": contacts.get("emails")[0] if contacts.get("emails") else None,
            "phone": contacts.get("phones")[0] if contacts.get("phones") else None,
            "linkedin": links.get("linkedin")[0] if links.get("linkedin") else None,
            "github": links.get("github")[0] if links.get("github") else None,
            "website": links.get("portfolio")[0] if links.get("portfolio") else None,
            "summary": sections.get("summary", ""),
            "address": contacts.get("address", "")
        }

        # Store structured sections
        structured_sections = {
            "work": parsed.get("work", []),
            "education": parsed.get("education", []),
            "skills": parsed.get("skills", []),
            "projects": parsed.get("projects", []),
            "certificates": parsed.get("certificates", [])
        }

        document = {
            "cv_id": str(ObjectId()),
            "basics": basics,
            **structured_sections,
            "sections": sections,
            "raw_text": parsed.get("raw_text", ""),
            "uploaded_at": datetime.utcnow(),
            "user_email": user.get("email"),
        }

        # Insert to MongoDB
        result = cv_collection.insert_one(document)
        document["_id"] = str(result.inserted_id)
        document["cv_id"] = str(result.inserted_id)

        return CVSubmitResponse(
            status="success",
            message="CV parsed and saved successfully",
            cv_id=str(result.inserted_id),
            parsed_data=CVParsed(**document)
        )

    except Exception as e:
        raise HTTPException(500, f"CV parsing failed: {str(e)}")

    finally:
        try:
            os.unlink(pdf_path)
        except:
            pass


@router.get("/list")
async def list_cvs(user: dict = Depends(get_current_user)):
    """Get all CVs submitted by the current user"""
    
    
    cursor = cv_collection.find(
        {"user_email": user.get("email")},
        {"name": 1, "uploaded_at": 1, "emails": 1, "parser_version": 1}
    )
    
    cvs = []
    for cv in cursor:
        cv["cv_id"] = str(cv["_id"])
        del cv["_id"]
        cvs.append(cv)
    
    return {"cvs": cvs, "count": len(cvs)}


@router.get("/{cv_id}")
async def get_cv(cv_id: str, user: dict = Depends(get_current_user)):
    """Retrieve a specific CV by ID"""
   
    
    try:
        cv = cv_collection.find_one(
            {"_id": ObjectId(cv_id), "user_email": user.get("email")}
        )
        
        if not cv:
            raise HTTPException(404, "CV not found")
        
        cv["cv_id"] = str(cv["_id"])
        del cv["_id"]
        
        return cv
        
    except Exception as e:
        raise HTTPException(400, f"Invalid CV ID: {str(e)}")


@router.get("/{cv_id}/experience")
async def get_parsed_experience(cv_id: str, user: dict = Depends(get_current_user)):
    """
    Get structured experience data extracted from CV
    Useful for debugging feature engineering
    """
    
    
    try:
        cv = cv_collection.find_one(
            {"_id": ObjectId(cv_id), "user_email": user.get("email")}
        )
        
        if not cv:
            raise HTTPException(404, "CV not found")
        
        # Extract structured experience using feature engineering parser
        from app.services.feature_engineering import parse_experience_from_sections
        
        sections = cv.get("sections", {})
        jobs = parse_experience_from_sections(sections)
        
        return {
            "cv_id": cv_id,
            "total_jobs": len(jobs),
            "jobs": jobs,
            "raw_experience_text": sections.get("experience", "")
        }
        
    except Exception as e:
        raise HTTPException(400, f"Error parsing experience: {str(e)}")