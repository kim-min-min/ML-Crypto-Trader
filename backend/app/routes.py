from fastapi import APIRouter, HTTPException
from app.services import trading_service
from datetime import datetime

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard():
    try:
        data = await trading_service.get_dashboard_data() 
        return data
    except Exception as e:
        print(f"Dashboard Error: {e}") 
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_trade_history():
    try:
        history = await trading_service.get_recent_trades(limit=10) 
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail="매매 기록을 불러오는 중 오류 발생")

@router.post("/bot/control")
async def control_bot(action: str):
    result = await trading_service.control_bot_process(action)
    return {"status": "success", "action": action, "result": result}