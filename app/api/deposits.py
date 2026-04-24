# app/api/deposits.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from app.database import get_db
from app import models

router = APIRouter(prefix="/api/deposits", tags=["Admin - Deposits"])

class ActionRequest(BaseModel):
    id: int
    action: str  # "approve" သို့မဟုတ် "reject"

# 📥 [GET] Pending ဖြစ်နေသော ငွေသွင်းစာရင်းများကို ဆွဲထုတ်ရန်
@router.get("/pending")
def get_pending_deposits(db: Session = Depends(get_db)):
    deposits = db.query(models.Transaction).filter(
        models.Transaction.type == "deposit",
        models.Transaction.status == "pending"
    ).all()

    result = []
    for d in deposits:
        user = db.query(models.User).filter(models.User.id == d.user_id).first()
        result.append({
        "id": d.id,
        "username": user.username if user else "Unknown",
        "amount": d.amount,
        "bankName": d.method,
        "refId": d.ref_id,
        "time": d.created_at.strftime("%d %b %Y, %I:%M %p"),
        "receiptUrl": d.receipt_url if hasattr(d, 'receipt_url') else None
    })
    return result

# 📤 [POST] ငွေသွင်းမှုကို Approve / Reject လုပ်ရန် (🌟 Bonus Logic ပေါင်းထည့်ထားသည်)
@router.post("/action")
def process_deposit_action(req: ActionRequest, db: Session = Depends(get_db)):
    txn = db.query(models.Transaction).filter(models.Transaction.id == req.id).first()
    
    if not txn or txn.type != "deposit" or txn.status != "pending":
        raise HTTPException(status_code=400, detail="Invalid transaction or already processed")

    user = db.query(models.User).filter(models.User.id == txn.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if req.action == "approve":
        txn.status = "success"
        
        # ၁။ သွင်းလိုက်သော ငွေရင်းကို ပင်မစာရင်း (balance) ထဲ ထည့်မည်
        user.balance += txn.amount 
        
        bonus_messages = []
        
        # 🌟 ၂။ First Deposit 5% & Spin Wheel Unlocked (Bonus Balance သို့ ထည့်မည်)
        if not user.is_first_deposit_done:
            # First Deposit Bonus (5%)
            first_deposit_bonus = txn.amount * 0.05
            user.bonus_balance += first_deposit_bonus
            bonus_messages.append(f"FD Bonus: +{first_deposit_bonus}")
            
            # Spin Wheel Unlock (အနည်းဆုံး 10 သွင်းမှ)
            if txn.amount >= 10 and user.locked_spin_bonus > 0:
                user.bonus_balance += user.locked_spin_bonus
                bonus_messages.append(f"Spin Wheel Unlocked: +{user.locked_spin_bonus}")
                user.locked_spin_bonus = 0.0 # ဖြည်ပြီးလျှင် 0 ထားမည်
                
            user.is_first_deposit_done = True

        # 🌟 ၃။ Lifetime Referral Bonus Logic (user_code ကို အသုံးပြု၍ ရှာဖွေခြင်း)
        if user.referred_by:
            # 💡 ဒီနေရာမှာ models.User.user_code လို့ ပြောင်းလိုက်ပါပြီ
            referrer = db.query(models.User).filter(models.User.user_code == user.referred_by).first()
            if referrer:
                ref_bonus = 0
                if txn.amount >= 1000: ref_bonus = 50
                elif txn.amount >= 500: ref_bonus = 25
                elif txn.amount >= 300: ref_bonus = 15
                elif txn.amount >= 100: ref_bonus = 5
                elif txn.amount >= 50: ref_bonus = 2.5
                
                if ref_bonus > 0:
                    referrer.bonus_balance += ref_bonus
                    # (နောက်ပိုင်း History ပြချင်ပါက Referrer အတွက် Transaction မှတ်ပေးနိုင်ပါသည်)

        db.commit()
        
        msg = "Deposit approved successfully!"
        if bonus_messages:
            msg += f" ({', '.join(bonus_messages)})"
            
        return {"status": "success", "message": msg}
        
    elif req.action == "reject":
        txn.status = "failed"
        db.commit()
        return {"status": "success", "message": "Deposit rejected!"}
    else:
        raise HTTPException(status_code=400, detail="Invalid action keyword")
