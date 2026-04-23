import uuid # 🌟 uuid ကို import လုပ်ပါမည်
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from app.database import Base
from datetime import datetime, timezone

# 🌟 Custom ID ထုတ်ပေးမည့် Helper Function အသစ်
def generate_custom_id(prefix: str) -> str:
    # ကျပန်းစာသားထဲမှ အရှေ့ ၆ လုံးကိုယူ၍ အကြီးပြောင်းမည်
    short_uuid = str(uuid.uuid4())[:6].upper()
    return f"{prefix}-{short_uuid}"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    
    # 🌟 UI တွင်ပြသမည့် User Code အသစ် (ဥပမာ USR-9A2F5C)
    user_code = Column(String, unique=True, index=True, default=lambda: generate_custom_id("USR"))
    
    username = Column(String, unique=True, index=True)
    phone_number = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String)
    
    # User အချက်အလက်များ
    bank_name = Column(String, nullable=True)
    bank_account_name = Column(String, nullable=True)
    bank_account_number = Column(String, nullable=True)
    referral_code = Column(String, nullable=True)
    
    balance = Column(Float, default=0.0)
    role = Column(String, default="user")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    
    # 🌟 UI တွင်ပြသမည့် Ticket Code အသစ် (ဥပမာ TCK-B8102A)
    ticket_code = Column(String, unique=True, index=True, default=lambda: generate_custom_id("TCK"))
    
    user_id = Column(Integer, ForeignKey("users.id"))
    draw_number = Column(String, default="DRAW-001")
    number = Column(String, index=True)
    bet_amount = Column(Float)
    status = Column(String, default="pending") 
    win_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class DrawResult(Base):
    __tablename__ = "draw_results"

    id = Column(Integer, primary_key=True, index=True)
    draw_number = Column(String, unique=True, index=True) # 🌟 ဤသည်မှာ DRAW-001 စသဖြင့် ရှိပြီးသားမို့ မပြင်တော့ပါ
    winning_number = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    
    # 🌟 UI တွင်ပြသမည့် Transaction Code အသစ် (ဥပမာ TXN-00F19D)
    txn_code = Column(String, unique=True, index=True, default=lambda: generate_custom_id("TXN"))
    
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String) # 'deposit' သို့မဟုတ် 'withdraw'
    amount = Column(Float)
    method = Column(String) # Bank Name
    
    ref_id = Column(String, nullable=True) # Deposit အတွက် Transaction ID
    receipt_url = Column(String, nullable=True)
    
    account_name = Column(String, nullable=True) # Withdraw အတွက်
    account_no = Column(String, nullable=True) # Withdraw အတွက်
    
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # 🌟 AdminBank က Transaction ရဲ့ အောက်ထဲမှာ ဝင်မနေရပါ။ အရှေ့ဆုံး (ဘယ်ဘက်အစွန်ဆုံး) မှာ ကပ်နေရပါမည်။
class AdminBank(Base):
    __tablename__ = "admin_banks"

    id = Column(Integer, primary_key=True, index=True) # 🌟 primary_key=True ပါရပါမည်
    name = Column(String, index=True)
    account_name = Column(String)
    account_no = Column(String)             # ဥပမာ - 123-456-7890
