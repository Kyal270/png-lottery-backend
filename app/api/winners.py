# app/api/admin.py (သို့မဟုတ် သက်ဆိုင်ရာ router ဖိုင်တွင် ထည့်ရန်)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app.api.auth import get_current_user # (ညီကို့ရဲ့ auth လမ်းကြောင်းအတိုင်း ပြင်ပါ)

router = APIRouter(prefix="/api/winners", tags=["Admin - Winners"])
# ... အခြား Admin API များ ...

@router.get("/all")
def get_all_winners(db: Session = Depends(get_db)):
    # 🌟 Ticket ဇယားနဲ့ User ဇယားကို ပေါင်းပြီး နိုင်ထားတဲ့ (win_amount > 0) သူများကို ရှာပါမည်
    winning_tickets = db.query(models.Ticket, models.User).join(
        models.User, models.Ticket.user_id == models.User.id
    ).filter(
        models.Ticket.win_amount > 0  # ငွေလျော်ထားပြီးသား Ticket များကိုသာ ယူမည်
    ).order_by(models.Ticket.created_at.desc()).all()

    winners_list = []
    for ticket, user in winning_tickets:
        winners_list.append({
            "id": ticket.id,
            "drawId": ticket.draw_number,
            "userId": user.username,         # 🌟 User ဇယားထဲက Username ကို ယူပါမည်
            "winNumber": ticket.number,
            "payout": ticket.win_amount,
            "time": ticket.created_at.strftime("%d %b %Y, %I:%M %p") if ticket.created_at else "Unknown"
        })
        
    return winners_list