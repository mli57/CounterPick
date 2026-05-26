import pandas as pd
import xgboost as xgb
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

def main():
    df_raw = pd.read_csv("data/output.csv")
    print(f"Raw rows: {len(df_raw)}")
    df = df_raw.dropna() # drop NaN rows
    print(f"Training rows: {len(df)}")

    X = df[['cc_delta', 'dmg_mit_delta', 'game_time_delta']]
    y = df['win']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    model = xgb.XGBClassifier( # use classifier because we predict win/loss (1 or 0)
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        random_state=42
    )
    model.fit(X_train, y_train)
    pred_test = model.predict(X_test)
    print(f"Accuracy: {accuracy_score(y_test, pred_test):.3f}")
    joblib.dump(model, "models/model.pkl")

if __name__ == "__main__":
    main()