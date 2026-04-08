import ccxt
import pandas as pd
import pandas_ta as ta
import time
from datetime import datetime, timedelta

# 1. 초기 설정
exchange = ccxt.bybit({
    'options': {'defaultType': 'swap'} 
})
symbol = "BTC/USDT"
timeframe = "1m"        
days_to_collect = 180

# 2. 데이터 수집 함수
def collect_data():
    since = int((datetime.now() - timedelta(days=days_to_collect)).timestamp() * 1000)
    all_ohlcv = []
    
    print(f"🚀 {timeframe} 데이터 수집 시작 (최근 {days_to_collect}일)...")
    
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, 1000)
            if not ohlcv: break
            
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 1
            
            print(f"📦 수집 중: {datetime.fromtimestamp(ohlcv[-1][0]/1000)}")
            

            if ohlcv[-1][0] >= int(time.time() * 1000) - (1 * 60 * 1000): break # 1분 전 데이터까지 수집
            
            time.sleep(0.1)
        except Exception as e:
            print(f"⚠️ 에러 발생: {e}, 5초 뒤 재시도...")
            time.sleep(5)
    
    df = pd.DataFrame(all_ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    df.set_index('ts', inplace=True)
    return df

# 3. AI 피처 생성
def add_features_and_target(df):
    for col in ['open', 'high', 'low', 'close', 'vol']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # --- [Price & Trend Features] ---
    # 1. RSI 및 단기 꺾임, 가속도 (Stoch RSI 대체)
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['rsi_slope'] = df['rsi'].diff(5) 
    
    # 2. 이동평균선 이격도
    df['ma5'] = ta.sma(df['close'], length=5)
    df['ma10'] = ta.sma(df['close'], length=10)
    
    df['dist_ma5'] = ((df['close'] - df['ma5']) / df['ma5']) * 100
    df['dist_ma10'] = ((df['close'] - df['ma10']) / df['ma10']) * 100
    
    # --- [Volume Features (과거 완성된 데이터이므로 있는 그대로 비율만 계산)] ---
    df['vol_ma10'] = ta.sma(df['vol'], length=10)
    df['vol_ratio'] = (df['vol'] / df['vol_ma10']).clip(upper=10)

    # --- [Target: 10분 뒤 위아래 변동폭] ---
    future_period = 10 
    df['future_max_ret'] = (df['high'].rolling(window=future_period).max().shift(-future_period) / df['close'] - 1) * 100
    df['future_min_ret'] = (df['low'].rolling(window=future_period).min().shift(-future_period) / df['close'] - 1) * 100

    # 2. N분 뒤의 종가 수익률
    df['future_close_ret'] = (df['close'].shift(-future_period) / df['close'] - 1) * 100
    
    df.dropna(inplace=True)
    return df

if __name__ == "__main__":
    # 1. 데이터 수집 실행
    raw_df = collect_data()
    
    # 2. 피처 추가 및 정답지 생성
    processed_df = add_features_and_target(raw_df)
    
    # 3. CSV 파일로 저장 (학습용)
    processed_df.to_csv("learning_data_1m_with_vol.csv")
    
    print("-" * 30)
    print(f"✅ 초단타용 데이터 준비 완료!")
    print(f"📂 파일명: learning_data_1m_with_vol.csv")
    print(f"📊 총 데이터 행 수: {len(processed_df)}행")
    print("-" * 30)