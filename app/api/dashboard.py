from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
import pyotp

# 🌟 Database နှင့် Auth များကို လှမ်းယူပါမည်
from app.database import get_db
from app import models
from app.api.auth import get_admin_user, ADMIN_TOTP_SECRET 

router = APIRouter(prefix="/api/dashboard", tags=["Admin Draw & Bets"])

class BetResponse(BaseModel):
    id: int
    userId: str
    number: str
    amount: float
    time: str
    draw: str
    status: str = "pending" 
    win_amount: float = 0.0

class PayoutRequest(BaseModel):
    draw_id: str
    winning_number: str
    auth_code: str

# ---------------------------------------------------------
# API Routes များ
# ---------------------------------------------------------

# 📥 [GET] လောင်းကြေးစာရင်းများ ဆွဲထုတ်ရန် API
@router.get("/bets", response_model=List[BetResponse])
def get_all_bets(
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user) # 🌟 Admin သာ ကြည့်ခွင့်ရှိသည်
):
    # 🌟 Ticket Table ထဲက Data များကို ဆွဲထုတ်ပါမည်
    tickets = db.query(models.Ticket).all()
    result = []
    
    for ticket in tickets:
        # Ticket ပိုင်ရှင် User ကိုပါ တွဲရှာပါမည်
        user = db.query(models.User).filter(models.User.id == ticket.user_id).first()
        
        result.append({
            "id": ticket.id,
            "userId": user.username if user else "Unknown",
            "number": ticket.number,
            "amount": ticket.bet_amount, # models.py တွင် bet_amount ဟု ပေးထားသည်
            "time": ticket.created_at.strftime("%Y-%m-%d %I:%M %p") if ticket.created_at else "N/A",
            "draw": ticket.draw_number, # models.py တွင် draw_number ဟု ပေးထားသည်
            "status": ticket.status,          # 👈 ဒါလေး အသစ်တိုးပါ
        "win_amount": ticket.win_amount,   # 👈 ဒါလေး အသစ်တိုးပါ
        })
        
    return result

# 📤 [POST] ထီပေါက်စဉ် ကြေညာရန် API
@router.post("/payout")
@router.post("/payout")
def declare_payout(request: PayoutRequest, db: Session = Depends(get_db), admin: models.User = Depends(get_admin_user)):
    
    # 🌟 ၁။ 2FA Code မှန်/မမှန် အရင်စစ်ပါမည်
    totp = pyotp.TOTP(ADMIN_TOTP_SECRET)
    if not totp.verify(request.auth_code):
        raise HTTPException(status_code=400, detail="Invalid Authentication Code! Payout Denied.")

    existing_draw = db.query(models.DrawResult).filter(models.DrawResult.draw_number == request.draw_id).first()
    if not existing_draw:
        new_result = models.DrawResult(draw_number=request.draw_id, winning_number=request.winning_number)
        db.add(new_result)
    else:
        existing_draw.winning_number = request.winning_number
    
    db.commit()

    # 🌟 ၂။ Code မှန်မှသာ အောက်က Payout အလုပ်များကို ဆက်လုပ်ပါမည်
    tickets = db.query(models.Ticket).filter(models.Ticket.draw_number == request.draw_id).all()
    
    winners_count = 0
    total_payout = 0

    for ticket in tickets:
        if ticket.status != "pending":
            continue

        if ticket.number == request.winning_number:
            payout_amount = ticket.bet_amount * 500
            user = db.query(models.User).filter(models.User.id == ticket.user_id).first()
            if user:
                user.balance += payout_amount
            
            ticket.status = "won" # 🌟 "win" အစား "won" ဟု ပြောင်းပါ
            ticket.win_amount = payout_amount
            winners_count += 1
            total_payout += payout_amount
        else:
            ticket.status = "lost" # 🌟 "lose" အစား "lost" ဟု ပြောင်းပါ

    db.commit()

    return {
        "message": f"Payout complete! {winners_count} winners got total {total_payout:,.2f} PGK.",
        "winners": winners_count,
        "total_payout": total_payout
    }

@router.get("/next-draw")
def get_next_draw(
    db: Session = Depends(get_db), 
    admin: models.User = Depends(get_admin_user)
):
    # Database ထဲက နောက်ဆုံးသိမ်းခဲ့တဲ့ ပွဲစဉ်ကို ရှာပါမည်
    last_draw = db.query(models.DrawResult).order_by(models.DrawResult.id.desc()).first()
    
    # 🌟 Database အလွတ်ကြီးဆိုရင် ပထမဆုံးပွဲစဉ်ကို ပြန်ပို့ပေးမည်
    if not last_draw or not last_draw.draw_number:
        return {"next_draw_id": "DRAW-001"}
    
    # 🌟 ရှိခဲ့ရင် DRAW-001 ထဲက 001 ကိုဆွဲထုတ်၊ 1 ပေါင်းပြီး ပြန်ပို့မည်
    try:
        parts = last_draw.draw_number.split("-")  # ["DRAW", "001"]
        current_num = int(parts[1])               # 1
        next_num = current_num + 1                # 2
        
        # DRAW-002, DRAW-015 စသဖြင့် ဂဏန်း ၃ လုံးပြည့်အောင် Format ချမည်
        next_draw_id = f"DRAW-{next_num:03d}"     
        return {"next_draw_id": next_draw_id}
    except Exception as e:
        return {"next_draw_id": "DRAW-001"} # Error တက်ရင် ပုံမှန်အတိုင်းပြန်ထားမည်