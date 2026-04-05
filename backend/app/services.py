import json
import os
import aiofiles
from fastapi import HTTPException

class TradingService:
    def __init__(self):
        self.status_file = 'bot_status.json'
        self.history_file = 'trade_history.csv'

    async def get_dashboard_data(self):
        if not os.path.exists(self.status_file):
            return {"message": "봇이 아직 데이터를 생성하지 않았습니다."}

        try:
            # 비동기로 파일 읽기 (동접자가 많아도 여기서 안 막힘)
            async with aiofiles.open(self.status_file, mode='r') as f:
                data = await f.read()
                bot_info = json.loads(data)
            
            return bot_info
            
        except Exception as e:
            print(f"❌ JSON 읽기 오류: {e}")
            raise HTTPException(status_code=500, detail="데이터 읽기 실패")

    async def get_recent_trades(self, limit=10):
        """매매 기록도 봇이 써준 CSV에서 읽기만 함"""
        pass

trading_service = TradingService()