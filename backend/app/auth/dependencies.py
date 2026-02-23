from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from jose import JWTError
from app.auth.jwt_handler import decode_access_token
from app.models.user_model import users_collection

auth_scheme = HTTPBearer()

def get_current_user(token: str = Depends(auth_scheme)):
    """Get current authenticated user from JWT token"""
    try:
        payload = decode_access_token(token.credentials)
        email = payload.get("email")
        
        # Verify user exists in database
        user = users_collection.find_one({"email": email})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

def get_admin_user(current_user = Depends(get_current_user)):
    """Get current user and verify admin role"""
    email = current_user.get("email")
    user = users_collection.find_one({"email": email})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Check if user has admin role (default to 'user' if role field doesn't exist)
    user_role = user.get("role", "user")
    
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user
