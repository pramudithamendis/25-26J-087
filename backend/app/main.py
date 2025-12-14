from fastapi import FastAPI
from app.auth.auth_router import auth_router
from app.routes.user_router import router as user_router
from app.routes.candidate_router import router as candidate_router
from app.routes.job_router import router as job_router
from app.routes.evaluation_router import router as evaluation_router
from app.routes.questions_router import router as questions_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(candidate_router)
app.include_router(job_router)
app.include_router(evaluation_router)
app.include_router(questions_router)
