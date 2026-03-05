from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse
from app.auth.dependencies import get_current_user
from app.schemas.cv_schema import CVSubmitResponse, CVParsed, CVUpdateRequest
from app.database import cv_collection
from app.models.user_model import users_collection
from app.utils.file_handler import save_uploaded_file
from app.config import settings
import tempfile
from datetime import datetime
from bson import ObjectId
import os
import logging
from app.parsers.cv_parser import parse_resume  


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cv", tags=["CV Management"])


@router.post("/submit", response_model=CVSubmitResponse)
async def submit_cv(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    if not file.filename.lower().endswith(('.pdf', '.txt', '.docx')):
        raise HTTPException(400, "Only PDF, TXT, and DOCX files are supported")
    
    # Save temp file for parsing
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        pdf_path = tmp.name
    
    # Reset file for re-use (saving to uploads)
    await file.seek(0)
    
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

        # Also save the file to uploads/cv/ folder (same as job application flow)
        # so it persists and can be used by the evaluation pipeline
        try:
            user_email = user.get("email")
            user_doc = users_collection.find_one({"email": user_email})
            if user_doc:
                user_id = str(user_doc["_id"])
                saved_path = await save_uploaded_file(
                    file,
                    settings.CV_UPLOAD_FOLDER,
                    user_id,
                    'cv'
                )
                if saved_path:
                    # Update user profile with cv_file_path
                    users_collection.update_one(
                        {"email": user_email},
                        {"$set": {"cv_file_path": saved_path}}
                    )
                    logger.info(f"CV file saved to {saved_path} for user {user_id}")
                else:
                    logger.warning(f"Failed to save CV file to uploads for user {user_id}")
        except Exception as save_err:
            logger.warning(f"Could not persist CV file to uploads: {str(save_err)}")

        return CVSubmitResponse(
            success=True,
            message="CV parsed and saved successfully",
            data=CVParsed(**document)
        )

    except Exception as e:
        raise HTTPException(500, f"CV parsing failed: {str(e)}")

    finally:
        try:
            os.unlink(pdf_path)
        except:
            pass


@router.put("/{cv_id}", response_model=CVParsed)
async def update_cv(
    cv_id: str,
    update: CVUpdateRequest,
    user: dict = Depends(get_current_user)
):
    """Update an existing CV's editable fields"""
    try:
        # Verify ownership
        existing = cv_collection.find_one(
            {"_id": ObjectId(cv_id), "user_email": user.get("email")}
        )
        if not existing:
            raise HTTPException(404, "CV not found")

        # Build update dict from provided fields
        update_data = update.model_dump(exclude_none=False)

        cv_collection.update_one(
            {"_id": ObjectId(cv_id)},
            {"$set": update_data}
        )

        # Fetch updated document
        updated = cv_collection.find_one({"_id": ObjectId(cv_id)})
        updated["cv_id"] = str(updated["_id"])
        del updated["_id"]

        return CVParsed(**updated)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Failed to update CV: {str(e)}")


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


@router.get("/{cv_id}/pdf")
async def get_cv_pdf(cv_id: str, user: dict = Depends(get_current_user)):
    """Retrieve the uploaded PDF file for a CV"""

    try:
        cv = cv_collection.find_one({"_id": ObjectId(cv_id)})

        if not cv:
            raise HTTPException(status_code=404, detail="CV not found")

        # Correct email extraction
        cv_user_email = cv.get("user_email") or cv.get("basics", {}).get("email")

        if not cv_user_email:
            raise HTTPException(status_code=404, detail="CV owner email not found")

        # Find the user
        user_doc = users_collection.find_one({"email": cv_user_email})

        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")

        user_id = str(user_doc["_id"])

        # Try common extensions
        for ext in ["pdf", "txt", "docx"]:
            file_path = os.path.join(settings.CV_UPLOAD_FOLDER, f"{user_id}_cv.{ext}")

            if os.path.exists(file_path):
                return FileResponse(
                    path=file_path,
                    media_type="application/pdf" if ext == "pdf" else "application/octet-stream",
                    filename=f"{cv_id}_cv.{ext}",
                )

        # Try saved path
        if user_doc.get("cv_file_path") and os.path.exists(user_doc["cv_file_path"]):
            ext = user_doc["cv_file_path"].split(".")[-1]

            return FileResponse(
                path=user_doc["cv_file_path"],
                media_type="application/pdf" if ext == "pdf" else "application/octet-stream",
                filename=f"{cv_id}_cv.{ext}",
            )

        raise HTTPException(status_code=404, detail="CV file not found on disk")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error retrieving PDF: {str(e)}")