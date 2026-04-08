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
timeframe = "5m"        
days_to_collect = 365

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
            
            # 5분봉이므로 5분(5 * 60 * 1000) 전까지만 가져오고 종료
            if ohlcv[-1][0] >= int(time.time() * 1000) - (5 * 60 * 1000): break
            
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
    df['rsi_slope'] = df['rsi'].diff(3) 
    df['rsi_accel'] = df['rsi'].diff(1)
    
    # 2. 단기(100분) 및 중기(5시간) 이동평균선 이격도
    df['ma20'] = ta.sma(df['close'], length=20)
    df['ma60'] = ta.sma(df['close'], length=60)
    
    df['dist_ma20'] = ((df['close'] - df['ma20']) / df['ma20']) * 100 
    df['dist_ma60'] = ((df['close'] - df['ma60']) / df['ma60']) * 100 
    
    # --- [Volume Features (과거 완성된 데이터이므로 있는 그대로 비율만 계산)] ---
    df['vol_ma20'] = ta.sma(df['vol'], length=20)
    df['vol_ratio'] = (df['vol'] / df['vol_ma20']).clip(upper=10)
    df['vol_slope'] = (df['vol'].diff(1) / df['vol_ma20']).clip(lower=-10, upper=10)

    # --- [Target: 60분 뒤 위아래 변동폭] ---
    future_period = 24 
    df['future_max_ret'] = (df['high'].rolling(window=future_period).max().shift(-future_period) / df['close'] - 1) * 100
    df['future_min_ret'] = (df['low'].rolling(window=future_period).min().shift(-future_period) / df['close'] - 1) * 100
    
    df.dropna(inplace=True)
    return df

if __name__ == "__main__":
    # 1. 데이터 수집 실행
    raw_df = collect_data()
    
    # 2. 피처 추가 및 정답지 생성
    processed_df = add_features_and_target(raw_df)
    
    # 3. CSV 파일로 저장 (학습용)
    processed_df.to_csv("learning_data_5m_vol2.csv")
    
    print("-" * 30)
    print(f"✅ 초단타용 데이터 준비 완료! (모든 기준 5분)")
    print(f"📂 파일명: learning_data_5m_vol2.csv")
    print(f"📊 총 데이터 행 수: {len(processed_df)}행")
    print("-" * 30)