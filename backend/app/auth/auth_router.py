from fastapi import APIRouter, HTTPException
from app.schemas.user_schema import UserCreate, UserLogin
from app.utils.password import hash_password, verify_password
from app.models.user_model import get_users_collection
from app.auth.jwt_handler import create_access_token

auth_router = APIRouter(prefix="/auth", tags=["Auth"])

@auth_router.post("/register")
async def register(user: UserCreate):
    users_collection = get_users_collection()
    
    existing = await users_collection.find_one({"email": user.email})
    if existing:
        raise HTTPException(400, "Email already registered")
    
    hashed = hash_password(user.password)
    await users_collection.insert_one({"email": user.email, "password": hashed})
    
    return {"message": "User registered successfully"}

@auth_router.post("/login")
async def login(user: UserLogin):
    users_collection = get_users_collection()
    
    found = await users_collection.find_one({"email": user.email})
    if not found or not verify_password(user.password, found["password"]):
        raise HTTPException(401, "Invalid email or password")
    
    token = create_access_token({"email": user.email})
    return {"access_token": token, "token_type": "bearer"}