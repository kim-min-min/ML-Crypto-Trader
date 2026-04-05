import pandas as pd
import pandas_ta as ta
import joblib
import config
from datetime import datetime, timezone

class TradingStrategy:
    def __init__(self, model_path):
        self.model = joblib.load(model_path)
        self.features = [
            'dist_ma20', 'dist_ma60', 'rsi', 'rsi_slope', 'vol_ratio'
        ]

    def predict_proba(self, exchange_instance):
        # 데이터 수집 (지표 계산을 위해 넉넉히 100개)
        ohlcv = exchange_instance.ex.fetch_ohlcv(config.SYMBOL, timeframe=config.TIMEFRAME, limit=100)
        df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
        
        # 1. 타임스탬프 변환 및 경과 시간 계산
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        candle_start_time = df['ts'].iloc[-1]
        
        elapsed_seconds = (now_utc - candle_start_time).total_seconds()
        elapsed_seconds = max(1, min(300, elapsed_seconds)) # 1초 미만 방지
        
        live_vol = df['vol'].iloc[-1]
        projected_vol = live_vol * (300 / elapsed_seconds)
        
        # 마지막 행의 거래량을 보정된 값으로 교체
        df.loc[df.index[-1], 'vol'] = projected_vol

        # 3. 피처 계산
        # 가격 지표
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['rsi_slope'] = df['rsi'].diff(3)
        
        df['ma20'] = ta.sma(df['close'], length=20)
        df['ma60'] = ta.sma(df['close'], length=60)
        df['dist_ma20'] = ((df['close'] - df['ma20']) / df['ma20']) * 100 
        df['dist_ma60'] = ((df['close'] - df['ma60']) / df['ma60']) * 100
        
        # 거래량 지표 (보정된 projected_vol이 적용된 상태)
        df['vol_ma20'] = ta.sma(df['vol'], length=20)
        df['vol_ratio'] = (df['vol'] / df['vol_ma20']).clip(upper=10)
        
        # 4. 데이터 정제 및 최종 입력 데이터 추출
        df.dropna(inplace=True)
        
        # 모델에 넣을 때는 딱 'self.features'에 정의된 컬럼들만 순서대로 추출
        last_row = df.iloc[[-1]]
        x_input = last_row[self.features]
        
        # --- [예측 수행] ---
        probs = self.model.predict_proba(x_input)[0]
        
        # probs[1]: 롱 확률, probs[2]: 숏 확률
        return probs[1], probs[2], elapsed_seconds