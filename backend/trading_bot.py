import time
import json
from datetime import datetime
from exchange_helper import BybitHelper # 경로 확인 필수!
from strategy import TradingStrategy
import config
import pandas as pd
import os


# 매매 기록 저장 함수
def log_trade(side, amount, price, pnl=0):
    file_name = 'trade_history.csv'
    new_data = {
        'timestamp': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        'side': [side],
        'amount': [amount],
        'price': [price],
        'pnl': [pnl]
    }
    df = pd.DataFrame(new_data)
    
    if not os.path.exists(file_name):
        df.to_csv(file_name, index=False, mode='w', encoding='utf-8-sig')
    else:
        df.to_csv(file_name, index=False, mode='a', header=False, encoding='utf-8-sig')

def run_bot():
    bot = BybitHelper()
    ai = TradingStrategy('trading_model_1m_binary.pkl')
    bot.set_leverage()

    
    print("🚀 CYBER-TRADER 엔진 가동!")

    while True:
        try:
            # 1. 잔고 및 포지션 정보 한 번에 가져오기
            current_balance = bot.get_balance()
            pos = bot.get_position_details() 
            curr_pnl = pos['pnl_pct']
            
            # 2. [수정됨] AI 예측 (바이너리라 확률이 2개만 나옴)
            probs = ai.predict_proba(bot)
            pred_short = probs[0]
            pred_long = probs[1]
            
            now_dt = datetime.now()
            now_str = now_dt.strftime('%H:%M:%S')

            # 3. 리액트 공유용 JSON 데이터 조립 (이건 그대로 둬도 됨)
            status_data = {
                "balance": float(current_balance),
                "side": pos['side'] if pos['side'] else "IDLE",
                "size": float(pos['size']),
                "entry_price": float(pos['entry_price']),
                "last_pnl": float(curr_pnl),
                "pred_long": float(pred_long),
                "pred_short": float(pred_short),
                "timestamp": now_dt.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open('bot_status.json', 'w') as f:
                json.dump(status_data, f)
            
            print(f"[{now_str}] 잔고: {current_balance} | 롱: {pred_long:.3f} | 숏: {pred_short:.3f} - 분석 중...")

            # ---------------------------------------------------------
            # 4. 매매 로직 
            # ---------------------------------------------------------
            if pos['size'] == 0:
                
                if pred_long >= config.LONG_THRESHOLD:
                    amt = bot.calculate_amount(current_balance)
                    res = bot.execute_order('buy', 1, amt) 
                    if res: 
                        log_trade('LONG_ENTRY', amt, res.get('average', 0))
                        print(f"[{now_str}] 🔥 LONG 진입 완료 & CSV 기록")
                    
                elif pred_short >= config.SHORT_THRESHOLD:
                    amt = bot.calculate_amount(current_balance)
                    res = bot.execute_order('sell', 2, amt) 
                    if res: 
                        log_trade('SHORT_ENTRY', amt, res.get('average', 0))
                        print(f"[{now_str}] 📉 SHORT 진입 완료 & CSV 기록")

            else:
                # 차트 기준 설정값에 레버리지를 곱해서 '실제 ROE 컷오프'로 변환
                actual_stop_loss = config.STOP_LOSS * config.LEVERAGE
                actual_take_profit = config.TAKE_PROFIT * config.LEVERAGE # 0.3 * 레버리지

                # 1. 기계적 손절 (-0.1% * 레버리지)
                if curr_pnl <= actual_stop_loss:
                    res = bot.close_all_positions()
                    if res:
                        log_trade('LOSS_CUT', pos['size'], res.get('average', 0), pnl=curr_pnl)
                        print(f"[{now_str}] 🛡️ 손절 완료 (ROE: {curr_pnl:.2f}%)")
                    continue

                # 2. 기계적 익절 (0.3% * 레버리지)
                elif curr_pnl >= actual_take_profit:
                    res = bot.close_all_positions()
                    if res:
                        log_trade('TAKE_PROFIT', pos['size'], res.get('average', 0), pnl=curr_pnl)
                        print(f"[{now_str}] 💎 익절 완료 (ROE: {curr_pnl:.2f}%)")
                    continue

            time.sleep(10)

        except Exception as e:
            print(f"❌ 에러: {e}")
            time.sleep(10)


if __name__ == "__main__":
    run_bot()