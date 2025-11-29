from fastapi import APIRouter, HTTPException, status, UploadFile, File
from typing import List
from bson import ObjectId
import io
import re
import PyPDF2

from app.models.questions_model import questions_collection
from app.schemas.questions_schema import QuestionCreate, QuestionResponse

router = APIRouter(prefix="/api/items", tags=["Items"])


@router.get("", response_model=List[QuestionResponse])
async def get_items():
    try:
        items = list(questions_collection.find({}, {"_id": 0}))
        return items
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving items: {str(e)}"
        )


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def add_item(item: QuestionCreate):
    try:
        questions_collection.insert_one(item.dict())
        return {"message": "Item added"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding item: {str(e)}"
        )

@router.post("/extract-github")
async def extract_github(file: UploadFile = File(...)):
    try:
        pdf_stream = io.BytesIO(await file.read())
        reader = PyPDF2.PdfReader(pdf_stream)
        github_links = []

        # Regex for GitHub links
        github_pattern = r'(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)?'

        for page in reader.pages:
            # Extract text links
            text = page.extract_text() or ""
            github_links += re.findall(github_pattern, text, re.IGNORECASE)

            # Extract annotation links
            if "/Annots" in page:
                for annot in page["/Annots"]:
                    obj = annot.get_object()
                    if obj.get("/A") and obj["/A"].get("/URI"):
                        url = obj["/A"]["/URI"]
                        if re.match(github_pattern, url, re.IGNORECASE):
                            github_links.append(url)

        # Cleanup
        clean_links = []
        for link in github_links:
            link = link.rstrip('/.')
            if not link.startswith("http"):
                link = "https://" + link
            if link not in clean_links:
                clean_links.append(link)

        if clean_links:
            return {"github_link": clean_links[0], "all_links": clean_links}
        else:
            return {"github_link": None, "message": "No GitHub link found in the PDF."}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error extracting GitHub links: {str(e)}"
        )
