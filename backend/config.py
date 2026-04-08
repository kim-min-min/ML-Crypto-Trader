import os
from dotenv import load_dotenv

load_dotenv()

# API 설정
API_KEY = os.getenv('BYBIT_API_KEY')
SECRET_KEY = os.getenv('BYBIT_SECRET_KEY')

# 매매 설정
SYMBOL = 'BTC/USDT:USDT'
TIMEFRAME = '1m'          
LEVERAGE = 2             
RATIO = 0.98            


LONG_THRESHOLD = 0.56 
SHORT_THRESHOLD = 0.58
STOP_LOSS = -0.10        
TRAILING_START = 0.2    
TRAILING_DROP = 0.1    