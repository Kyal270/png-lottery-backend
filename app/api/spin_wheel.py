# app/api/spin_wheel.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import random
from app.database import get_db
from app import models
from app.api.user_auth import get_current_user # 🌟 Auth ကို လှမ်းယူပါမည်

router = APIRouter(prefix="/api/spin", tags=["Spin Wheel"])

# 🌟 current_user ကို Depends နဲ့ လှမ်းယူလိုက်ပါပြီ
@router.post("/play")
def play_spin_wheel(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    
    # User က လှည့်ပြီးသားဆိုရင် ထပ်လှည့်ခွင့်မပေးပါ
    if current_user.locked_spin_bonus > 0:
        raise HTTPException(status_code=400, detail="You have already claimed your spin bonus!")

    # 🌟 Weighted Probability Logic (၁ မှ ၅ ကို ပိုပေါက်စေမည်)
    prizes = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    weights = [12, 12, 12, 12, 12, 10, 10, 10, 5, 5]
    winning_number = random.choices(prizes, weights=weights, k=1)[0]

    # 🌟 လက်ရှိ Login ဝင်ထားသော User ရဲ့ အကောင့်ထဲသို့ ပေါက်သောငွေ သွားသိမ်းမည်
    current_user.locked_spin_bonus = float(winning_number)
    db.commit()

    return {
        "status": "success",
        "winning_number": winning_number,
        "message": f"You won {winning_number} PGK!"
    }