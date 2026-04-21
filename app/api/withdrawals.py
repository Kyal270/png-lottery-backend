# app/api/withdrawals.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app import models

router = APIRouter(prefix="/api/withdrawals", tags=["Admin - Withdrawals"])

class ActionRequest(BaseModel):
    id: int
    action: str

# 📥 [GET] Pending ဖြစ်နေသော ငွေထုတ်စာရင်းများကို ဆွဲထုတ်ရန်
@router.get("/pending")
def get_pending_withdrawals(db: Session = Depends(get_db)):
    withdrawals = db.query(models.Transaction).filter(
        models.Transaction.type == "withdraw",
        models.Transaction.status == "pending"
    ).all()

    result = []
    for w in withdrawals:
        user = db.query(models.User).filter(models.User.id == w.user_id).first()
        result.append({
            "id": w.id,
            "username": user.username if user else "Unknown",
            "amount": w.amount,
            "bankName": w.method,
            "accountName": w.account_name,
            "accountNo": w.account_no,
            "time": w.created_at.strftime("%d %b %Y, %I:%M %p")
        })
    return result

# 📤 [POST] ငွေထုတ်မှုကို Approve / Reject လုပ်ရန်
@router.post("/action")
def process_withdrawal_action(req: ActionRequest, db: Session = Depends(get_db)):
    txn = db.query(models.Transaction).filter(models.Transaction.id == req.id).first()
    
    if not txn or txn.type != "withdraw" or txn.status != "pending":
        raise HTTPException(status_code=400, detail="Invalid transaction or already processed")

    user = db.query(models.User).filter(models.User.id == txn.user_id).first()

    if req.action == "approve":
        txn.status = "success"
        message = "Withdrawal approved successfully!"
    elif req.action == "reject":
        txn.status = "failed"
        # 🌟 Reject လုပ်လျှင် ကြိုနှုတ်ထားသော ငွေကို User ထံ ပြန်ပေါင်းပေးခြင်း
        if user:
            user.balance += txn.amount
        message = "Withdrawal rejected. Funds returned to user balance."
    else:
        raise HTTPException(status_code=400, detail="Invalid action keyword")

    db.commit()
    return {"status": "success", "message": message}