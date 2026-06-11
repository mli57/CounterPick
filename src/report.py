"""
report.py
Generates the graphs in readme.md using matplotlib

How to run:
    python src/report.py 

Optional flags:    
    --db (eg test.db)
    --role (top, mid, bot, etc)
    --top (# of champs in heatmap)
    --out (output dir)
"""

import argparse
import os
import sqlite3
import sys

import joblib
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_curve, auc
import xgboost as xgb

plt.style.use("dark_background")
matplotlib.rcParams.update({"font.size": 10, "grid.linewidth": 0.6})

FEATURES = [
    "cc_delta", "dmg_mit_delta", "damage_dealt_delta", "kills_delta", "deaths_delta", "range_delta",
    "gold_14_delta", "xp_14_delta", "cs_lane_14_delta", "level_14_delta",
    "gold_10_delta", "xp_10_delta", "cs_lane_10_delta", "level_10_delta",
]
FEATURE_LABELS = [
    "CC time delta", "Dmg mitigated delta", "Dmg dealt delta", "Kills delta", "Deaths delta", "Range delta",
    "Gold @14 delta", "XP @14 delta", "CS @14 delta", "Level @14 delta",
    "Gold @10 delta", "XP @10 delta", "CS @10 delta", "Level @10 delta",
]
BLUE  = "steelblue"
GREEN = "mediumseagreen"
RED   = "indianred"


def load_training_data(csv_path: str = "data/output.csv"):
    df = pd.read_csv(csv_path).dropna()
    return df[FEATURES].values, df["win"].values


def get_top_champions(conn, role, n):
    patch = conn.execute("SELECT MAX(patch) FROM champion_tags").fetchone()[0]
    rows = conn.execute("""
        SELECT cm.champion_name
        FROM champion_tags ct
        JOIN champion_meta cm USING (champion_id)
        JOIN champion_role_majority crm ON crm.champion_id = ct.champion_id AND crm.patch = ct.patch
        WHERE ct.role = ? AND ct.patch = ? AND crm.majority_role = ?
        ORDER BY ct.avg_kills DESC
        LIMIT ?
    """, (role, patch, role, n)).fetchall()
    return [r[0] for r in rows]


def build_heatmap_matrix(conn, model, champions, role):
    sys.path.insert(0, "src")
    from predict import predict_matchup

    num_champions = len(champions)
    win_prob_matrix = np.full((num_champions, num_champions), np.nan)
    for i, champion in enumerate(champions):
        for j, opponent in enumerate(champions):
            if i == j:
                win_prob_matrix[i, j] = 0.5
                continue
            try:
                win_prob_matrix[i, j] = predict_matchup(conn, model, champion, opponent, role)["win_probability"]
            except Exception:
                win_prob_matrix[i, j] = np.nan
    return win_prob_matrix


def save_roc(features, labels, out_path):
    fig, ax = plt.subplots(figsize=(7, 5))

    cross_val = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    fold_tprs, fold_aucs = [], []
    shared_fpr = np.linspace(0, 1, 200)

    for train_idx, test_idx in cross_val.split(features, labels):
        fold_model = xgb.XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42)
        fold_model.fit(features[train_idx], labels[train_idx])
        false_pos_rate, true_pos_rate, _ = roc_curve(labels[test_idx], fold_model.predict_proba(features[test_idx])[:, 1])
        interpolated_tpr = np.interp(shared_fpr, false_pos_rate, true_pos_rate)
        interpolated_tpr[0] = 0.0
        fold_tprs.append(interpolated_tpr)
        fold_aucs.append(auc(false_pos_rate, true_pos_rate))
        ax.plot(false_pos_rate, true_pos_rate, lw=1, alpha=0.5, color="red")

    mean_tpr = np.mean(fold_tprs, axis=0)
    mean_tpr[-1] = 1.0
    ax.plot(shared_fpr, mean_tpr, color=BLUE, lw=2,
            label=f"Mean AUC = {np.mean(fold_aucs):.3f} ± {np.std(fold_aucs):.3f}")
    ax.fill_between(shared_fpr,
                    mean_tpr - np.std(fold_tprs, axis=0),
                    mean_tpr + np.std(fold_tprs, axis=0),
                    alpha=0.35, color=BLUE)
    ax.plot([0, 1], [0, 1], "--", color="gray", lw=1)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC — 5-fold CV")
    ax.legend(fontsize=9)
    ax.grid(True)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)

    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def save_feature_importance(model, out_path):
    fig, ax = plt.subplots(figsize=(7, 5))

    booster = model.get_booster()
    booster.feature_names = FEATURE_LABELS
    xgb.plot_importance(booster, ax=ax, importance_type="gain",
                        title="Feature Importance", xlabel="Feature importance (gain)",
                        show_values=True, color=BLUE)
    for text in ax.texts:
        try:
            text.set_text(f"{float(text.get_text()):.2f}")
        except ValueError:
            pass

    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def save_heatmap(win_prob_matrix, champions, role, out_path):
    fig, ax = plt.subplots(figsize=(10, 8))

    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("wr", [RED, "black", GREEN])
    heatmap_image = ax.imshow(win_prob_matrix, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    plt.colorbar(heatmap_image, ax=ax, fraction=0.03, pad=0.02, label="Win probability")

    ax.set_xticks(range(len(champions)))
    ax.set_yticks(range(len(champions)))
    ax.set_xticklabels(champions, rotation=45, ha="right", fontsize=7)
    ax.set_yticklabels(champions, fontsize=7)
    ax.set_title(f"{role} matchup win probability  (row beats column)")
    ax.set_xlabel("Opponent")
    ax.set_ylabel("Champion")

    if len(champions) <= 15:
        for row in range(len(champions)):
            for col in range(len(champions)):
                win_prob = win_prob_matrix[row, col]
                if not np.isnan(win_prob):
                    ax.text(col, row, f"{win_prob:.0%}", ha="center", va="center",
                            fontsize=6, color="white")

    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db",   default="test.db")
    parser.add_argument("--role", default="TOP")
    parser.add_argument("--top",  type=int, default=15, help="Number of champions in heatmap")
    parser.add_argument("--out",  default="images", help="Output directory for graph PNGs")
    return parser.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.out, exist_ok=True)

    print("Loading model and training data…")
    model = joblib.load("models/model.pkl")
    features, labels = load_training_data("data/output.csv")

    conn      = sqlite3.connect(args.db)
    champions = get_top_champions(conn, args.role, args.top)
    if not champions:
        print(f"No champions found for role {args.role}.")
        return

    print("Plotting ROC curves (re-runs CV)…")
    save_roc(features, labels, os.path.join(args.out, "roc.png"))
    print("  -> roc.png")

    save_feature_importance(model, os.path.join(args.out, "feature_importance.png"))
    print("  -> feature_importance.png")

    print(f"Building heatmap for {len(champions)} {args.role} champions…")
    win_prob_matrix = build_heatmap_matrix(conn, model, champions, args.role)
    save_heatmap(win_prob_matrix, champions, args.role,
                 os.path.join(args.out, f"heatmap_{args.role}.png"))
    print(f"  -> heatmap_{args.role}.png")

    print(f"Done. All graphs saved to {args.out}/")


if __name__ == "__main__":
    main()
