import pandas as pd
import lightgbm as lgb
import numpy as np
import joblib

# ==========================================
# 1. 데이터 불러오기 및 피처 설정
# ==========================================
print(" 5분봉 단기스윙 양방향 분류 모델 학습 시작...")

df = pd.read_csv("learning_data_5m_with_vol.csv") 

features = [
    'dist_ma20', 'dist_ma60', 
    'rsi', 'rsi_slope','vol_ratio'
]

# ==========================================
# 2. 트리플 배리어 타겟 라벨링 (롱: 1, 숏: 2, 관망: 0)
# ==========================================
FEE_RATE = 0.12     # 수수료 및 슬리피지 (왕복)
TAKE_PROFIT = 0.40  # 익절 목표 (0.5%)
STOP_LOSS = -0.65   # 손절 라인 (-0.3%)

# 최고점과 최저점을 모두 고려한 깐깐한 조건
conditions = [
    # 롱(1): 30분 동안 최저점이 손절선 안 건드리고, 최고점이 익절선 터치
    (df['future_max_ret'] >= TAKE_PROFIT) & (df['future_min_ret'] > STOP_LOSS),
    
    # 숏(2): 30분 동안 최고점이 위로 튀지 않고, 최저점이 숏 익절선(하락) 터치
    (df['future_min_ret'] <= -TAKE_PROFIT) & (df['future_max_ret'] < abs(STOP_LOSS))
]
choices = [1, 2]
df['target_class'] = np.select(conditions, choices, default=0)

print(f"📊 [롱(1) 타점] 비율: {(df['target_class']==1).mean()*100:.2f}%")
print(f"📊 [숏(2) 타점] 비율: {(df['target_class']==2).mean()*100:.2f}%")
print(f"📊 [관망(0) 비율]: {(df['target_class']==0).mean()*100:.2f}%\n")

# ==========================================
# 3. 데이터 분할
# ==========================================
X = df[features]
y = df['target_class']

train_size = int(len(df) * 0.7)
val_size = int(len(df) * 0.15)

X_train, y_train = X.iloc[:train_size], y.iloc[:train_size]
X_val, y_val = X.iloc[train_size:train_size+val_size], y.iloc[train_size:train_size+val_size]
X_test, y_test = X.iloc[train_size+val_size:], y.iloc[train_size+val_size:]

# ==========================================
# 🧠 4. LGBM 다중 분류 모델 (Multi-class)
# ==========================================
model = lgb.LGBMClassifier(
    objective='multiclass',
    num_class=3,            
    n_estimators=500,       # 1000 -> 100: 공부 시간 확 줄여!
    learning_rate=0.01,     
    max_depth=4,            # 5 -> 3: 깊게 생각하지 말고 딱 3번만 쪼개!
    num_leaves=20,           # 31 -> 7: 복잡한 패턴은 다 버려!
    min_child_samples=500, # 100 -> 2000: 비슷한 데이터가 2000개는 모여야 패턴으로 인정해!
    random_state=42,
    verbosity=-1,
    class_weight='balanced' 
)

print("🧠 양방향 패턴 학습 중...")
model.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],
    eval_metric='multi_logloss',
    callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)]
)

# ==========================================
# 5. 양방향 시뮬레이션 (보고서 로직 변경)
# ==========================================
y_pred_prob = model.predict_proba(X_test)
prob_long = y_pred_prob[:, 1]
prob_short = y_pred_prob[:, 2]

# 컷오프 설정 (롱과 숏의 임계값을 분리)
PROB_LONG_THRESHOLD = 0.55
PROB_SHORT_THRESHOLD = 0.55

long_idx = np.where(prob_long >= PROB_LONG_THRESHOLD)[0]
short_idx = np.where(prob_short >= PROB_SHORT_THRESHOLD)[0]

def get_report(indices, side="LONG"):
    if len(indices) == 0:
        print(f"⚠️ {side}: 타점 없음 (기준 확률이 너무 높음)")
        return 0
    
    # 예측한 인덱스의 실제 정답 클래스 가져오기
    actual_classes = df.loc[X_test.index, 'target_class'].iloc[indices]
    
    # 롱은 1을 맞춰야 승리, 숏은 2를 맞춰야 승리
    target_val = 1 if side == "LONG" else 2
    win_rate = (actual_classes == target_val).mean() * 100
    
    # 보수적인 수익 계산: 승리하면 TP만큼 먹고, 실패(0이나 반대 방향)하면 모조리 손절 쳤다고 가정
    win_prob = win_rate / 100
    avg_profit = (win_prob * TAKE_PROFIT) + ((1 - win_prob) * STOP_LOSS) - FEE_RATE
    total_profit = avg_profit * len(indices)
    
    print(f"[{side}] 진입: {len(indices):4d}번 | 승률: {win_rate:5.2f}% | 예상 누적수익: {total_profit:7.4f}%")
    return total_profit

print(f"\n--- 실전 보고서 (진입 확률 롱: {PROB_LONG_THRESHOLD*100}% / 숏: {PROB_SHORT_THRESHOLD*100}% 이상 시) ---")
l_res = get_report(long_idx, "LONG")
s_res = get_report(short_idx, "SHORT")
print(f"💵 합계 누적 수익률: {l_res + s_res:.4f}%")

# ==========================================
# 6. 모델 저장 및 지표 확인
# ==========================================
joblib.dump(model, 'trading_model_5m_multi.pkl')

importances = pd.DataFrame({'feature': features, 'importance': model.feature_importances_})
print("\n🔥 지표 중요도 ")
print(importances.sort_values(by='importance', ascending=False))