from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List

from app import models
from app.database import get_db

router = APIRouter(prefix="/api/financials", tags=["Admin - Financials"])

# 🌟 ၁။ Data Models (Frontend လိုချင်သော ပုံစံများ)
class SummaryData(BaseModel):
    totalDeposits: float
    totalWithdrawals: float

class RoundData(BaseModel):
    id: int
    drawId: str
    date: str
    winNumber: str
    totalReceived: float
    totalPaid: float
    profit: float

class BetData(BaseModel):
    id: int
    userId: str
    number: str
    amount: float
    draw: str

class FinancialsResponse(BaseModel):
    summary: SummaryData
    rounds: List[RoundData]
    activeBets: List[BetData]

# 📥 [GET] ငွေကြေးအချက်အလက်အားလုံးကို တစ်ပြိုင်နက်ဆွဲထုတ်ရန် API
@router.get("/overview", response_model=FinancialsResponse)
def get_financial_overview(db: Session = Depends(get_db)):
   # 🌟 ၁။ Summary Data တွက်ချက်ခြင်း (Database နှင့် အတိအကျ ကိုက်ညီအောင် ပြင်ဆင်ထားသည်)
    total_deposits = db.query(func.sum(models.Transaction.amount)).filter(
        func.lower(models.Transaction.type) == "deposit",
        func.lower(models.Transaction.status) == "success"  # 🌟 'approved' အစား 'success' ဟု ပြင်ထားသည်
    ).scalar() or 0.0

    total_withdrawals = db.query(func.sum(models.Transaction.amount)).filter(
        func.lower(models.Transaction.type) == "withdraw",  # 🌟 'withdrawal' အစား 'withdraw' ဟု ပြင်ထားသည်
        func.lower(models.Transaction.status) == "success"  # 🌟 'approved' အစား 'success' ဟု ပြင်ထားသည်
    ).scalar() or 0.0

    summary = SummaryData(totalDeposits=total_deposits, totalWithdrawals=total_withdrawals)

    # 🌟 ၂။ Round Data တွက်ချက်ခြင်း (Draw တစ်ခုချင်းစီအလိုက်)
    # ပြီးခဲ့တဲ့ ပွဲစဉ်တွေအတွက် တွက်ပါမယ်
    draw_results = db.query(models.DrawResult).order_by(models.DrawResult.created_at.desc()).all()
    rounds = []
    
    for idx, draw in enumerate(draw_results):
        # ထိုပွဲစဉ်အတွက် ဝင်ငွေ (Total Received)
        total_received = db.query(func.sum(models.Ticket.bet_amount)).filter(
            models.Ticket.draw_number == draw.draw_number
        ).scalar() or 0.0
        
        # ထိုပွဲစဉ်အတွက် ထွက်ငွေ (Total Paid)
        total_paid = db.query(func.sum(models.Ticket.win_amount)).filter(
            models.Ticket.draw_number == draw.draw_number
        ).scalar() or 0.0

        rounds.append(RoundData(
            id=draw.id,
            drawId=draw.draw_number,
            date=draw.created_at.strftime("%d/%m/%Y") if draw.created_at else "N/A",
            winNumber=draw.winning_number,
            totalReceived=total_received,
            totalPaid=total_paid,
            profit=total_received - total_paid
        ))

    # 🌟 ၃။ Active Bets (လက်ရှိပွဲစဉ်အတွက် ထိုးထားသော စာရင်း) တွက်ချက်ခြင်း
    # အရင်ဆုံး လက်ရှိပွဲစဉ် (Active Draw) ကို ရှာပါမယ်
    last_draw = db.query(models.DrawResult).order_by(models.DrawResult.id.desc()).first()
    active_draw = f"DRAW-{str(int(last_draw.draw_number.split('-')[1]) + 1).zfill(3)}" if last_draw else "DRAW-001"

    active_tickets = db.query(models.Ticket, models.User).join(
        models.User, models.Ticket.user_id == models.User.id
    ).filter(
        models.Ticket.draw_number == active_draw
    ).all()

    active_bets = []
    for ticket, user in active_tickets:
        active_bets.append(BetData(
            id=ticket.id,
            userId=user.username,
            number=ticket.number,
            amount=ticket.bet_amount,
            draw=ticket.draw_number
        ))

    return FinancialsResponse(
        summary=summary,
        rounds=rounds,
        activeBets=active_bets
    )