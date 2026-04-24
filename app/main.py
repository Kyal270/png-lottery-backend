# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app import models
from app.api import auth, dashboard, deposits, withdrawals, financials, history, users, winners
from app.api import user_auth, admin_api, spin_wheel
import os
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware # 🌟 CORS အတွက် Import လုပ်ပါ

# 🌟 slowapi အတွက် လိုအပ်သည်များ Import လုပ်ခြင်း
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# 🌟 Limiter ကို ကြေညာပါမည် (User ရဲ့ IP Address ပေါ်မူတည်ပြီး မှတ်သားပါမည်)
limiter = Limiter(key_func=get_remote_address)

os.makedirs("uploads", exist_ok=True)


app = FastAPI(title="PNG 3D Lottery API", version="1.0.0")
models.Base.metadata.create_all(bind=engine)

# ==========================================
# 🛡️ CORS Policy သတ်မှတ်ခြင်း 🌟
# ==========================================
origins = [
    "http://localhost:5173",  # React Dev Server
    "http://127.0.0.1:5173",  # React Dev Server (Alternative)
    # 💡 နောင်တစ်ချိန် Live လွှင့်တဲ့အခါ "https://www.your-lottery-website.com" စသဖြင့် ဒီမှာ လာတိုးရပါမည်
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,   # 🌟 အပေါ်မှာ ရေးထားတဲ့ လင့်ခ်တွေကိုပဲ ခွင့်ပြုမည်
    allow_credentials=True,
    allow_methods=["*"],     # GET, POST, DELETE စသည်တို့ကို အကုန်ခွင့်ပြုမည်
    allow_headers=["*"],     # Token တွေပို့မည့် Headers များကို ခွင့်ပြုမည်
)
# ==========================================
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 🌟 FastAPI App ထဲသို့ Limiter ကို ထည့်သွင်းခြင်း
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 🌟 Router ကို App ထဲသို့ တပ်ဆင်ခြင်း
app.include_router(auth.router)
app.include_router(user_auth.router)
# 🌟 Dashboard API လမ်းကြောင်းကို တပ်ဆင်လိုက်ပါပြီ
app.include_router(spin_wheel.router)
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
