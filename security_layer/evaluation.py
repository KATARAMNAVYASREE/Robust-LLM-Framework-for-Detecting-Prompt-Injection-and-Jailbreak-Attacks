"""Reusable binary metrics and decision-policy summary."""
def binary_metrics(labels, predictions):
    if len(labels) != len(predictions):
        raise ValueError("labels and predictions must have equal length")
    if not labels:
        raise ValueError("At least one example is required")
    tp = sum(y == 1 and p == 1 for y, p in zip(labels, predictions))
    tn = sum(y == 0 and p == 0 for y, p in zip(labels, predictions))
    fp = sum(y == 0 and p == 1 for y, p in zip(labels, predictions))
    fn = sum(y == 1 and p == 0 for y, p in zip(labels, predictions))
    div = lambda a, b: a / b if b else 0.0
    precision = div(tp, tp + fp)
    recall = div(tp, tp + fn)
    f1 = div(2 * precision * recall, precision + recall)
    return {
        "samples": len(labels),
        "accuracy": div(tp + tn, len(labels)),
        "precision": precision, "recall": recall, "f1": f1,
        "false_positive_rate": div(fp, fp + tn),
        "false_negative_rate": div(fn, fn + tp),
        "TP": tp, "TN": tn, "FP": fp, "FN": fn,
    }

def policy_summary(rows):
    actions = ("BLOCK", "REVIEW", "ALLOW")
    counts = {a: sum(r.get("action") == a for r in rows) for a in actions}
    benign_review = [r.get("id") for r in rows
                     if int(r.get("label", 0)) == 0 and r.get("action") == "REVIEW"]
    benign_block = [r.get("id") for r in rows
                    if int(r.get("label", 0)) == 0 and r.get("action") == "BLOCK"]
    attack_not_blocked = [r.get("id") for r in rows
                          if int(r.get("label", 0)) == 1 and r.get("action") != "BLOCK"]
    return {
        "decision_counts": counts,
        "benign_review_ids": benign_review,
        "benign_block_ids": benign_block,
        "attack_not_blocked_ids": attack_not_blocked,
    }
