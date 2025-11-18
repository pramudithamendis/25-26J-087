from pydantic import BaseModel, EmailStr, field_validator
import re

class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @field_validator('password')
    def validate_password(cls, v):
        # 1. Check encoding length for bcrypt (max 72 bytes)
        if len(v.encode('utf-8')) > 72:
            raise ValueError("Password too long. Maximum 72 characters allowed (due to security hashing limits).")

        # 2. Minimum length
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")

        # 3. Require variety: uppercase, lowercase, digit, special char
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character.")

        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str