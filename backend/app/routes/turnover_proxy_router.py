"""
Proxy router — forwards all /turnover/* requests from the public API service
to the internal ML service.

The API service validates the user's JWT before proxying, so unauthenticated
requests never reach the ML service. The ML service re-validates the JWT as
defence-in-depth. The X-Internal-Secret header is added so the ML service
can optionally require it for extra assurance.
"""
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from app.auth.dependencies import get_current_user
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/turnover", tags=["Early Attrition Risk Prediction"])

_ML_TIMEOUT = 300  # seconds — prediction pipeline can be slow


async def _forward(request: Request, sub_path: str) -> Response:
    ml_url = settings.ML_SERVICE_URL.rstrip("/")
    if not ml_url:
        raise HTTPException(503, "ML_SERVICE_URL is not configured")

    target = f"{ml_url}/turnover/{sub_path}" if sub_path else f"{ml_url}/turnover"

    # Forward all original headers except hop-by-hop ones; inject internal secret
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length", "transfer-encoding")
    }
    if settings.INTERNAL_SERVICE_SECRET:
        headers["X-Internal-Secret"] = settings.INTERNAL_SERVICE_SECRET

    body = await request.body()

    try:
        async with httpx.AsyncClient(timeout=_ML_TIMEOUT) as client:
            resp = await client.request(
                method=request.method,
                url=target,
                headers=headers,
                content=body,
                params=dict(request.query_params),
            )
    except httpx.ConnectError as exc:
        logger.error("Cannot reach ML service at %s: %s", ml_url, exc)
        raise HTTPException(503, "ML service is unavailable")
    except httpx.TimeoutException:
        raise HTTPException(504, "ML service timed out")

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
    )


@router.api_route(
    "/{sub_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy(
    sub_path: str,
    request: Request,
    _user: dict = Depends(get_current_user),
):
    return await _forward(request, sub_path)


@router.api_route("", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_root(
    request: Request,
    _user: dict = Depends(get_current_user),
):
    return await _forward(request, "")
