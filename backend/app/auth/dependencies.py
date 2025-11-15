from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from jose import JWTError
from app.auth.jwt_handler import decode_access_token

auth_scheme = HTTPBearer()

def get_current_user(token: str = Depends(auth_scheme)):
    try:
        payload = decode_access_token(token.credentials)
        return payload
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")
