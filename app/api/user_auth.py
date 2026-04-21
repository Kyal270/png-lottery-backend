# app/api/user_auth.py
import os
import shutil
from sqlalchemy import func
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Header, UploadFile, File, Form
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.database import get_db
from app import models
from app.core.security import get_password_hash, verify_password, create_access_token, SECRET_KEY, ALGORITHM
from pydantic import BaseModel
from app.api.auth import get_current_user
from app.api.users import UserProfileResponse

UPLOAD_DIR = "uploads/receipts"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Router ကို သတ်မှတ်ခြင်း
router = APIRouter(prefix="/api/user-auth", tags=["User Actions & Auth"])

# --- Pydantic Models (Schemas) ---
class UserRegister(BaseModel):
    username: str
    phone_number: str
    password: str
    bank_name: str
    bank_account_name: str
    bank_account_number: str
    referral_code: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class BetRequest(BaseModel):
    number: str
    amount: float

class WithdrawCreate(BaseModel):
    amount: float
    bank: str
    account_name: str
    account_no: str

# --- Security Dependency ---
def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    try:
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = db.query(models.User).filter(models.User.username == username).first()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

# ==========================================
#              AUTH ENDPOINTS
# ==========================================

@router.post("/register")
async def register(user: UserRegister, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    
    new_user = models.User(
        username=user.username,
        phone_number=user.phone_number,
        hashed_password=get_password_hash(user.password), # 🌟 ပြင်ဆင်ထားသည်
        bank_name=user.bank_name,
        bank_account_name=user.bank_account_name,
        bank_account_number=user.bank_account_number,
        referral_code=user.referral_code,
        balance=0.0,
        role="user"
    )
    db.add(new_user)
    db.commit()
    return {"message": "Success"}

@router.post("/login")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password): # 🌟 ပြင်ဆင်ထားသည်
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Token ထုတ်ပေးခြင်း
    token = create_access_token(data={"sub": db_user.username, "role": db_user.role}) # 🌟 ပြင်ဆင်ထားသည်
    return {"access_token": token, "username": db_user.username}

# ==========================================
#             ACTION ENDPOINTS
# ==========================================

@router.get("/dashboard-data")
def get_dashboard_data(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # ၁။ Tickets နှင့် Transactions ဆွဲထုတ်သည့် နဂို Logic
    tickets = db.query(models.Ticket).filter(models.Ticket.user_id == current_user.id).order_by(models.Ticket.created_at.desc()).limit(10).all()
    transactions = db.query(models.Transaction).filter(models.Transaction.user_id == current_user.id).order_by(models.Transaction.created_at.desc()).limit(10).all()
    
    ticket_list = [{
        "id": t.id, 
        "draw": t.draw_number, 
        "number": t.number, 
        "bet_amount": t.bet_amount, 
        "date": t.created_at.strftime("%d %b %Y, %I:%M %p"), 
        "status": t.status, 
        "win_amount": t.win_amount
    } for t in tickets]

    txn_list = [{
        "id": txn.id, 
        "type": txn.type, 
        "amount": txn.amount, 
        "method": txn.method, 
        "ref": txn.ref_id if txn.ref_id else txn.account_no, 
        "date": txn.created_at.strftime("%d %b %Y, %I:%M %p"), 
        "status": txn.status
    } for txn in transactions]

    # 🌟 ၂။ Last Draw Data ကို ရှာသည့် Logic (အသစ်ထည့်ထားသည်)
    last_draw_record = db.query(models.DrawResult).order_by(models.DrawResult.id.desc()).first()
    last_draw_data = None
    if last_draw_record and last_draw_record.draw_number:
        draw_date = last_draw_record.created_at.strftime("%d %b %Y") if last_draw_record.created_at else "Today"
        last_draw_data = {
            "draw_number": last_draw_record.draw_number,
            "winning_number": last_draw_record.winning_number,
            "date": draw_date
        }

    # 🌟 Active Draw ကို ရှာခြင်း (နောက်ဆုံးထွက်ထားတဲ့ Draw + 1)
    last_draw = db.query(models.DrawResult).order_by(models.DrawResult.id.desc()).first()
    
    # နောက်ဆုံးထွက်ထားတာ DRAW-005 ဆိုရင် Active က DRAW-006 ဖြစ်ရပါမယ်
    if last_draw:
        last_num = int(last_draw.draw_number.split("-")[1])
        active_draw = f"DRAW-{str(last_num + 1).zfill(3)}"
    else:
        active_draw = "DRAW-001"

    # ၃။ Return ပြန်မည့် Data အားလုံးစုစည်းခြင်း
    return {
        "wallet": {
            "username": current_user.username,
            "balance": current_user.balance,
            "currency": "PGK",
            "bank_name": current_user.bank_name,
            "bank_account_name": current_user.bank_account_name,
            "bank_account_number": current_user.bank_account_number
        },
        "tickets": ticket_list,
        "transactions": txn_list,
        "active_draw": active_draw,
        "last_draw": last_draw_data  # 🌟 ဒေတာကို React ဆီ ပို့ပေးမည့် နေရာ
    }
    
@router.post("/bet")
async def place_bet(bet: BetRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.balance < bet.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    current_user.balance -= bet.amount
    # 🌟 လက်ရှိပွဲစဉ်ကို ပြန်ရှာပါ
    last_draw = db.query(models.DrawResult).order_by(models.DrawResult.id.desc()).first()
    active_draw = f"DRAW-{str(int(last_draw.draw_number.split('-')[1]) + 1).zfill(3)}" if last_draw else "DRAW-001"

    new_ticket = models.Ticket(
        user_id=current_user.id,
        number=bet.number,
        bet_amount=bet.amount,
        draw_number=active_draw # 🌟 ပုံသေမသုံးဘဲ dynamic သုံးလိုက်ပါပြီ
    )
    
    db.add(new_ticket)
    db.commit()
    
    return {"message": "Bet placed successfully!", "new_balance": current_user.balance}

@router.post("/deposit")
async def create_deposit(
    amount: float = Form(...),
    bank: str = Form(...),
    ref_id: str = Form(...),
    receipt: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    try:
        # ၁။ ပုံ၏ Extension ကို ယူခြင်း (ဥပမာ .jpg, .png)
        file_extension = os.path.splitext(receipt.filename)[1] if receipt.filename else ".jpg"
        
        # ၂။ ပုံအမည် သတ်မှတ်ခြင်း (ဥပမာ deposit_1_TXN123.jpg)
        file_name = f"deposit_{current_user.id}_{ref_id}{file_extension}"
        
        # 🌟 ဒီစာကြောင်း ရှိမရှိ သေချာစစ်ပါ (ဒါက Pylance error တက်နေတဲ့ အချက်ပါ)
        file_path = os.path.join(UPLOAD_DIR, file_name)

        # ၃။ ပုံကို Server ထဲ သိမ်းဆည်းခြင်း
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(receipt.file, buffer)

        # ၄။ Database (Transaction Table) ထဲတွင် သိမ်းဆည်းခြင်း
        new_tx = models.Transaction(
            user_id=current_user.id,
            type="deposit",
            amount=amount,
            method=bank,
            ref_id=ref_id,
            receipt_url=file_path, # 🌟 file_path ကို ဒီမှာ သုံးထားပါသည်
            status="pending"
        )

        db.add(new_tx)
        db.commit()
        
        return {"message": "Deposit request submitted successfully"}
        
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload receipt")

@router.post("/withdraw")
async def create_withdraw(
    request: WithdrawCreate, # 🌟 အပေါ်မှာ ဆောက်ခဲ့တဲ့ Class ကို ဒီမှာ ပြန်သုံးတာပါ
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    if current_user.balance < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    new_tx = models.Transaction(
        user_id=current_user.id,
        type="withdraw",
        amount=request.amount,
        method=request.bank,
        account_name=request.account_name,
        account_no=request.account_no,
        status="pending"
    )
    current_user.balance -= request.amount # Balance ချက်ချင်းနှုတ်ထားမည်
    db.add(new_tx)
    db.commit()
    return {"message": "Success"}

@router.get("/my-profile", response_model=UserProfileResponse)
def get_my_profile(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # 🌟 User က သူ့ Token နဲ့သူ လာတာဖြစ်လို့ ရှာနေစရာမလိုတော့ပါ၊ current_user ကို တန်းသုံးရုံပါပဲ
    
    join_date = "Unknown"
    if hasattr(current_user, 'created_at') and current_user.created_at:
        try:
            join_date = current_user.created_at.strftime("%d/%m/%Y")
        except AttributeError:
            join_date = str(current_user.created_at).split()[0]

    current_balance = getattr(current_user, "balance", 0.0)

    total_deposits = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.user_id == current_user.id,
        func.lower(models.Transaction.type) == "deposit",
        func.lower(models.Transaction.status) == "success"
    ).scalar() or 0.0

    total_withdraws = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.user_id == current_user.id,
        func.lower(models.Transaction.type) == "withdraw",
        func.lower(models.Transaction.status) == "success"
    ).scalar() or 0.0

    safe_db_id = str(current_user.user_code) if current_user.user_code else str(current_user.id)

    return UserProfileResponse(
        id=str(current_user.username), 
        db_id=safe_db_id, # 🌟 NULL ဖြစ်နေရင်တောင် ရိုးရိုး ID ကို String ပြောင်းပြီး ပို့ပေးပါမည်
        joinDate=join_date,
        balance=float(current_balance),
        totalDeposits=float(total_deposits),
        totalWithdraws=float(total_withdraws),
        status="Active" 
    )