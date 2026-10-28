from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

def calculate_metrics(y_true, y_pred):
    if not y_true:
        return {"samples": 0, "accuracy": 0, "precision": 0, "recall": 0, "f1": 0,
                "false_positive_rate": 0, "false_negative_rate": 0, "tn": 0, "fp": 0, "fn": 0, "tp": 0}
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0,1]).ravel()
    return {
        "samples": len(y_true),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "false_positive_rate": round(float(fp / (fp + tn)) if fp + tn else 0, 4),
        "false_negative_rate": round(float(fn / (fn + tp)) if fn + tp else 0, 4),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)
    }
