from fastapi import APIRouter, HTTPException, status
from app.schemas.user_schema import UserCreate, UserLogin
from app.utils.password import hash_password, verify_password
from app.models.user_model import users_collection
from .jwt_handler import create_access_token
import logging

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/auth", tags=["Auth"])

@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserCreate):
    """Register a new user"""
    try:
        logger.info(f"Registration attempt for email: {user.email}")
        existing = users_collection.find_one({"email": user.email})
        if existing:
            logger.warning(f"Registration failed: Email {user.email} already registered")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        hashed = hash_password(user.password)
        # Add default role as 'user', can be changed manually to 'admin' in DB
        result = users_collection.insert_one({
            "email": user.email,
            "password": hashed,
            "role": "user",  # Default role
            "first_name": user.first_name,
            "last_name": user.last_name,
            "city": user.city,
            "phone_number": user.phone_number
        })
        logger.info(f"User registered successfully: {user.email}, ID: {result.inserted_id}")
        return {"message": "User registered successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@auth_router.post("/login", status_code=status.HTTP_200_OK)
def login(user: UserLogin):
    """Login user and return JWT token"""
    try:
        logger.info(f"Login attempt for email: {user.email}")
        found = users_collection.find_one({"email": user.email})

        if not found:
            logger.warning(f"Login failed: User {user.email} not found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        if not verify_password(user.password, found["password"]):
            logger.warning(f"Login failed: Invalid password for {user.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        token = create_access_token({"email": user.email})
        logger.info(f"Login successful for: {user.email}")
        return {"access_token": token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )