from fastapi import APIRouter, HTTPException, status, UploadFile, File, Request
from typing import List
from bson import ObjectId
import io
import re
import PyPDF2
import requests

from sentence_transformers import SentenceTransformer, util
import numpy as np
import ollama

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

        github_pattern = r'(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)?'

        for page in reader.pages:
            text = page.extract_text() or ""
            github_links += re.findall(github_pattern, text, re.IGNORECASE)

            if "/Annots" in page:
                for annot in page["/Annots"]:
                    obj = annot.get_object()
                    if obj.get("/A") and obj["/A"].get("/URI"):
                        url = obj["/A"]["/URI"]
                        if re.match(github_pattern, url, re.IGNORECASE):
                            github_links.append(url)

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


GITHUB_API = "https://api.github.com/repos"


@router.get("/readme")
async def get_readme(user: str, repo: str):
    if not user or not repo:
        raise HTTPException(status_code=400, detail="Provide user & repo parameters")

    url = f"{GITHUB_API}/{user}/{repo}/readme"
    headers = {"Accept": "application/vnd.github.v3.raw"}

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail={"error": "Could not fetch README", "details": response.json()}
        )

    return response.text



client = ollama.Client()
MODEL_NAME = "llama3.2:1b"

@router.post("/ask")
async def ask_model(payload: dict):
    prompt = payload.get("prompt")
    if not prompt:
        raise HTTPException(status_code=400, detail="Missing 'prompt' in request body")

    response = client.generate(model=MODEL_NAME, prompt=prompt)

    return {"response": response.response}

model = SentenceTransformer('all-MiniLM-L6-v2')

def find_best_matching_project(job_description, projects):
    job_embedding = model.encode(job_description, convert_to_tensor=True)
    project_texts = [p["title"] + " - " + p["description"] for p in projects]
    project_embeddings = model.encode(project_texts, convert_to_tensor=True)

    similarities = util.cos_sim(job_embedding, project_embeddings)[0].cpu().numpy()

    best_index = int(np.argmax(similarities))
    best_project = projects[best_index]
    best_score = float(similarities[best_index])

    return best_project, best_score, similarities


@router.post("/match-project")
async def match_project(payload: dict):
    if "job_description" not in payload or "projects" not in payload:
        raise HTTPException(
            status_code=400,
            detail="Request must include job_description and projects"
        )

    job_description = payload["job_description"]
    projects = payload["projects"]

    best_project, best_score, similarities = find_best_matching_project(job_description, projects)

    ranking = [
        {"title": projects[i]["title"], "score": float(similarities[i])}
        for i in range(len(projects))
    ]

    ranking_sorted = sorted(ranking, key=lambda x: x["score"], reverse=True)

    return {
        "best_project": {
            "title": best_project["title"],
            "description": best_project["description"],
            "score": round(best_score, 4)
        },
        "ranking": ranking_sorted
    }

@router.get("/repos/{username}")
async def get_public_repos(username: str):
    """
    Fetch all public GitHub repositories for a given user.
    """
    try:
        url = f"https://api.github.com/users/{username}/repos"
        headers = {"Accept": "application/vnd.github.v3+json"}

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail={
                    "error": "Could not fetch repositories",
                    "details": response.json()
                }
            )

        repos = response.json()

        # Clean important fields
        cleaned = [
            {
                "name": repo["name"],
                "full_name": repo["full_name"],
                "html_url": repo["html_url"],
                "description": repo.get("description"),
                "language": repo.get("language"),
                "created_at": repo.get("created_at"),
                "updated_at": repo.get("updated_at"),
                "stargazers_count": repo.get("stargazers_count"),
                "forks_count": repo.get("forks_count"),
            }
            for repo in repos
        ]

        return {"user": username, "repo_count": len(cleaned), "repos": cleaned}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching repositories: {str(e)}"
        )

