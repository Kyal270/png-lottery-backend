# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app import models
from app.api import auth, dashboard, deposits, withdrawals, financials, history, users, winners
from app.api import user_auth, admin_api
import os
from fastapi.staticfiles import StaticFiles

os.makedirs("uploads", exist_ok=True)


app = FastAPI(title="PNG 3D Lottery API", version="1.0.0")
models.Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 🌟 Router ကို App ထဲသို့ တပ်ဆင်ခြင်း
app.include_router(auth.router)
app.include_router(user_auth.router)
# 🌟 Dashboard API လမ်းကြောင်းကို တပ်ဆင်လိုက်ပါပြီ
app.include_router(dashboard.router)
app.include_router(deposits.router)
app.include_router(withdrawals.router)
app.include_router(financials.router)
app.include_router(history.router)
app.include_router(users.router)
app.include_router(winners.router)
app.include_router(user_auth.router)
app.include_router(admin_api.router) # 🌟 ဒါလေး ထပ်ဖြည့်ပေးပါ

@app.get("/")
def read_root():
    return {"message": "System Online: PNG 3D Lottery Backend Infrastructure Active 🛡️"}