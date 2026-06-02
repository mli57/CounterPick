"""
train_model.py

How it works: 
Trains XGBoost model on output.csv generated from build_features.py
Uses 5-fold stratified CV to get a stable evaluation
Outputs AUC-ROC (can it rank good matchups above bad ones?) and log loss (are the probabilities accurate?)

How to run:
    python src/backend/train_model.py
"""

import pandas as pd
import xgboost as xgb
import joblib
from sklearn.model_selection import StratifiedKFold, cross_val_score

FEATURES = ['cc_delta', 'dmg_mit_delta', 'damage_dealt_delta', 'kills_delta', 'deaths_delta', 'range_delta']

def main():
    df_raw = pd.read_csv("data/output.csv")
    print(f"Raw rows: {len(df_raw)}")
    df = df_raw.dropna() # drop NaN rows
    print(f"Training rows: {len(df)}")

    X = df[FEATURES]
    y = df['win']

    model = xgb.XGBClassifier(
        n_estimators=100,   # number of trees
        max_depth=4,        # max depth per tree 
        learning_rate=0.1,  # how much each tree corrects the previous; linked to n_estimators
        random_state=42
    )

    # each fold trains on 80%, tests on a different 20%, rotated 5 times -> returns one score per fold
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    auc_scores = cross_val_score(model, X, y, cv=cv, scoring='roc_auc')
    logloss_scores = cross_val_score(model, X, y, cv=cv, scoring='neg_log_loss')  # negated by sklearn convention
    print(f"AUC-ROC  (5-fold CV): {auc_scores.mean():.3f} +/- {auc_scores.std():.3f}")
    print(f"Log loss (5-fold CV): {(-logloss_scores).mean():.3f} +/- {logloss_scores.std():.3f}")

    # fit final model on all data
    model.fit(X, y)
    joblib.dump(model, "models/model.pkl")
    print("Model saved to models/model.pkl")

if __name__ == "__main__":
    main()
