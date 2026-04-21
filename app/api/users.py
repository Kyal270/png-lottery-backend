# app/api/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from app import models
from app.database import get_db

# 🌟 Admin API များနှင့် သီးသန့်ဖြစ်စေရန် prefix ထည့်ထားသည်
router = APIRouter(prefix="/api/users", tags=["Admin - Users"])

class UserProfileResponse(BaseModel):
    id: str
    db_id: str
    joinDate: str
    balance: float
    totalDeposits: float
    totalWithdraws: float
    status: str

@router.get("/{search_term}", response_model=UserProfileResponse)
def search_user(search_term: str, db: Session = Depends(get_db)):
    # 🌟 ၁။ ဂဏန်းဖြင့်ဖြစ်စေ၊ စာသားဖြင့်ဖြစ်စေ ရှာမည်
    if search_term.isdigit():
        user = db.query(models.User).filter(models.User.id == int(search_term)).first()
    else:
        user = db.query(models.User).filter(
            func.lower(models.User.username) == search_term.lower()
        ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found in the system")

    # 🌟 Date Format ပြဿနာကို ကာကွယ်ထားသည်
    join_date = "Unknown"
    if hasattr(user, 'created_at') and user.created_at:
        try:
            join_date = user.created_at.strftime("%d/%m/%Y")
        except AttributeError:
            join_date = str(user.created_at).split()[0]

    # 🌟 ၂။ User ၏ Balance ကို ယူမည် (Wallet Table မရှိသဖြင့် User ထဲမှ တိုက်ရိုက်ယူမည်) 🌟
    # အကယ်၍ user ဇယားထဲမှာ balance အကွက်မရှိရင် 0.0 ဟု ပုံသေထားပေးမည်
    current_balance = getattr(user, "balance", 0.0)

    # 🌟 ၃။ Total Deposits
    total_deposits = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.user_id == user.id,
        func.lower(models.Transaction.type) == "deposit",
        func.lower(models.Transaction.status) == "success"
    ).scalar() or 0.0

    # 🌟 ၄။ Total Withdrawals
    total_withdraws = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.user_id == user.id,
        func.lower(models.Transaction.type) == "withdraw",
        func.lower(models.Transaction.status) == "success"
    ).scalar() or 0.0

    return UserProfileResponse(
        id=str(user.username), 
        db_id=user.user_code,         # 🌟 Database အစစ်ထဲက ID (ဥပမာ - 1, 2, 3) ကို ယူပါမည်
        joinDate=join_date,
        balance=float(current_balance),
        totalDeposits=float(total_deposits),
        totalWithdraws=float(total_withdraws),
        status="Active" # User ဇယားထဲမှာ is_active/is_banned ရှိလာရင် ဒီနေရာမှာ ပြောင်းချိတ်လို့ရပါတယ်
    )