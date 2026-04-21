from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str
    auth_code: Optional[str] = None # User တွေအတွက် မလိုတဲ့အတွက် Optional ထားပေးရပါမယ်

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    message: str