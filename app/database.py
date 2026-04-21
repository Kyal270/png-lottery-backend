import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv() # .env ဖိုင်ကို ဖတ်ရန်

# .env ထဲတွင် မရှိပါက SQLite ကို default အနေဖြင့် သုံးမည်
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lottery.db")

# SQLite အတွက်သာ check_same_thread လိုအပ်ပါသည်
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()