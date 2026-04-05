import ccxt
import math
import config

class BybitHelper:
    def __init__(self):
        self.ex = ccxt.bybit({
            'apiKey': config.API_KEY,
            'secret': config.SECRET_KEY,
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'}
        })

    def set_leverage(self):
        try:
            self.ex.set_leverage(config.LEVERAGE, config.SYMBOL)
        except Exception as e:
            print(f"⚠️ 레버리지 설정 중 참고: {e}")

    def get_balance(self):
        try:
            balance = self.ex.fetch_balance()
            return float(balance['total'].get('USDT', 0))
        except Exception as e:
            print(f"❌ 잔고 조회 실패: {e}")
            return 0.0

    def get_position_details(self):
        try:
            positions = self.ex.fetch_positions([config.SYMBOL])
            details = {'side': None, 'size': 0, 'entry_price': 0, 'pnl_pct': 0}
            
            for p in positions:
                # CCXT 표준 필드명을 사용합니다.
                size = float(p.get('contracts') or 0) 
                
                if size > 0:
                    details['side'] = p.get('side')
                    details['size'] = size
                    details['entry_price'] = float(p.get('entryPrice') or 0)
                    
                    upnl = float(p.get('unrealizedPnl') or 0)
                    leverage = float(p.get('leverage') or 1)  
                    
                    entry_value = size * details['entry_price']
                    
                    if entry_value > 0:
                        details['pnl_pct'] = (upnl / (entry_value / leverage)) * 100
                    else:
                        details['pnl_pct'] = 0
                    
                    break
            return details
        except Exception as e:
            print(f"❌ 포지션 체크 중 오류: {e}")
            return {'side': None, 'size': 0, 'entry_price': 0, 'pnl_pct': 0}

    def calculate_amount(self, balance):
        try:
            ticker = self.ex.fetch_ticker(config.SYMBOL)
            price = ticker['last']
            if price <= 0: return 0  # 0 나누기 방지
            
            amt = (balance * config.RATIO * config.LEVERAGE) / price
            return math.floor(amt * 1000) / 1000
        except Exception as e:
            print(f"❌ 수량 계산 실패: {e}")
            return 0

    def execute_order(self, side, position_idx, amount):
        if amount <= 0: return None
        
        params = {'positionIdx': position_idx} # 1: Long, 2: Short
        try:
            if side == 'buy':
                res = self.ex.create_market_buy_order(config.SYMBOL, amount, params)
            else:
                res = self.ex.create_market_sell_order(config.SYMBOL, amount, params)
            return res
        except Exception as e:
            print(f"❌ 주문 실행 실패: {e}")
            return None

    def close_all_positions(self):
        pos = self.get_position_details()
        
        current_side = pos['side'].lower() if pos['side'] else None
        
        if pos['size'] > 0:
            side = 'sell' if current_side == 'long' else 'buy'
            idx = 1 if current_side == 'long' else 2
            
            print(f"DEBUG: 현재 {current_side} 포지션 종료 시도 -> 방향: {side}, IDX: {idx}")
            
            res = self.execute_order(side, idx, pos['size'])
            
            if res:
                print(f"📢 모든 {pos['side']} 포지션 종료 완료")
            return res