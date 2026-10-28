
import csv
import json
import sys
import time
from pathlib import Path
from collections import defaultdict

import joblib
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_auc_score,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.detector import regex_detect
from ml.robustness_cases import ROBUSTNESS_CASES

MODEL_PATH = PROJECT_ROOT / "ml" / "artifacts" / "prompt_injection_model.joblib"
OUTPUT_DIR = PROJECT_ROOT / "ml" / "artifacts"
JSON_PATH = OUTPUT_DIR / "robustness_results.json"
CSV_PATH = OUTPUT_DIR / "robustness_predictions.csv"


def metrics_for(labels, predictions, probabilities=None):
    tn, fp, fn, tp = confusion_matrix(
        labels, predictions, labels=[0, 1]
    ).ravel()

    result = {
        "samples": len(labels),
        "accuracy": float(accuracy_score(labels, predictions)),
        "precision": float(precision_score(
            labels, predictions, zero_division=0
        )),
        "recall": float(recall_score(
            labels, predictions, zero_division=0
        )),
        "f1": float(f1_score(
            labels, predictions, zero_division=0
        )),
        "false_positive_rate": float(fp / (fp + tn)) if (fp + tn) else 0.0,
        "false_negative_rate": float(fn / (fn + tp)) if (fn + tp) else 0.0,
        "true_positive": int(tp),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
    }

    if probabilities is not None:
        try:
            result["roc_auc"] = float(roc_auc_score(labels, probabilities))
        except ValueError:
            result["roc_auc"] = None

    return result


def timed_regex(text):
    start = time.perf_counter()
    result = regex_detect(text)
    elapsed_ms = (time.perf_counter() - start) * 1000

    return int(bool(result.get("is_attack", False))), elapsed_ms


def main():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. "
            "Train the model before running this script."
        )

    model = joblib.load(MODEL_PATH)
    model_classes = list(model.classes_)

    if 1 not in model_classes:
        raise ValueError(
            f"Model does not have attack class 1: {model_classes}"
        )

    attack_index = model_classes.index(1)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    regex_predictions, regex_times = [], []
    ml_predictions, ml_probabilities, ml_times = [], [], []
    labels = [int(case["label"]) for case in ROBUSTNESS_CASES]

    for case in ROBUSTNESS_CASES:
        text = case["text"]

        regex_prediction, regex_ms = timed_regex(text)
        regex_predictions.append(regex_prediction)
        regex_times.append(regex_ms)

        start = time.perf_counter()
        ml_prediction = int(model.predict([text])[0])
        ml_probability = float(
            model.predict_proba([text])[0][attack_index]
        )
        ml_ms = (time.perf_counter() - start) * 1000

        ml_predictions.append(ml_prediction)
        ml_probabilities.append(ml_probability)
        ml_times.append(ml_ms)

        rows.append({
            "id": case["id"],
            "category": case["category"],
            "language": case["language"],
            "expected_label": case["label"],
            "regex_prediction": regex_prediction,
            "regex_correct": regex_prediction == case["label"],
            "ml_prediction": ml_prediction,
            "ml_attack_probability": round(ml_probability, 6),
            "ml_correct": ml_prediction == case["label"],
            "regex_latency_ms": round(regex_ms, 6),
            "ml_latency_ms": round(ml_ms, 6),
            "text": text,
        })

    results = {
        "test_suite": "hand-authored robustness smoke tests",
        "warning": (
            "Small diagnostic suite; not a representative benchmark. "
            "Verify Telugu translations and labels with a fluent speaker."
        ),
        "case_count": len(ROBUSTNESS_CASES),
        "regex_baseline": metrics_for(labels, regex_predictions),
        "ml_classifier": metrics_for(
            labels, ml_predictions, ml_probabilities
        ),
        "latency": {
            "regex_average_ms": float(np.mean(regex_times)),
            "regex_p95_ms": float(np.percentile(regex_times, 95)),
            "ml_average_ms": float(np.mean(ml_times)),
            "ml_p95_ms": float(np.percentile(ml_times, 95)),
        },
        "by_category": {},
        "by_language": {},
    }

    # Breakdown by category and language.
    for grouping_field in ("category", "language"):
        grouped = defaultdict(list)

        for index, case in enumerate(ROBUSTNESS_CASES):
            grouped[case[grouping_field]].append(index)

        for group_name, indexes in grouped.items():
            group_labels = [labels[i] for i in indexes]
            group_regex = [regex_predictions[i] for i in indexes]
            group_ml = [ml_predictions[i] for i in indexes]

            results_key = (
                "by_category" if grouping_field == "category"
                else "by_language"
            )

            results[results_key][group_name] = {
                "regex": metrics_for(group_labels, group_regex),
                "ml": metrics_for(
                    group_labels,
                    group_ml,
                    [ml_probabilities[i] for i in indexes],
                ),
            }

    with JSON_PATH.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)

    with CSV_PATH.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print("\nOVERALL RESULTS")
    print(json.dumps({
        "regex_baseline": results["regex_baseline"],
        "ml_classifier": results["ml_classifier"],
        "latency": results["latency"],
    }, indent=2))

    print("\nBY LANGUAGE")
    print(json.dumps(results["by_language"], indent=2, ensure_ascii=False))

    print("\nBY CATEGORY")
    print(json.dumps(results["by_category"], indent=2, ensure_ascii=False))

    print(f"\nJSON report: {JSON_PATH}")
    print(f"CSV predictions: {CSV_PATH}")


if __name__ == "__main__":
    main()
