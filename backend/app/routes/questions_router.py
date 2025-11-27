from fastapi import APIRouter, HTTPException, status
from typing import List
from bson import ObjectId

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
