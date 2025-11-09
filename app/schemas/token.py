from pydantic import BaseModel, ConfigDict
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    plan: str
    
    model_config = ConfigDict(from_attributes=True)

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str
    user: UserResponse
    
    model_config = ConfigDict(from_attributes=True)

class TokenPayload(BaseModel):
    sub: str | None = None
