
import csv
import json
import sys
import time
from pathlib import Path
from collections import defaultdict

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.multilingual_cases import MULTILINGUAL_CASES
from app.detector import analyze_text

OUTPUT_DIR = ROOT / "ml" / "artifacts"
CSV_PATH = OUTPUT_DIR / "multilingual_predictions.csv"
JSON_PATH = OUTPUT_DIR / "multilingual_results.json"

# ---------------------------------------------------------
# Evaluation configuration
# ---------------------------------------------------------

# This threshold is for binary evaluation only.
# It does not change the detector's BLOCK/REVIEW/ALLOW policy.
EVALUATION_THRESHOLD = 0.65


# ---------------------------------------------------------
# Metric calculation
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
            if (fp + tn) > 0 else 0.0
        ),
        "false_negative_rate": (
            float(fn / (fn + tp))
            if (fn + tp) > 0 else 0.0
        ),
        "true_positive": int(tp),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
    }


# ---------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------

def main():
    if not MULTILINGUAL_CASES:
        raise ValueError(
            "MULTILINGUAL_CASES is empty. "
            "Check ml/multilingual_cases.py."
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = []
    groups = defaultdict(list)
    latencies = []

    print("Starting multilingual evaluation...")
    print(
        "Binary evaluation threshold:",
        EVALUATION_THRESHOLD,
    )
    print(
        "Number of test cases:",
        len(MULTILINGUAL_CASES),
    )

    for case in MULTILINGUAL_CASES:
        text = case["text"]
        expected = int(case["label"])

        start = time.perf_counter()
        result = analyze_text(text)
        elapsed_ms = (
            time.perf_counter() - start
        ) * 1000

        risk_score = float(result["risk_score"])

        # Binary evaluation prediction uses the configured
        # threshold, independently of the mitigation action.
        predicted = int(
            risk_score >= EVALUATION_THRESHOLD
        )

        row = {
            "id": case["id"],
            "language": case["language"],
            "category": case["category"],
            "expected_label": expected,
            "predicted_label": predicted,
            "correct": predicted == expected,
            "evaluation_threshold": EVALUATION_THRESHOLD,
            "risk_score": round(risk_score, 4),
            "action": result["action"],
            "attack_type": result.get(
                "attack_type",
                "unknown",
            ),
            "latency_ms": round(elapsed_ms, 4),
            "text": text,
        }

        rows.append(row)
        groups[case["language"]].append(row)
        latencies.append(elapsed_ms)

    # -----------------------------------------------------
    # Overall metrics
    # -----------------------------------------------------

    labels = [
        row["expected_label"]
        for row in rows
    ]

    predictions = [
        row["predicted_label"]
        for row in rows
    ]

    overall = calculate_metrics(
        labels,
        predictions,
    )

    results = {
        "description": (
            "Prototype multilingual evaluation using "
            "manually authored test cases. "
            "This is not a validated benchmark."
        ),
        "total_cases": len(rows),
        "evaluation_threshold": EVALUATION_THRESHOLD,
        "overall": overall,
        "average_latency_ms": (
            sum(latencies) / len(latencies)
            if latencies else 0.0
        ),
        "by_language": {},
    }

    # -----------------------------------------------------
    # Per-language metrics
    # -----------------------------------------------------

    for language, language_rows in sorted(
        groups.items()
    ):
        lang_labels = [
            row["expected_label"]
            for row in language_rows
        ]

        lang_predictions = [
            row["predicted_label"]
            for row in language_rows
        ]

        results["by_language"][language] = (
            calculate_metrics(
                lang_labels,
                lang_predictions,
            )
        )

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
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)

    # -----------------------------------------------------
    # Save JSON
    # -----------------------------------------------------

    with JSON_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            results,
            file,
            indent=2,
            ensure_ascii=False,
        )

    # -----------------------------------------------------
    # Print summary
    # -----------------------------------------------------

    print("\nMULTILINGUAL ROBUSTNESS RESULTS")
    print("=" * 70)
    print(
        json.dumps(
            results,
            indent=2,
            ensure_ascii=False,
        )
    )

    print("\nINDIVIDUAL PREDICTIONS")
    print("-" * 90)

    print(
        f"{'ID':8} {'LANGUAGE':24} {'EXPECTED':8} "
        f"{'PREDICTED':9} {'RISK':8} "
        f"{'ACTION':8} {'RESULT':8}"
    )

    for row in rows:
        status = (
            "PASS" if row["correct"] else "FAIL"
        )

        print(
            f"{row['id']:8} "
            f"{row['language'][:24]:24} "
            f"{row['expected_label']:<8} "
            f"{row['predicted_label']:<9} "
            f"{row['risk_score']:<8.4f} "
            f"{row['action']:<8} "
            f"{status:<8}"
        )

    print("\nLANGUAGE SUMMARY")
    print("-" * 70)

    for language, metrics in sorted(
        results["by_language"].items()
    ):
        print(
            f"{language:24} "
            f"n={metrics['samples']:<3} "
            f"accuracy={metrics['accuracy']:.3f} "
            f"precision={metrics['precision']:.3f} "
            f"recall={metrics['recall']:.3f} "
            f"F1={metrics['f1']:.3f} "
            f"FPR={metrics['false_positive_rate']:.3f}"
        )

    print("\nFILES SAVED")
    print("CSV:", CSV_PATH)
    print("JSON:", JSON_PATH)


if __name__ == "__main__":
    main()
