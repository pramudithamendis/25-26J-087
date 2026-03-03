from fastapi import APIRouter, HTTPException, status, UploadFile, File, Request
from fastapi import Depends
from app.auth.dependencies import get_current_user
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
from app.models.questions_readme_model import questions_readme_collection
from app.schemas.questions_schema import QuestionCreate, QuestionResponse
from app.schemas.questions_cloneRepo import CloneRequest

import urllib.parse
import base64
import httpx

import os
from git import Repo
from pathlib import Path

router = APIRouter(prefix="/api/items", tags=["Items"])

@router.get("", response_model=List[QuestionResponse])
async def get_items(user=Depends(get_current_user)):
    try:
        items = list(questions_collection.find({}, {"_id": 0}))
        return items
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving items: {str(e)}"
        )


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def add_item(item: QuestionCreate,user=Depends(get_current_user)):
    try:
        questions_collection.insert_one(item.dict())
        return {"message": "Item added"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding item: {str(e)}"
        )


async def fetch_readme(user: str, repo: str):
    """
    Fetch the README content for a given GitHub repo.
    """
    url = f"{GITHUB_API}/{user}/{repo}/readme"
    headers = {"Accept": "application/vnd.github.v3.raw"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return None
    return response.text


@router.post("/extract-github-readme")
async def extract_github_and_store(user=Depends(get_current_user), file: UploadFile = File(...)):
    """
    Extract GitHub links from PDF, fetch README content, and store in MongoDB.
    """
    try:
        pdf_stream = io.BytesIO(await file.read())
        reader = PyPDF2.PdfReader(pdf_stream)
        github_links = []

        github_pattern = r'(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)?'

        # Extract links from text and annotations
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

        if not clean_links:
            return {"message": "No GitHub links found in the PDF."}

        # Fetch README and store in MongoDB
        stored_repos = []
        for link in clean_links:
            parts = link.replace("https://github.com/", "").split("/")
            if len(parts) < 2:
                continue
            user, repo = parts[0], parts[1]
            readme_content = await fetch_readme(user, repo)
            if readme_content:
                doc = {
                    "user": user,
                    "repo": repo,
                    "github_url": link,
                    "readme": readme_content
                }
                questions_readme_collection.insert_one(doc)
                stored_repos.append(link)

        return {
            "message": f"Stored README content for {len(stored_repos)} repositories",
            "repos_stored": stored_repos
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error extracting GitHub links or storing README: {str(e)}"
        )
                
GITHUB_API = "https://api.github.com/repos"


# @router.get("/readme")
# async def get_readme(user: str, repo: str):
#     if not user or not repo:
#         raise HTTPException(status_code=400, detail="Provide user & repo parameters")

#     url = f"{GITHUB_API}/{user}/{repo}/readme"
#     headers = {"Accept": "application/vnd.github.v3.raw"}

#     response = requests.get(url, headers=headers)

#     if response.status_code != 200:
#         raise HTTPException(
#             status_code=response.status_code,
#             detail={"error": "Could not fetch README", "details": response.json()}
#         )

#     return response.text

model = SentenceTransformer('all-MiniLM-L6-v2')

def find_best_matching_project(job_description, projects):
    job_embedding = model.encode(job_description, convert_to_tensor=True)
    project_texts = [p["readme"] for p in projects]
    project_embeddings = model.encode(project_texts, convert_to_tensor=True)

    similarities = util.cos_sim(job_embedding, project_embeddings)[0].cpu().numpy()

    best_index = int(np.argmax(similarities))
    best_project = projects[best_index]
    best_score = float(similarities[best_index])

    return best_project, best_score, similarities


@router.post("/match-project")
async def match_project(payload: dict,user=Depends(get_current_user)):
    if "job_description" not in payload:
        raise HTTPException(
            status_code=400,
            detail="Request must include job_description"
        )

    job_description = payload["job_description"]
    username =  payload["username"]
    projects = list(questions_readme_collection.find({"user": username}))

    best_project, best_score, similarities = find_best_matching_project(job_description, projects)

    ranking = [
        {"repo": projects[i]["repo"], "score": float(similarities[i]), "github_url": projects[i]["github_url"]}
        for i in range(len(projects))
    ]

    ranking_sorted = sorted(ranking, key=lambda x: x["score"], reverse=True)

    return {
        "best_project": {
            "repo": best_project["repo"],
            "readme": best_project["readme"],
            "github_url": best_project["github_url"],
            "score": round(best_score, 4)
        },
        "ranking": ranking_sorted
    }

@router.get("/repos/{username}")
async def get_public_repos(username: str,user=Depends(get_current_user)):
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

@router.post("/clone")
def clone_repo(payload: CloneRequest,user=Depends(get_current_user)):
    repo_url = payload.repo_url
    dest = os.path.abspath(payload.dest)

    try:
        
        if os.path.exists(dest):
            raise HTTPException(
                status_code=400,
                detail=f"Destination path already exists: {dest}"
            )

        Repo.clone_from(repo_url, dest)
        return {"status": "success", "repo": repo_url, "destination": dest}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


client = ollama.Client()
MODEL_NAME = "llama3.2:1b"

@router.post("/ask")
async def generate_questions(payload: dict, user=Depends(get_current_user)):
    folder = payload.get("folder")
    filenames = payload.get("filenames")  # <-- now expecting list

    if not folder or not filenames:
        raise HTTPException(status_code=400, detail="Missing 'folder' or 'filenames'.")

    if not isinstance(filenames, list) or len(filenames) == 0:
        raise HTTPException(status_code=400, detail="'filenames' must be a non-empty list.")

    combined_content = ""

    # 🔁 Loop through all selected files
    for filename in filenames:
        filepath = os.path.join(folder, filename)

        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                file_content = f.read()
                combined_content += f"\n\n--- FILE: {filename} ---\n"
                combined_content += file_content
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error reading file {filename}: {str(e)}"
            )

    # 🧠 Build prompt from ALL files
    prompt = (
        "Read the following code/files and generate a list of clear, helpful questions "
        "that someone might ask to better understand them. "
        "Note that the user has done this project 1 year ago so sometimes the user might have forgotten some details."
        "Avoid preamble\n\n"
        f"--- TEXT START ---\n{combined_content}\n--- TEXT END ---\n\n"
        "Questions:"
    )

    response = client.generate(model=MODEL_NAME, prompt=prompt)

    return {"questions": response.response}

@router.get("/files/{username}/{reponame}")
async def list_files(username: str,reponame: str):
    FILES_DIR = Path(__file__).parent.parent.parent / "uploads" / "repos" / username /reponame
    print(FILES_DIR)
    try:
        return [f.name for f in FILES_DIR.iterdir() if f.is_file()]
    except Exception:
        raise HTTPException(status_code=500, detail="Cannot read files")

@router.get("/files/{username}/{reponame}/{filename}")
async def get_file(username: str,reponame: str,filename: str):
    FILES_DIR = Path(__file__).parent.parent.parent / "uploads" / "repos" / username /reponame
    file_path = FILES_DIR / filename
    print(file_path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return file_path.read_text()

import joblib
from app.services.hiring_duration.stage_tracker import StageTracker   # REQUIRED

import os
import joblib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

MODEL_PATH = os.path.join(
    BASE_DIR,
    "app",
    "ml_models",
    "hiring_duration",
    "stage_tracker_model.pkl"
)

model_bundle = joblib.load(MODEL_PATH)

tracker = StageTracker(model_bundle["df"])

tracker.models = model_bundle["models"]
tracker.jobtitle_encoding = model_bundle["jobtitle_encoding"]


@router.post("/predict-hiring-timeline")
async def predict_timeline(payload: dict, user=Depends(get_current_user)):

    try:
        prediction = tracker.predict_remaining_stages(payload)

        return {
            "timeline_predictions": prediction
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )