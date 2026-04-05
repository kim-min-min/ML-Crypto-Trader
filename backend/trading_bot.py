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
    ai = TradingStrategy('trading_model_5m_multi.pkl')
    bot.set_leverage()

    highest_profit = 0
    is_trailing = False
    
    print("🚀 CYBER-TRADER 엔진 가동!")

    while True:
        try:
            # 1. 잔고 및 포지션 정보 한 번에 가져오기 (API 호출 최적화)
            current_balance = bot.get_balance()
            pos = bot.get_position_details() 
            curr_pnl = pos['pnl_pct']
            
            # 2. AI 예측
            pred_long, pred_short, _ = ai.predict_proba(bot)
            
            now_dt = datetime.now()
            now_str = now_dt.strftime('%H:%M:%S')

            # 3. 리액트 공유용 JSON 데이터 조립
            status_data = {
                "balance": float(current_balance),
                "side": pos['side'] if pos['side'] else "IDLE",
                "size": float(pos['size']),
                "entry_price": float(pos['entry_price']),
                "last_pnl": float(curr_pnl),
                "pred_long": float(pred_long),
                "pred_short": float(pred_short),
                "highest_profit": float(highest_profit),
                "is_trailing": bool(is_trailing),
                "timestamp": now_dt.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            
            with open('bot_status.json', 'w') as f:
                json.dump(status_data, f)
            
            print(f"[{now_str}] 잔고: {current_balance} | 롱: {pred_long:.3f} | 숏: {pred_short:.3f} - 분석 중...")

            # ---------------------------------------------------------
            # 4. 매매 로직 (CSV 저장 추가)
            # ---------------------------------------------------------
            if pos['size'] == 0:
                highest_profit = 0
                is_trailing = False
                
                if pred_long >= config.ENTRY_THRESHOLD:
                    amt = bot.calculate_amount(current_balance)
                    res = bot.execute_order('buy', 1, amt) # 롱 진입
                    if res: # ⭐ 주문 성공 시 기록
                        # res.get('average')는 실제 체결가입니다.
                        log_trade('LONG_ENTRY', amt, res.get('average', 0))
                        print(f"[{now_str}] 🔥 LONG 진입 완료 & CSV 기록")
                    
                elif pred_short >= config.ENTRY_THRESHOLD:
                    amt = bot.calculate_amount(current_balance)
                    res = bot.execute_order('sell', 2, amt) # 숏 진입
                    if res: # ⭐ 주문 성공 시 기록
                        log_trade('SHORT_ENTRY', amt, res.get('average', 0))
                        print(f"[{now_str}] 📉 SHORT 진입 완료 & CSV 기록")

            else:
                # 강제 손절
                if curr_pnl <= config.STOP_LOSS:
                    res = bot.close_all_positions() # 모든 포지션 종료
                    if res:
                        log_trade('LOSS_CUT', pos['size'], res.get('average', 0), pnl=curr_pnl)
                        print(f"[{now_str}] 🛡️ 손절 완료 & CSV 기록")
                    continue

                if curr_pnl > highest_profit:
                    highest_profit = curr_pnl

                if not is_trailing and curr_pnl >= config.TRAILING_START:
                    is_trailing = True

                # 익절 실행 (트레일링 스탑)
                if is_trailing:
                    drawdown = highest_profit - curr_pnl
                    if drawdown >= config.TRAILING_DROP:
                        res = bot.close_all_positions() # 모든 포지션 종료
                        if res:
                            log_trade('TAKE_PROFIT', pos['size'], res.get('average', 0), pnl=curr_pnl)
                            print(f"[{now_str}] 💎 익절 완료 & CSV 기록")

            time.sleep(10)

        except Exception as e:
            print(f"❌ 에러: {e}")
            time.sleep(10)


if __name__ == "__main__":
    run_bot()