from fastapi import FastAPI
from app.auth.auth_router import auth_router
from app.routes.user_router import router as user_router
from app.routes.cv_routes import router as cv_router

app = FastAPI()

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(cv_router)

