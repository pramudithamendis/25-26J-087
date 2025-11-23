from fastapi import FastAPI
from app.auth.auth_router import auth_router
from app.routes.user_router import router as user_router
from app.routes.candidate_router import router as candidate_router

app = FastAPI()

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(candidate_router)
