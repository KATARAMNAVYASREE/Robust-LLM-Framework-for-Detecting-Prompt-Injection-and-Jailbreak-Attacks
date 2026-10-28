
import json
import sys
import time
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.detector as detector
from ml.test_adversarial import CASES


ARTIFACTS = ROOT / "ml" / "artifacts"
ACTIVE_MODEL = ARTIFACTS / "prompt_injection_model.joblib"
REPORT_PATH = ARTIFACTS / "stage10_comparison.json"


def metrics(rows):
    tp = sum(r["expected"] == 1 and r["predicted"] == 1 for r in rows)
    tn = sum(r["expected"] == 0 and r["predicted"] == 0 for r in rows)
    fp = sum(r["expected"] == 0 and r["predicted"] == 1 for r in rows)
    fn = sum(r["expected"] == 1 and r["predicted"] == 0 for r in rows)

    def ratio(a, b):
        return a / b if b else 0.0

    precision = ratio(tp, tp + fp)
    recall = ratio(tp, tp + fn)
    f1 = ratio(2 * precision * recall, precision + recall)

    return {
        "samples": len(rows),
        "accuracy": ratio(tp + tn, len(rows)),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": ratio(fp, fp + tn),
        "false_negative_rate": ratio(fn, fn + tp),
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
    }


def evaluate(model_path):
    model = joblib.load(model_path)
    previous_model = detector.ml_model
    detector.ml_model = model

    rows = []
    latencies = []

    try:
        for case in CASES:
            started = time.perf_counter()
            result = detector.analyze_text(case["text"])
            elapsed = (time.perf_counter() - started) * 1000

            expected = int(case["label"])
            predicted = int(bool(result["is_attack"]))

            rows.append({
                "id": case["id"],
                "language": case["language"],
                "category": case["category"],
                "expected": expected,
                "predicted": predicted,
                "correct": expected == predicted,
                "risk_score": result["risk_score"],
                "action": result["action"],
            })
            latencies.append(elapsed)
    finally:
        detector.ml_model = previous_model

    return {
        "metrics": metrics(rows),
        "average_latency_ms": (
            sum(latencies) / len(latencies) if latencies else 0.0
        ),
        "predictions": rows,
    }


def find_previous_model():
    # Prefer the timestamped backup made by the Stage 10 trainer.
    backups = list(ARTIFACTS.glob("prompt_injection_model_backup_*.joblib"))

    # Fall back to the earlier fixed-name backup if present.
    fixed_backup = ARTIFACTS / "prompt_injection_model_backup.joblib"
    if not backups and fixed_backup.exists():
        return fixed_backup

    if not backups:
        raise FileNotFoundError(
            "No previous model backup found. Retrain using the Stage 10 "
            "script first, or specify the backup path manually."
        )

    return max(backups, key=lambda p: p.stat().st_mtime)


def main():
    if not ACTIVE_MODEL.exists():
        raise FileNotFoundError(f"Active model not found: {ACTIVE_MODEL}")

    old_path = find_previous_model()

    print(f"Previous model: {old_path}")
    print(f"Updated model : {ACTIVE_MODEL}")

    before = evaluate(old_path)
    after = evaluate(ACTIVE_MODEL)

    report = {
        "description": (
            "Before-and-after comparison on the same manually authored "
            "adversarial cases. This is a small smoke test, not a validated benchmark."
        ),
        "previous_model": str(old_path),
        "updated_model": str(ACTIVE_MODEL),
        "before": before,
        "after": after,
    }

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nSTAGE 10 COMPARISON")
    print("=" * 65)

    for name, result in (("BEFORE", before), ("AFTER", after)):
        m = result["metrics"]
        print(
            f"{name:7} "
            f"accuracy={m['accuracy']:.3f} "
            f"precision={m['precision']:.3f} "
            f"recall={m['recall']:.3f} "
            f"F1={m['f1']:.3f} "
            f"FPR={m['false_positive_rate']:.3f} "
            f"FP={m['false_positive']} "
            f"FN={m['false_negative']}"
        )

    print("\nCASE-BY-CASE CHANGES")
    old_by_id = {r["id"]: r for r in before["predictions"]}
    new_by_id = {r["id"]: r for r in after["predictions"]}

    for case in CASES:
        case_id = case["id"]
        old = old_by_id[case_id]
        new = new_by_id[case_id]

        if old["predicted"] != new["predicted"]:
            print(
                f"{case_id}: prediction "
                f"{old['predicted']} -> {new['predicted']}; "
                f"risk {old['risk_score']:.4f} -> {new['risk_score']:.4f}; "
                f"action {old['action']} -> {new['action']}"
            )

    print(f"\nJSON report saved: {REPORT_PATH}")


if __name__ == "__main__":
    main()
