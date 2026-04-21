from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime

from app import models
from app.database import get_db
# Admin Token စစ်မည့် function ကို Import လုပ်ရန် (ညီကို့လမ်းကြောင်းအတိုင်း ပြင်ပါ)
# from app.api.auth import get_current_admin_user 

router = APIRouter(prefix="/api/history", tags=["Admin - History"])

# 📥 [GET] မှတ်တမ်းအားလုံးကို Database မှ ဆွဲထုတ်ရန် API
@router.get("/all") # လုံခြုံရေးအတွက် admin route အောက်မှာ ထားပါ
def get_all_history(db: Session = Depends(get_db)):
    history_list = []

    # 🌟 ၁။ ငွေသွင်း / ငွေထုတ် မှတ်တမ်းများ (Transactions) ကို ဆွဲထုတ်ပါမည်
    transactions = db.query(models.Transaction, models.User).join(
        models.User, models.Transaction.user_id == models.User.id
    ).all()

    for txn, user in transactions:
        history_list.append({
            "id": f"txn_{txn.id}",
            "userId": user.username,
            "type": txn.type.capitalize(), # Deposit သို့မဟုတ် Withdrawal
            "amount": txn.amount,
            "status": txn.status.capitalize(), # Pending, Approved, Rejected
            "time_obj": txn.created_at, # စီစဉ်ရန်အတွက် ဖွက်ထားမည်
            "time": txn.created_at.strftime("%d %b %Y, %I:%M %p") if txn.created_at else "Unknown"
        })

    # 🌟 ၂။ ထိုးကြေး နှင့် ပေါက်မဲ မှတ်တမ်းများ (Tickets) ကို ဆွဲထုတ်ပါမည်
    tickets = db.query(models.Ticket, models.User).join(
        models.User, models.Ticket.user_id == models.User.id
    ).all()

    for ticket, user in tickets:
        # ထိုးကြေး (Bet) မှတ်တမ်း
        history_list.append({
            "id": f"bet_{ticket.id}",
            "userId": user.username,
            "type": "Bet",
            "amount": ticket.bet_amount,
            "status": "Success",
            "time_obj": ticket.created_at,
            "time": ticket.created_at.strftime("%d %b %Y, %I:%M %p") if ticket.created_at else "Unknown"
        })
        
        # အကယ်၍ ပေါက်ခဲ့လျှင် (Win) မှတ်တမ်းပါ ထပ်ထည့်ပါမည်
        if ticket.win_amount and ticket.win_amount > 0:
            history_list.append({
                "id": f"win_{ticket.id}",
                "userId": user.username,
                "type": "Win",
                "amount": ticket.win_amount,
                "status": "Paid",
                "time_obj": ticket.created_at, 
                "time": ticket.created_at.strftime("%d %b %Y, %I:%M %p") if ticket.created_at else "Unknown"
            })

    # 🌟 ၃. အချိန်အလိုက် အသစ်ဆုံးကို အပေါ်တင်ရန် Sort လုပ်ပါမည်
    history_list.sort(key=lambda x: x["time_obj"] if x["time_obj"] else datetime.min, reverse=True)

    # Frontend သို့ မပို့မီ time_obj ကို ပြန်ဖျက်ပါမည်
    for record in history_list:
        del record["time_obj"]

    return history_list