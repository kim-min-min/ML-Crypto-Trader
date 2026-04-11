import pandas as pd
import lightgbm as lgb
import numpy as np
import joblib

# ==========================================
# 1. 데이터 불러오기 및 피처 설정
# ==========================================
print("📂 1분봉 단기스윙 양방향(Binary) 분류 모델 학습 시작...")

df = pd.read_csv("learning_data_1m_with_vol.csv") 

features = [
    'dist_ma5', 'dist_ma10', 
    'rsi', 'rsi_slope','vol_ratio'
]

# ==========================================
# 2. 이진 분류 타겟 라벨링 (롱: 1, 숏: 0) 
# ==========================================
FEE_RATE = 0.12 
TAKE_PROFIT = 0.30  
STOP_LOSS = -0.10

# 일단 전부 버릴 쓰레기(-1)로 세팅
df['target_class'] = -1 

# 롱(1): 위로 확실히 튄 놈 (손절 안 당함)
df.loc[(df['future_max_ret'] >= TAKE_PROFIT) & (df['future_min_ret'] > STOP_LOSS), 'target_class'] = 1

# 숏(0): 아래로 확실히 꽂힌 놈 (위로 안 튐)
df.loc[(df['future_min_ret'] <= -TAKE_PROFIT) & (df['future_max_ret'] < abs(STOP_LOSS)), 'target_class'] = 0

# 🌟 [핵심] 이도 저도 아닌 횡보(-1) 데이터는 아예 훈련장에서 쫓아낸다!
df = df[df['target_class'] != -1]

print(f"📊 [퓨어 롱(1)] 비율: {(df['target_class']==1).mean()*100:.2f}%")
print(f"📊 [퓨어 숏(0)] 비율: {(df['target_class']==0).mean()*100:.2f}%\n")

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
# 🧠 4. LGBM 이진 분류 모델 (Binary)
# ==========================================
model = lgb.LGBMClassifier(
    objective='binary',
    n_estimators=500,       
    learning_rate=0.01,     
    max_depth=4,           
    num_leaves=20,          
    min_child_samples=500,  
    random_state=42,
    verbosity=-1, 
)

print("🧠 양방향 이진 패턴 학습 중...")
model.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],
    eval_metric='binary_logloss', # [수정됨] multi_logloss -> binary_logloss
    callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)]
)

# ==========================================
# 5. 양방향 시뮬레이션 (보고서 로직 변경)
# ==========================================
y_pred_prob = model.predict_proba(X_test)
prob_short = y_pred_prob[:, 0] # [수정됨] 0(숏)일 확률
prob_long = y_pred_prob[:, 1]  # [수정됨] 1(롱)일 확률

# [수정됨] 이진 분류니까 확실하게 60% 이상일 때만 진입하도록 컷오프 상향
PROB_LONG_THRESHOLD = 0.60
PROB_SHORT_THRESHOLD = 0.65

long_idx = np.where(prob_long >= PROB_LONG_THRESHOLD)[0]
short_idx = np.where(prob_short >= PROB_SHORT_THRESHOLD)[0]

def get_report(indices, side="LONG"):
    if len(indices) == 0:
        print(f"⚠️ {side}: 타점 없음 (기준 확률이 너무 높음)")
        return 0
    
    # 예측한 인덱스의 실제 정답 클래스 가져오기
    actual_classes = df.loc[X_test.index, 'target_class'].iloc[indices]
    
    # [수정됨] 롱은 1을 맞춰야 승리, 숏은 0을 맞춰야 승리
    target_val = 1 if side == "LONG" else 0
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
joblib.dump(model, 'trading_model_1m_binary.pkl') # [수정됨] 이름 변경

importances = pd.DataFrame({'feature': features, 'importance': model.feature_importances_})
print("\n🔥 지표 중요도 ")
print(importances.sort_values(by='importance', ascending=False))