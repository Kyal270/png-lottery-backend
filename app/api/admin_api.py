# app/api/admin_api.py
from fastapi import APIRouter, HTTPException, Depends, Header
from app.api.auth import get_admin_user
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
import jose.jwt as jwt
from jose import jwt, JWTError

import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/api/admin", tags=["Admin Actions"])
SECRET_KEY = os.getenv("SECRET_KEY", "YOUR_SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# --- Admin ဖြစ်မဖြစ် စစ်ဆေးမည့် Function ---
def get_admin_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        user = db.query(models.User).filter(models.User.username == username).first()
        
        # 🌟 Admin ဟုတ်မဟုတ် စစ်ဆေးခြင်း
        if not user or user.role != "admin":
            # 🌟 ဒီနေရာမှာ ဖြတ်ချလိုက်ရင် အောက်က except ထဲ မရောက်အောင် ပြင်ထားသည်
            raise HTTPException(status_code=403, detail="Admin privileges required")
            
        return user
        
    except JWTError: # 🌟 Exception အစား JWTError လို့ ပြောင်းပါ
        raise HTTPException(status_code=401, detail="Could not validate credentials")


# ==========================================
#             ADMIN ENDPOINTS
# ==========================================

# ၁။ Pending ဖြစ်နေသော Transactions များကို ယူရန်
@router.get("/transactions/pending")
async def get_pending_transactions(admin: models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    transactions = db.query(models.Transaction).filter(models.Transaction.status == "pending").all()
    
    result = []
    for txn in transactions:
        user = db.query(models.User).filter(models.User.id == txn.user_id).first()
        result.append({
            "id": txn.id,
            "username": user.username if user else "Unknown",
            "type": txn.type,
            "amount": txn.amount,
            "method": txn.method,
            "account_name": txn.account_name, # 🌟 ဒါလေး ထပ်ဖြည့်လိုက်ပါ
            "ref": txn.ref_id if txn.ref_id else txn.account_no,
            "date": txn.created_at.strftime("%d %b %Y, %I:%M %p")
        })
    return result

# ၂။ Transaction ကို Approve လုပ်ရန်
@router.put("/transaction/{txn_id}/approve")
async def approve_transaction(
    txn_id: int, 
    admin: models.User = Depends(get_admin_user), # 🌟 အပေါ်က function ကို လှမ်းသုံးပါသည်
    db: Session = Depends(get_db)
):
    txn = db.query(models.Transaction).filter(models.Transaction.id == txn_id).first()
    if not txn or txn.status != "pending":
        raise HTTPException(status_code=400, detail="Transaction not found or already processed")

    user = db.query(models.User).filter(models.User.id == txn.user_id).first()
    
    # Deposit ဆိုရင် User Balance ထဲ ပိုက်ဆံထည့်ပေးရပါမယ်
    if txn.type == "deposit":
        user.balance += txn.amount
    
    # Withdraw ဆိုရင်တော့ Balance ထဲက ကြိုနှုတ်ထားပြီးသားမို့ Status ပဲ ပြောင်းပေးရုံပါ
    txn.status = "success"
    
    db.commit()
    return {"message": f"Transaction {txn_id} approved successfully"}

# ၃။ Transaction ကို Reject လုပ်ရန်
@router.put("/transaction/{txn_id}/reject")
async def reject_transaction(txn_id: int, admin: models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    txn = db.query(models.Transaction).filter(models.Transaction.id == txn_id).first()
    if not txn or txn.status != "pending":
        raise HTTPException(status_code=400, detail="Transaction not found or already processed")

    user = db.query(models.User).filter(models.User.id == txn.user_id).first()
    
    # Withdraw ကို Reject လုပ်ရင် နှုတ်ထားတဲ့ ပိုက်ဆံ ပြန်ပေါင်းပေးရပါမယ်
    if txn.type == "withdraw":
        user.balance += txn.amount
        
    txn.status = "failed"
    
    db.commit()
    return {"message": f"Transaction {txn_id} rejected"}