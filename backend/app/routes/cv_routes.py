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
    
    
    # Validate file type
    if not file.filename.lower().endswith(('.pdf', '.txt', '.docx')):
        raise HTTPException(400, "Only PDF, TXT, and DOCX files are supported")
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        pdf_path = tmp.name
    
    try:
        # Parse CV using Mongo Client parser
        parsed = parse_resume(pdf_path)
        
        # Create document for MongoDB
        document = {
            "name": parsed["contacts"].get("name"),
            "emails": parsed["contacts"].get("emails", []),
            "phones": parsed["contacts"].get("phones", []),
            "links": parsed["contacts"].get("links", {}),
            "sections": parsed.get("sections", {}),
            "raw_text": parsed.get("raw_text", ""),
            "uploaded_at": datetime.utcnow(),
            "user_email": user.get("email"),
            "parser_version": "mongoClient"  # Track parser version
        }
        
        # Store in MongoDB
        
        result = cv_collection.insert_one(document)
        
        # Add cv_id to document
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
        # Clean up temp file
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