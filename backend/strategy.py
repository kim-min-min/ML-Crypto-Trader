import pandas as pd
import pandas_ta as ta
import joblib
import config
from datetime import datetime, timezone

class TradingStrategy:
    def __init__(self, model_path):
        self.model = joblib.load(model_path)
        # 모델 학습 시 사용한 피처 리스트로 정확히 맞춤
        self.features = [
            'dist_ma5', 'dist_ma10', 'rsi', 'rsi_slope', 'vol_ratio'
        ]

    def predict_proba(self, exchange_instance):
        # 데이터 수집 (지표 계산을 위해 넉넉히 100개)
        ohlcv = exchange_instance.ex.fetch_ohlcv(config.SYMBOL, timeframe=config.TIMEFRAME, limit=100)
        df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
        
        for col in ['open', 'high', 'low', 'close', 'vol']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 1. 타임스탬프 변환 및 경과 시간 계산
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        candle_start_time = df['ts'].iloc[-1]
        
        elapsed_seconds = (now_utc - candle_start_time).total_seconds()
        elapsed_seconds = max(1, min(300, elapsed_seconds)) # 1초 미만 방지
        
        # 2. 거래량 보정 (라이브 캔들)
        live_vol = df['vol'].iloc[-1]
        projected_vol = live_vol * (60 / elapsed_seconds)
        df.loc[df.index[-1], 'vol'] = projected_vol

        # 3. 네가 바꾼 최신 피처 계산 로직 완벽 적용
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['rsi_slope'] = df['rsi'].diff(5) 
        
        df['ma5'] = ta.sma(df['close'], length=5)
        df['ma10'] = ta.sma(df['close'], length=10)
        
        df['dist_ma5'] = ((df['close'] - df['ma5']) / df['ma5']) * 100
        df['dist_ma10'] = ((df['close'] - df['ma10']) / df['ma10']) * 100
        
        df['vol_ma10'] = ta.sma(df['vol'], length=10)
        df['vol_ratio'] = (df['vol'] / df['vol_ma10']).clip(upper=10)
        
        # 4. 데이터 정제 및 최종 입력 데이터 추출
        df.dropna(inplace=True)
        
        # 모델에 넣을 때는 정의된 컬럼들만 순서대로 추출
        last_row = df.iloc[[-1]]
        x_input = last_row[self.features]
        
        # --- [예측 수행] ---
        probs = self.model.predict_proba(x_input)[0]
        
        # 이진 분류 모델: probs[0] = 숏(0) 확률, probs[1] = 롱(1) 확률
        pred_short = probs[0]
        pred_long = probs[1]
        
        return pred_short, pred_long, elapsed_seconds