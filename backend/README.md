# Backend

This folder contains the backend for the project. The backend is a **FastAPI** application with dependencies managed by a Python virtual environment.

**Quick summary:**
- **Framework:** FastAPI
- **Server:** Uvicorn (for development and production)
- **Env management:** python venv
- **Dependencies:** `requirements.txt`

**What this README covers:**
- Project structure
- Creating and activating a virtual environment (Windows PowerShell)
- Installing dependencies
- Environment variables (.env)
- Running the FastAPI app
- Project layout and where to add new routes

## Project structure

```powershell
backend/
├── app/
│   ├── main.py              # FastAPI app initialization and entry point
│   ├── config.py            # Configuration and environment settings
│   ├── database.py          # Database connection setup
│   ├── sceduler.py          # Hirebase job posting and article fetching scheduler
│   ├── __init__.py          # Package initialization
│   ├── agents/              # Agentic AI system for CV evaluation
│   ├── auth/                # Authentication and authorization
│   ├── data/                # Data files and storage
│   │   ├── articles/        # Cached articles
│   │   ├── topics.json      # Topics configuration
│   │   └── __init__.py
│   ├── jobs/                # Job postings and article fetching
│   ├── ml_models/           # ML models for CV evaluation
│   ├── models/              # Database models (SQLAlchemy, MongoDB, etc.)
│   ├── parsers/             # CV parsers
│   ├── routes/              # API endpoint blueprints
│   ├── schemas/             # Pydantic models for request/response validation
│   ├── services/            # Business logic layer (fetchers, processors, etc.)
│   └── utils/               # Utility functions
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (not committed)
├── venv/                    # virtual environment
├── uploads/
├── dataset/
├── dataset_scripts/
├── tests/
├── pytest.ini
└── README.md                
```

## Prerequisites

- Python 3.11.8 installed and available on `PATH`
- Git (optional, to clone the repo)
- **Tesseract OCR**: Required for OCR support (if processing image-based CVs)
  - Download: [Tesseract for Windows](https://github.com/UB-Mannheim/tesseract/wiki)
  - Ensure `tesseract.exe` is in your system `PATH`.

## Setup (Windows PowerShell)

Open PowerShell in the project root (`g:\Project\research\25-26J-087`) and run:

```powershell
cd "g:\Project\research\25-26J-087"
# create venv in the project root (if not present)
python -m venv venv
# activate the venv
venv\Scripts\activate 
# install dependencies for the backend
pip install -r requirements.txt
```

Notes:
- If you prefer the `backend` folder to have its own venv, change the `python -m venv` target accordingly.
- After activating the venv, make sure VS Code (if used) points to `G:\Project\research\25-26J-087\venv\Scripts\python.exe` as the interpreter.

## Environment variables

Create a `.env` file in the `backend/` folder with variables your app expects. Example:

```env
# --- Database ---
MONGO_URI=mongodb://localhost:27017/mydb
MONGO_DB=mydatabase

# --- Auth ---
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256
ENV=development

# --- GitHub ---
GITHUB_TOKEN=YOUR_GITHUB_TOKEN_HERE

# --- OpenAI API ---
OPENAI_API_KEY=YOUR_KEY
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# --- Provider Settings ---
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=openai
CV_EXTRACTION_METHOD=openai

# --- Upload Folder ---
UPLOAD_FOLDER=uploads

# --- Gnews API Key ---
GNEWS_API_KEY=

# --- Redis Queue settings (for background job processing) ---
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # Optional, leave empty if no password
EVALUATION_QUEUE_NAME=evaluations
```

The app uses `python-dotenv` to load `.env` automatically when the app starts.

## How to Run

### First-time setup (one-time)

1. **Navigate to project root:**
   ```powershell
   cd "g:\Project\research\25-26J-087"
   ```

2. **Create virtual environment:**
   ```powershell
   python -m venv venv
   ```

3. **Activate venv:**
   ```powershell
   venv\Scripts\activate 
   ```
   You should see `(venv)` at the start of your terminal prompt.

4. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

5. **(Optional) Create `.env` file** in `backend/` folder with your configuration (see [Environment variables](#environment-variables) section).

6. **(Optional) Start Redis via Docker:** From project root run `docker-compose up -d redis` (see [Running Redis with Docker](#running-redis-with-docker) below).

### Running the app (everyday)

After first-time setup, to start the app:

1. **Open PowerShell** in the project root or navigate there:
   ```powershell
   cd "g:\Project\research\25-26J-087"
   ```

2. **Activate venv (if not already active):**
   ```powershell
   .\venv\Scripts\Activate
   ```

3. **Start Redis server** (required for background job processing):
   - **Preferred (Docker):** From project root run `docker-compose up -d redis` to start Redis in the background. Keep `REDIS_HOST=localhost` in `backend/.env` when running the backend and worker on the host.
   - **Alternative (native):** Windows: Download from [Redis for Windows](https://github.com/microsoftarchive/redis/releases) or use WSL. Linux/Mac: `sudo apt-get install redis-server` or `brew install redis`. Start Redis: `redis-server` (default port 6379).

4. **Run the FastAPI app with Uvicorn:**
   ```powershell
   cd backend
   uvicorn app.main:app --reload
   ```
   - `--reload` enables auto-restart on file changes (development only)
   - For production, remove `--reload` and optionally add `--workers` for multiple processes

5. **Start the RQ worker** (in a separate terminal, required for background job processing):
   ```powershell
   cd backend
   python worker.py
   ```
   Or using RQ command:
   ```powershell
   python -m rq worker evaluations --with-scheduler
   ```

6. **Access the app:**
   - **Interactive API docs (Swagger UI):** `http://127.0.0.1:8000/docs`
   - **Alternative API docs (ReDoc):** `http://127.0.0.1:8000/redoc`
   - **API root:** `http://127.0.0.1:8000`

### Running Redis with Docker

A `docker-compose.yml` at the project root runs only Redis. The FastAPI app and RQ worker run on the host and connect to Redis at `localhost:6379`.

- **Start Redis:** From project root run `docker-compose up -d redis`.
- **Stop Redis:** Run `docker-compose down`. Add `-v` to remove the data volume for a clean state.
- **Config:** Keep `REDIS_HOST=localhost` and `REDIS_PORT=6379` in `backend/.env` when the backend and worker run on the host.

### Using an IDE (VS Code)

1. **Select the Python interpreter:**
   - Press `Ctrl+Shift+P` → type "Python: Select Interpreter"
   - Choose `G:\Project\research\25-26J-087\venv\Scripts\python.exe`

2. **Run with debugger (optional):**
   - Open the integrated terminal (Ctrl+`)
   - Activate the venv (if needed)
   - Run: `uvicorn app.main:app --reload`
   - You can now set breakpoints in your code and debug

## API & Code notes

- **Entry point:** `app/main.py` — FastAPI app initialization and route registration
- **Routes:** Add new endpoint modules in `app/routes/` and import them in `main.py`
- **Schemas:** Use Pydantic models in `app/schemas/` for request/response validation
- **Services:** Keep business logic in `app/services/` for better separation of concerns
- **Models:** Database models should live in `app/models/`
- **Auth:** Authentication logic in `app/auth/`

## Background Job Processing (Redis Queue)

The backend uses **Redis Queue (RQ)** for processing resume uploads and evaluations in the background. This allows users to submit applications and continue using the system while evaluations are processed asynchronously.

### Features

- **Non-blocking:** Users get immediate confirmation when submitting applications
- **Background Processing:** Evaluations run in the background without blocking the API
- **Status Tracking:** Applications track processing status (pending, processing, evaluated, failed)
- **Retry Logic:** Failed jobs are automatically retried up to 3 times
- **Admin Visibility:** Admins can see full processing status and evaluation results
- **User Privacy:** Users only see basic status (submitted, under_review, reviewed) - no scores or decisions

### Running the Worker

The RQ worker must be running to process background jobs:

```powershell
# Option 1: Using the worker script
cd backend
python worker.py

# Option 2: Using RQ command directly
python -m rq worker evaluations --with-scheduler
```

The worker will:
- Listen for new evaluation jobs in the Redis queue
- Process evaluations asynchronously
- Update application status in the database
- Handle errors and retries automatically

### Worker Requirements

- Redis server must be running (see [Environment variables](#environment-variables))
- Worker should run in a separate terminal/process from the FastAPI server
- For production, use a process manager (systemd, supervisor, etc.) to keep the worker running

## Agentic AI System

The backend now includes an **agentic AI system** for CV evaluation that uses autonomous agents to dynamically plan and execute evaluation workflows.

### Features

- **Dynamic Workflow**: Agents decide next steps based on current state (not fixed pipeline)
- **Hybrid Approach**: Combines rule-based (30%) and agentic reasoning (70%)
- **Tool System**: Agents use tools to interact with extractors and services
- **Memory Management**: Tracks reasoning chain for explainability
- **Fallback Mechanisms**: Automatically falls back to pipeline on errors
- **OCR Support**: Support for image-based CVs using `pytesseract` (Tesseract OCR)
- **Skill Trends Forecasting**: Predict future skill demand using historical job and Google Trends data

### Agentic Endpoints

- `POST /api/evaluate/agentic` - Run agentic evaluation (Admin-only)
- `POST /api/evaluate/dataset` - Evaluate on full dataset (Admin-only)
- `GET /api/evaluate/comparison` - Get comparison results (Admin-only)

### Configuration

Set in `.env` or `config.py`:
- `USE_AGENTIC_EVALUATION=true` - Use agentic system by default
- `AGENTIC_FALLBACK_TO_PIPELINE=true` - Fallback on errors
- `MAX_AGENT_ITERATIONS=20` - Max iterations in agentic loop
- `AGENT_TEMPERATURE=0.3` - LLM temperature for agents

### Documentation

- **Architecture**: See `docs/AGENTIC_ARCHITECTURE.md`
- **Evaluation Report**: See `docs/EVALUATION_REPORT.md`
- **Agent Code**: `app/services/agents/`

### Example: Adding a new route

Create `app/routes/cv_routes.py`:
```python
from fastapi import APIRouter, HTTPException
from app.schemas import CVSchema

router = APIRouter(prefix="/cv", tags=["cv"])

@router.get("/")
async def get_cvs():
    return {"cvs": []}

@router.post("/")
async def create_cv(cv: CVSchema):
    return {"created": cv}
```

Then register in `app/main.py`:
```python
from app.routes.cv_routes import router as cv_router

app.include_router(cv_router)
```

## Updating dependencies

When you add or upgrade packages, regenerate `requirements.txt` from the active venv:

```powershell
pip freeze > backend\requirements.txt
```

## Troubleshooting

- **Import errors in VS Code?** Ensure the workspace interpreter is set to `G:\Project\research\25-26J-087\venv\Scripts\python.exe` (see [Using an IDE (VS Code)](#using-an-ide-vs-code) section).
- **Port 8000 already in use?** Run Uvicorn on a different port: `uvicorn app.main:app --reload --port 8001`
- **ModuleNotFoundError?** Make sure the venv is activated and dependencies are installed: `pip install -r backend\requirements.txt`

## Contributing

- Add new routes in `app/routes/` as separate modules
- Keep the `main.py` factory minimal — register and initialize routes/extensions there
- Use Pydantic schemas for validation
- Keep business logic in services, not in route handlers

# ML-services 
```bash
docker run -it --rm -p 8000:8000 ner-service
```

## License

Add your project license here.
