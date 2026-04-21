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
        
        # 🌟 ပြင်ဆင်ချက်: DB ထဲက ပုံလင့်ခ် အစစ်ကို ဆွဲထုတ်လိုက်ပါပြီ
        "receiptUrl": d.receipt_url if hasattr(d, 'receipt_url') else None
    })
    return result

# 📤 [POST] ငွေသွင်းမှုကို Approve / Reject လုပ်ရန်
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
        user.balance += txn.amount # 🌟 User Balance ထဲသို့ ငွေပေါင်းထည့်ခြင်း
        message = "Deposit approved successfully!"
    elif req.action == "reject":
        txn.status = "failed"
        message = "Deposit rejected!"
    else:
        raise HTTPException(status_code=400, detail="Invalid action keyword")

    db.commit()
    return {"status": "success", "message": message}