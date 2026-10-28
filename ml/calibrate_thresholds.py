
import csv
import json
import sys
import time
from pathlib import Path

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

# ---------------------------------------------------------
# Project setup
# ---------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.multilingual_cases import MULTILINGUAL_CASES
from app.detector import analyze_text

OUTPUT_DIR = ROOT / "ml" / "artifacts"

CSV_PATH = OUTPUT_DIR / "threshold_calibration.csv"
JSON_PATH = OUTPUT_DIR / "threshold_calibration.json"

# Candidate thresholds to compare.
THRESHOLDS = [
    0.50,
    0.55,
    0.60,
    0.65,
    0.70,
    0.75,
    0.80,
    0.85,
    0.90,
]


# ---------------------------------------------------------
# Metrics
# ---------------------------------------------------------

def calculate_metrics(labels, predictions):
    tn, fp, fn, tp = confusion_matrix(
        labels,
        predictions,
        labels=[0, 1],
    ).ravel()

    return {
        "samples": len(labels),
        "accuracy": float(
            accuracy_score(labels, predictions)
        ),
        "precision": float(
            precision_score(
                labels,
                predictions,
                zero_division=0,
            )
        ),
        "recall": float(
            recall_score(
                labels,
                predictions,
                zero_division=0,
            )
        ),
        "f1": float(
            f1_score(
                labels,
                predictions,
                zero_division=0,
            )
        ),
        "false_positive_rate": (
            float(fp / (fp + tn))
            if (fp + tn) else 0.0
        ),
        "false_negative_rate": (
            float(fn / (fn + tp))
            if (fn + tp) else 0.0
        ),
        "true_positive": int(tp),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
    }


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():
    if not MULTILINGUAL_CASES:
        raise ValueError(
            "No cases found in ml/multilingual_cases.py"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Run the detector once per test case.
    # Reuse these risk scores for every threshold.
    base_rows = []

    for case in MULTILINGUAL_CASES:
        started = time.perf_counter()

        result = analyze_text(case["text"])

        latency_ms = (
            time.perf_counter() - started
        ) * 1000

        base_rows.append({
            "id": case["id"],
            "language": case["language"],
            "category": case["category"],
            "text": case["text"],
            "expected_label": int(case["label"]),
            "risk_score": float(result["risk_score"]),
            "current_action": result["action"],
            "latency_ms": round(latency_ms, 4),
        })

    labels = [
        row["expected_label"]
        for row in base_rows
    ]

    calibration_results = []
    prediction_rows = []

    for threshold in THRESHOLDS:
        predictions = [
            int(row["risk_score"] >= threshold)
            for row in base_rows
        ]

        metrics = calculate_metrics(
            labels,
            predictions,
        )

        calibration_results.append({
            "threshold": threshold,
            **metrics,
        })

        for row, predicted in zip(
            base_rows,
            predictions,
        ):
            prediction_rows.append({
                "threshold": threshold,
                "id": row["id"],
                "language": row["language"],
                "category": row["category"],
                "expected_label": row["expected_label"],
                "predicted_label": predicted,
                "correct": (
                    predicted == row["expected_label"]
                ),
                "risk_score": round(
                    row["risk_score"],
                    4,
                ),
                "current_action": row["current_action"],
                "text": row["text"],
            })

    # -----------------------------------------------------
    # Per-language evaluation for each threshold
    # -----------------------------------------------------

    per_language = {}

    languages = sorted({
        row["language"]
        for row in base_rows
    })

    for threshold in THRESHOLDS:
        threshold_report = {}

        for language in languages:
            language_rows = [
                row for row in base_rows
                if row["language"] == language
            ]

            lang_labels = [
                row["expected_label"]
                for row in language_rows
            ]

            lang_predictions = [
                int(row["risk_score"] >= threshold)
                for row in language_rows
            ]

            threshold_report[language] = (
                calculate_metrics(
                    lang_labels,
                    lang_predictions,
                )
            )

        per_language[str(threshold)] = threshold_report

    # -----------------------------------------------------
    # Save CSV
    # -----------------------------------------------------

    with CSV_PATH.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(prediction_rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(prediction_rows)

    # -----------------------------------------------------
    # Save JSON
    # -----------------------------------------------------

    report = {
        "description": (
            "Threshold calibration on manually authored "
            "multilingual development cases. Not an "
            "independent or validated benchmark."
        ),
        "number_of_cases": len(base_rows),
        "thresholds": calibration_results,
        "by_language": per_language,
        "note": (
            "Changing the evaluation threshold does not "
            "change the live BLOCK/REVIEW/ALLOW policy."
        ),
    }

    with JSON_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False,
        )

    # -----------------------------------------------------
    # Print results
    # -----------------------------------------------------

    print("\nTHRESHOLD CALIBRATION")
    print("=" * 88)

    print(
        f"{'Threshold':10} {'Accuracy':10} "
        f"{'Precision':10} {'Recall':10} "
        f"{'F1':10} {'FP':5} {'FN':5}"
    )

    for item in calibration_results:
        print(
            f"{item['threshold']:<10.2f} "
            f"{item['accuracy']:<10.3f} "
            f"{item['precision']:<10.3f} "
            f"{item['recall']:<10.3f} "
            f"{item['f1']:<10.3f} "
            f"{item['false_positive']:<5} "
            f"{item['false_negative']:<5}"
        )

    print("\nTELUGU-SCRIPT COMPARISON")
    print("-" * 88)

    for threshold in THRESHOLDS:
        metrics = per_language[str(threshold)][
            "Telugu-script"
        ]

        print(
            f"Threshold={threshold:.2f} "
            f"Accuracy={metrics['accuracy']:.3f} "
            f"F1={metrics['f1']:.3f} "
            f"FP={metrics['false_positive']} "
            f"FN={metrics['false_negative']}"
        )

    print("\nSaved CSV:", CSV_PATH)
    print("Saved JSON:", JSON_PATH)


if __name__ == "__main__":
    main()
