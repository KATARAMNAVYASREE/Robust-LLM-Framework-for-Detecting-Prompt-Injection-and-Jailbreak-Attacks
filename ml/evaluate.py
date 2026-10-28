
import json
import time
from pathlib import Path

import joblib
import numpy as np
from datasets import load_dataset
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_auc_score,
)

# Ensure imports work when running from the project root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

import sys
sys.path.insert(0, str(PROJECT_ROOT))

from app.detector import regex_detect


DATASET_NAME = "neuralchemy/Prompt-injection-dataset"
DATASET_CONFIG = "core"

MODEL_PATH = PROJECT_ROOT / "ml" / "artifacts" / "prompt_injection_model.joblib"
RESULT_PATH = PROJECT_ROOT / "ml" / "artifacts" / "evaluation_results.json"


def regex_predict(text):
    result = regex_detect(str(text))
    return int(bool(result.get("is_attack", False)))


def calculate_metrics(y_true, y_pred, probabilities=None):
    tn, fp, fn, tp = confusion_matrix(
        y_true, y_pred, labels=[0, 1]
    ).ravel()

    result = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "false_positive_rate": float(fp / (fp + tn)) if fp + tn else 0.0,
        "false_negative_rate": float(fn / (fn + tp)) if fn + tp else 0.0,
        "true_positive": int(tp),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
    }

    if probabilities is not None:
        try:
            result["roc_auc"] = float(roc_auc_score(y_true, probabilities))
        except ValueError:
            result["roc_auc"] = None

    return result


def measure_latency(function, items):
    predictions = []
    latencies_ms = []

    for item in items:
        start = time.perf_counter()
        prediction = function(item)
        elapsed = (time.perf_counter() - start) * 1000

        predictions.append(prediction)
        latencies_ms.append(elapsed)

    return predictions, {
        "average_ms": float(np.mean(latencies_ms)),
        "p95_ms": float(np.percentile(latencies_ms, 95)),
    }


def main():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Trained model not found: {MODEL_PATH}\n"
            "Train the model first using: python ml/train_real.py"
        )

    print("Loading benchmark dataset...")
    dataset = load_dataset(DATASET_NAME, DATASET_CONFIG)

    if "test" not in dataset:
        raise ValueError(
            f"No test split found. Available splits: {list(dataset.keys())}"
        )

    test_data = dataset["test"]

    if "text" not in test_data.column_names or "label" not in test_data.column_names:
        raise ValueError(
            f"Expected 'text' and 'label' columns. "
            f"Found: {test_data.column_names}"
        )

    texts = [str(text or "") for text in test_data["text"]]
    raw_labels = list(test_data["label"])

    # This evaluation expects binary labels: 0 = benign, 1 = attack.
    # Stop rather than silently guessing if the dataset uses other labels.
    try:
        labels = [int(label) for label in raw_labels]
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Labels are not numeric. Inspect the dataset label mapping "
            "before evaluating."
        ) from exc

    if not set(labels).issubset({0, 1}):
        raise ValueError(
            f"Expected binary labels 0 and 1; found: {sorted(set(labels))}"
        )

    if not texts:
        raise ValueError("The test split is empty.")

    print(f"Test samples: {len(texts)}")
    print(f"Label counts: benign={labels.count(0)}, attack={labels.count(1)}")

    print("\nLoading trained model...")
    model = joblib.load(MODEL_PATH)

    # Identify the model's positive class rather than assuming
    # probability column 1 always represents attacks.
    classes = list(model.classes_)
    if 1 not in classes:
        raise ValueError(
            f"The trained model has no positive class 1. Classes: {classes}"
        )
    positive_index = classes.index(1)

    def ml_predict(text):
        return int(model.predict([text])[0])

    def ml_probability(text):
        return float(model.predict_proba([text])[0][positive_index])

    print("\nEvaluating ML classifier...")
    ml_predictions, ml_latency = measure_latency(ml_predict, texts)
    ml_probabilities = [ml_probability(text) for text in texts]

    print("Evaluating regex baseline...")
    regex_predictions, regex_latency = measure_latency(regex_predict, texts)

    results = {
        "dataset": DATASET_NAME,
        "config": DATASET_CONFIG,
        "test_samples": len(texts),
        "label_mapping": {"0": "benign", "1": "attack"},
        "regex_baseline": {
            "metrics": calculate_metrics(labels, regex_predictions),
            "latency": regex_latency,
        },
        "ml_classifier": {
            "metrics": calculate_metrics(
                labels, ml_predictions, ml_probabilities
            ),
            "latency": ml_latency,
        },
    }

    print("\n" + "=" * 55)
    print("REGEX BASELINE")
    print(json.dumps(results["regex_baseline"], indent=2))

    print("\n" + "=" * 55)
    print("ML CLASSIFIER")
    print(json.dumps(results["ml_classifier"], indent=2))

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RESULT_PATH.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)

    print(f"\nEvaluation results saved to: {RESULT_PATH}")


if __name__ == "__main__":
    main()
