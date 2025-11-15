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

```
backend/
├── app/
│   ├── main.py              # FastAPI app initialization and entry point
│   ├── config.py            # Configuration and environment settings
│   ├── database.py          # Database connection setup
│   ├── models/              # Database models (e.g., SQLAlchemy, MongoDB)
│   ├── routes/              # API endpoint blueprints
│   ├── schemas/             # Pydantic models for request/response validation
│   ├── services/            # Business logic layer
│   ├── auth/                # Authentication and authorization
│   ├── utils/               # Utility functions
│   └── __pycache__/         # Python cache (ignored by .gitignore)
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (not committed)
└── README.md                # This file
```

## Prerequisites

- Python 3.8+ installed and available on `PATH`
- Git (optional, to clone the repo)

## Setup (Windows PowerShell)

Open PowerShell in the project root (`g:\Project\research\25-26J-087`) and run:

```powershell
cd "g:\Project\research\25-26J-087"
# create venv in the project root (if not present)
python -m venv venv
# activate the venv
.\venv\Scripts\Activate.ps1
# install dependencies for the backend
pip install -r backend\requirements.txt
```

Notes:
- If you prefer the `backend` folder to have its own venv, change the `python -m venv` target accordingly.
- After activating the venv, make sure VS Code (if used) points to `G:\Project\research\25-26J-087\venv\Scripts\python.exe` as the interpreter.

## Environment variables

Create a `.env` file in the `backend/` folder with variables your app expects. Example:

```env
MONGO_URI=mongodb://localhost:27017/mydb
MONGO_DB=mydatabase
JWT_SECRET=your-secret-key-here
ENV=development
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
   .\venv\Scripts\Activate
   ```
   You should see `(venv)` at the start of your terminal prompt.

4. **Install dependencies:**
   ```powershell
   pip install -r backend\requirements.txt
   ```

5. **(Optional) Create `.env` file** in `backend/` folder with your configuration (see [Environment variables](#environment-variables) section).

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

3. **Run the FastAPI app with Uvicorn:**
   ```powershell
   cd backend
   uvicorn app.main:app --reload
   ```
   - `--reload` enables auto-restart on file changes (development only)
   - For production, remove `--reload` and optionally add `--workers` for multiple processes

4. **Access the app:**
   - **Interactive API docs (Swagger UI):** `http://127.0.0.1:8000/docs`
   - **Alternative API docs (ReDoc):** `http://127.0.0.1:8000/redoc`
   - **API root:** `http://127.0.0.1:8000`

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

## License

Add your project license here.
