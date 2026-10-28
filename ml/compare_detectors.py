
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.detector import (
    regex_detect,
    ml_detect,
    analyze_text,
)
from app.normalizer import normalize_text

from ml.test_adversarial import CASES

OUTPUT_DIR = ROOT / "ml" / "artifacts"
CSV_PATH = OUTPUT_DIR / "detector_comparison.csv"
JSON_PATH = OUTPUT_DIR / "detector_comparison_summary.json"


def safe_divide(a, b):
    return a / b if b else 0.0


def calculate_metrics(labels, predictions):
    tp = sum(y == 1 and p == 1 for y, p in zip(labels, predictions))
    tn = sum(y == 0 and p == 0 for y, p in zip(labels, predictions))
    fp = sum(y == 0 and p == 1 for y, p in zip(labels, predictions))
    fn = sum(y == 1 and p == 0 for y, p in zip(labels, predictions))

    precision = safe_divide(tp, tp + fp)
    recall = safe_divide(tp, tp + fn)
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )

    return {
        "samples": len(labels),
        "accuracy": round(safe_divide(tp + tn, len(labels)), 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_positive_rate": round(safe_divide(fp, fp + tn), 4),
        "false_negative_rate": round(safe_divide(fn, fn + tp), 4),
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    methods = {
        "regex_only": [],
        "ml_only": [],
        "combined": [],
    }

    labels = []

    for case in CASES:
        text = case["text"]
        expected = int(case["label"])

        # All independent methods receive the same normalized text.
        normalized = normalize_text(text)["normalized_text"]

        start = time.perf_counter()
        regex_result = regex_detect(normalized)
        regex_ms = (time.perf_counter() - start) * 1000
        regex_prediction = int(regex_result["is_attack"])

        start = time.perf_counter()
        ml_result = ml_detect(normalized)
        ml_ms = (time.perf_counter() - start) * 1000

        if not ml_result["available"]:
            raise RuntimeError(
                "ML model unavailable. Check the model artifact path."
            )

        # ML-only uses a fixed 0.5 probability threshold.
        ml_prediction = int(ml_result["score"] >= 0.5)

        start = time.perf_counter()
        combined_result = analyze_text(text)
        combined_ms = (time.perf_counter() - start) * 1000

        # The combined method predicts a positive only for BLOCK.
        # REVIEW is reported separately, not silently treated as safe.
        combined_prediction = int(
            combined_result["action"] == "BLOCK"
        )

        labels.append(expected)
        methods["regex_only"].append(regex_prediction)
        methods["ml_only"].append(ml_prediction)
        methods["combined"].append(combined_prediction)

        rows.append({
            "id": case["id"],
            "category": case["category"],
            "language": case["language"],
            "expected_label": expected,
            "regex_prediction": regex_prediction,
            "regex_attack_type": regex_result["attack_type"],
            "regex_latency_ms": round(regex_ms, 4),
            "ml_prediction": ml_prediction,
            "ml_score": round(float(ml_result["score"]), 4),
            "ml_latency_ms": round(ml_ms, 4),
            "combined_prediction": combined_prediction,
            "combined_action": combined_result["action"],
            "combined_risk_score": combined_result["risk_score"],
            "combined_latency_ms": round(combined_ms, 4),
            "text": text,
        })

    summary = {
        "description": (
            "Small manually authored smoke test, not a validated "
            "security benchmark. Regex and ML are evaluated independently. "
            "Combined positive predictions mean BLOCK; REVIEW is reported "
            "separately and is not proof of safety."
        ),
        "sample_count": len(rows),
        "thresholds": {
            "regex_only": "At least one configured regex pattern matches",
            "ml_only": "Attack probability >= 0.5",
            "combined": "Action == BLOCK",
        },
        "metrics": {
            method: calculate_metrics(labels, predictions)
            for method, predictions in methods.items()
        },
        "combined_decision_counts": {
            action: sum(
                row["combined_action"] == action for row in rows
            )
            for action in ("BLOCK", "REVIEW", "ALLOW")
        },
        "benign_prompts_sent_to_review": [
            row["id"]
            for row in rows
            if row["expected_label"] == 0
            and row["combined_action"] == "REVIEW"
        ],
        "mean_latency_ms": {
            "regex_only": round(
                sum(row["regex_latency_ms"] for row in rows) / len(rows), 4
            ),
            "ml_only": round(
                sum(row["ml_latency_ms"] for row in rows) / len(rows), 4
            ),
            "combined": round(
                sum(row["combined_latency_ms"] for row in rows) / len(rows), 4
            ),
        },
    }

    with CSV_PATH.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with JSON_PATH.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2, ensure_ascii=False)

    print("\nDETECTOR COMPARISON")
    print("=" * 65)

    for method, metrics in summary["metrics"].items():
        print(f"\n{method.upper()}")
        print(json.dumps(metrics, indent=2))

    print("\nCOMBINED DECISION COUNTS")
    print(json.dumps(summary["combined_decision_counts"], indent=2))

    print("\nBENIGN PROMPTS SENT TO REVIEW")
    print(summary["benign_prompts_sent_to_review"])

    print("\nMEAN LATENCY (ms)")
    print(json.dumps(summary["mean_latency_ms"], indent=2))

    print(f"\nCSV saved: {CSV_PATH}")
    print(f"JSON saved: {JSON_PATH}")


if __name__ == "__main__":
    main()
