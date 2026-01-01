from fastapi import APIRouter, UploadFile, File, Depends
from app.auth.dependencies import get_current_user
import tempfile
from app.parsers.cv_parser import parse_resume
from app.models.cv_model import cv_collection  # Motor async collection

router = APIRouter(prefix="/api/cv", tags=["Cv Parsing"])

@router.post("/submit")
def submit_cv(file: UploadFile = File(...), user: dict = Depends(get_current_user) ):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file.file.read())
        pdf_path = tmp.name

    parsed = parse_resume(pdf_path)
    document = {
        "name": parsed["contacts"].get("name"),
        "emails": parsed["contacts"].get("emails", []),
        "phones": parsed["contacts"].get("phones", []),
        "links": parsed["contacts"].get("links", {}),
        "sections": parsed.get("sections", {}),
        "raw_text": parsed.get("raw_text", "")
    }

    result = cv_collection.insert_one(document)  # sync insert
    document["_id"] = str(result.inserted_id)

    return {
        "status": "success",
        "message": "CV parsed and saved successfully.",
        "resume": document
    }

