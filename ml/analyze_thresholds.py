
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

CSV_PATH = "ml/artifacts/robustness_predictions.csv"

df = pd.read_csv(CSV_PATH)

y_true = df["expected_label"].astype(int)
probabilities = df["ml_attack_probability"].astype(float)

print(f"Test examples: {len(df)}")
print()
print(
    f"{'Threshold':<12}"
    f"{'Accuracy':<12}"
    f"{'Precision':<12}"
    f"{'Recall':<10}"
    f"{'F1':<10}"
    f"{'FP':<6}"
    f"{'FN':<6}"
)

for threshold in [0.50, 0.60, 0.65, 0.70, 0.75, 0.80]:
    predictions = (probabilities >= threshold).astype(int)

    accuracy = accuracy_score(y_true, predictions)
    precision = precision_score(
        y_true, predictions, zero_division=0
    )
    recall = recall_score(
        y_true, predictions, zero_division=0
    )
    f1 = f1_score(
        y_true, predictions, zero_division=0
    )

    tn, fp, fn, tp = confusion_matrix(
        y_true, predictions, labels=[0, 1]
    ).ravel()

    print(
        f"{threshold:<12.2f}"
        f"{accuracy:<12.3f}"
        f"{precision:<12.3f}"
        f"{recall:<10.3f}"
        f"{f1:<10.3f}"
        f"{fp:<6}"
        f"{fn:<6}"
    )
