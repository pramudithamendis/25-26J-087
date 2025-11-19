from app.parsers.cv_parser import parse_resume
from app.models.cv_model import cv_collection
from bson import ObjectId

async def process_and_store_resume(pdf_path: str):
    parsed = parse_resume(pdf_path)

    document = {
        "name": parsed["contacts"].get("name"),
        "emails": parsed["contacts"].get("emails", []),
        "phones": parsed["contacts"].get("phones", []),
        "links": parsed["contacts"].get("links", {}),
        "sections": parsed.get("sections", {}),
        "raw_text": parsed.get("raw_text", "")
    }

    result = cv_collection.insert_one(document)
    document["_id"] = str(result.inserted_id)

    return document
