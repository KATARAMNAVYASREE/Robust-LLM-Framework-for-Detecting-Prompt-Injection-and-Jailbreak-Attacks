
import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "ml" / "artifacts" / "robustness_predictions.csv"
OUTPUT_PATH = ROOT / "ml" / "artifacts" / "threshold_analysis.json"


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Predictions file not found: {CSV_PATH}\n"
            "Run python ml\\evaluate_robustness.py first."
        )

    df = pd.read_csv(CSV_PATH)

    required = {
        "expected_label",
        "ml_attack_probability",
        "id",
        "text",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"CSV is missing required columns: {sorted(missing)}"
        )

    if df.empty:
        raise ValueError("The predictions CSV contains no rows.")

    df["expected_label"] = pd.to_numeric(
        df["expected_label"], errors="raise"
    ).astype(int)

    df["ml_attack_probability"] = pd.to_numeric(
        df["ml_attack_probability"], errors="raise"
    )

    y_true = df["expected_label"].to_numpy()
    probabilities = df["ml_attack_probability"].to_numpy()

    results = []

    print(f"Test examples: {len(df)}")
    print("\nTHRESHOLD COMPARISON")
    print("-" * 75)
    print(
        f"{'Threshold':>9} {'Accuracy':>9} {'Precision':>10} "
        f"{'Recall':>8} {'F1':>8} {'FP':>5} {'FN':>5}"
    )

    thresholds = [
        0.50, 0.55, 0.60, 0.65, 0.70,
        0.75, 0.80, 0.85, 0.90,
    ]

    for threshold in thresholds:
        y_pred = (probabilities >= threshold).astype(int)

        tn, fp, fn, tp = confusion_matrix(
            y_true, y_pred, labels=[0, 1]
        ).ravel()

        row = {
            "threshold": threshold,
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(
                precision_score(y_true, y_pred, zero_division=0)
            ),
            "recall": float(
                recall_score(y_true, y_pred, zero_division=0)
            ),
            "f1": float(f1_score(y_true, y_pred, zero_division=0)),
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        }
        results.append(row)

        print(
            f"{threshold:9.2f} "
            f"{row['accuracy']:9.3f} "
            f"{row['precision']:10.3f} "
            f"{row['recall']:8.3f} "
            f"{row['f1']:8.3f} "
            f"{fp:5d} {fn:5d}"
        )

    review = df[
        (
            (df["expected_label"] == 0)
            & (df["ml_attack_probability"] >= 0.65)
        )
        |
        (
            (df["expected_label"] == 1)
            & (df["ml_attack_probability"] < 0.65)
        )
    ]

    print("\nCASES TO REVIEW AT THRESHOLD 0.65")
    print("-" * 75)

    if review.empty:
        print("No misclassifications at this threshold.")
    else:
        columns = [
            col for col in [
                "id",
                "category",
                "language",
                "expected_label",
                "ml_attack_probability",
                "text",
            ]
            if col in review.columns
        ]
        print(review[columns].to_string(index=False))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nSaved report: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
