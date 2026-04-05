import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware 
from app.routes import router as api_router

# 1. 앱 생성 
app = FastAPI(
    title="CYBER-TRADER API v2.0",
    description="React + FastAPI 퀀트 매매 플랫폼용 백엔드",
    version="2.0.0"
)

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# 4. 기본 접속 확인용 루트 경로
@app.get("/")
async def root():
    return {"status": "online", "message": "Cyber-Trader API is running securely!"}

# 5. 직접 실행 시 uvicorn 가동
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=80, 
        reload=True,
        proxy_headers=True,
        forwarded_allow_ips="*"
    )