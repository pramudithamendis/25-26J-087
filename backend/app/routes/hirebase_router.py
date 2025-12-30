from fastapi import APIRouter, HTTPException, Depends
from datetime import date
from app.auth.dependencies import get_current_user
from app.schemas.hirebase_schema import (
    HirebaseFetchRequest,
    HirebaseFetchResponse
)
from app.services.hirebase_service import fetch_hirebase_jobs

router = APIRouter(prefix="/hirebase", tags=["Hirebase"])


@router.post("/fetch", response_model=HirebaseFetchResponse)
def fetch_hirebase_endpoint(
    payload: HirebaseFetchRequest,
    user=Depends(get_current_user)
):
    try:
        jobs = fetch_hirebase_jobs(
            limit=payload.limit,
            page=payload.page
        )

        return {
            "fetched_count": len(jobs),
            "fetch_date": date.today().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Hirebase fetch failed: {str(e)}"
        )
