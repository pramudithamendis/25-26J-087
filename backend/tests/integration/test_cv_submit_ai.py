"""
Integration-ish tests for the OpenAI CV submission endpoint.

We build a minimal FastAPI app with only the CV router and mock the OpenAI extraction
so tests are deterministic and do not require external network calls.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from bson import ObjectId

from app.auth.dependencies import get_current_user
from app.routes.cv_routes import router as cv_router
from app.services.cv_extraction_openai import CVOpenAIExtractionError


def _make_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(cv_router)
    app.dependency_overrides[get_current_user] = lambda: {"email": "test@gmail.com"}
    return app


def test_submit_cv_ai_success():
    app = _make_test_app()
    client = TestClient(app)

    inserted_id = ObjectId()

    mocked_fields = {
        "basics": {
            "name": "Yashodhara Sandeepani",
            "email": "yashodharasandeepani@gmail.com",
            "phone": "+94764443783",
            "linkedin": None,
            "github": None,
            "website": "https://yashodhara.me/YashodharaSandeepani/",
            "summary": "A highly dedicated and goal-oriented individual...",
            "address": "No.99/A, 2, Pamunuwa, Handessa",
        },
        "education": [
            {
                "institution": "Sri Lanka Institute of Information Technology",
                "area": "Data Science",
                "studyType": "BSc (Hons) in Information Technology",
                "startDate": "January 2022",
                "endDate": "Present",
                "gpa": None,
                "courses": [],
            }
        ],
        "work": [
            {
                "name": "Sri Lanka Telecom",
                "position": "Data Science Intern",
                "startDate": "January 2025",
                "endDate": "July 2025",
                "summary": None,
                "highlights": ["Worked on data analysis"],
            }
        ],
        "skills": [
            {"name": "General", "level": None, "keywords": ["PowerBI", "Excel", "Python"]}
        ],
        "projects": [
            {
                "name": "Data Warehouse and Business Intelligence",
                "description": "Built a PowerBI dashboard...",
                "highlights": [],
                "url": None,
            }
        ],
        "certificates": [
            {"name": "AI/ML Engineer Stage 1", "issuer": "SLIIT", "date": None}
        ],
    }

    with patch("app.routes.cv_routes.extract_cv_to_schema_fields") as mock_extract, patch(
        "app.routes.cv_routes.cv_collection"
    ) as mock_cv_collection, patch(
        "app.routes.cv_routes.users_collection"
    ) as mock_users_collection, patch(
        "app.routes.cv_routes.save_uploaded_file"
    ) as mock_save_uploaded_file:
        mock_extract.return_value = (mocked_fields, "RAW_TEXT")
        mock_cv_collection.insert_one.return_value = Mock(inserted_id=inserted_id)
        mock_users_collection.find_one.return_value = {"_id": ObjectId(), "email": "test@gmail.com"}
        mock_save_uploaded_file.return_value = "uploads/cv/test_cv.pdf"

        resp = client.post(
            "/cv/submit-ai",
            files={"file": ("cv.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["cv_id"] == str(inserted_id)
    assert body["data"]["basics"]["name"] == "Yashodhara Sandeepani"
    assert body["data"]["work"][0]["name"] == "Sri Lanka Telecom"


def test_submit_cv_ai_openai_error_returns_500():
    app = _make_test_app()
    client = TestClient(app)

    with patch("app.routes.cv_routes.extract_cv_to_schema_fields") as mock_extract:
        mock_extract.side_effect = CVOpenAIExtractionError("OpenAI request failed: rate limit")

        resp = client.post(
            "/cv/submit-ai",
            files={"file": ("cv.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )

    assert resp.status_code == 500
    assert "CV parsing failed (OpenAI)" in resp.json()["detail"]

