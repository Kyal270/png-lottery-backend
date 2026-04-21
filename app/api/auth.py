import pyotp
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from pydantic import BaseModel

# Local Imports
from app.database import get_db
from app import models
from app.core.security import verify_password, create_access_token, SECRET_KEY, ALGORITHM

# 🌟 Router ကို တစ်ခါတည်း သေချာ ကြေညာပါသည် (အောက်တွင် ထပ်မကြေညာတော့ပါ)
router = APIRouter(prefix="/api/auth", tags=["Admin Auth"])

# 🌟 Admin အတွက် Master Secret Key
ADMIN_TOTP_SECRET = "JBSWY3DPEHPK3PXP" 

# Token ကို Header ထဲကနေ ဆွဲထုတ်ပေးမည့်အပိုင်း
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/user-auth/login")

# Current User ကို ဆွဲထုတ်မည့် Function

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_role: str = payload.get("role")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# 🌟 get_current_user ကို အရင်စစ်ပြီးမှ Role ကို ထပ်စစ်မည့် Function
async def get_admin_user(current_user: models.User = Depends(get_current_user)):
    # current_user ထဲမှာ role ပါမပါ သေချာစစ်ပါမည်
    if not current_user or current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Access Denied: Admin privileges required!"
        )
    return current_user

# Admin Login အတွက် Request Model
class AdminLoginRequest(BaseModel):
    username: str
    password: str
    auth_code: str 

@router.post("/login")
async def admin_login(request: AdminLoginRequest, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == request.username).first()
    
    if not db_user or not verify_password(request.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials!")
        
    if db_user.role != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized: Admin access required!")
    
    # 4. Google Authenticator Code စစ်ဆေးခြင်း
    totp = pyotp.TOTP(ADMIN_TOTP_SECRET)
    if not totp.verify(request.auth_code):
        raise HTTPException(status_code=401, detail="Invalid Auth Code!")

    # 5. အကုန်မှန်ကန်ပါက Token ထုတ်ပေးခြင်း
    token = create_access_token(data={"sub": db_user.username, "role": db_user.role})
    
    return {
        "access_token": token,
        "role": db_user.role,
        "message": "Welcome Master! Authenticated successfully."
    }