
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.additional_training_data import ADDITIONAL_TRAINING_DATA
from ml.test_adversarial import CASES


def normalize(text):
    return " ".join(text.casefold().split())


training_texts = {
    normalize(text): (text, label)
    for text, label in ADDITIONAL_TRAINING_DATA
}

overlaps = []

for case in CASES:
    key = normalize(case["text"])

    if key in training_texts:
        train_text, train_label = training_texts[key]
        overlaps.append({
            "test_id": case["id"],
            "test_label": int(case["label"]),
            "training_label": int(train_label),
            "text": case["text"],
            "labels_match": int(case["label"]) == int(train_label),
        })

print("EXACT TRAINING/TEST OVERLAP CHECK")
print("=" * 50)
print("Supplementary training examples:", len(ADDITIONAL_TRAINING_DATA))
print("Adversarial test examples:", len(CASES))
print("Exact overlapping examples:", len(overlaps))

for item in overlaps:
    print(
        f"\n{item['test_id']}: "
        f"test_label={item['test_label']}, "
        f"training_label={item['training_label']}, "
        f"labels_match={item['labels_match']}"
    )
    print("Text:", item["text"])

if not overlaps:
    print("No exact text overlaps found.")

print(
    "\nNote: This checks supplementary data only. "
    "It does not check overlap with the original downloaded training dataset."
)
