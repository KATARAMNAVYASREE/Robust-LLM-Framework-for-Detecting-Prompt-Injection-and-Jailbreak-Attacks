
from pathlib import Path
import json

import joblib
import pandas as pd
from datasets import load_dataset
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)

ROOT = Path(__file__).resolve().parents[1]

EXTRA_DATA = ROOT / "ml" / "data" / "stage8_examples.csv"
ARTIFACTS = ROOT / "ml" / "artifacts"
MODEL_PATH = ARTIFACTS / "prompt_injection_model.joblib"
REPORT_PATH = ARTIFACTS / "stage8_validation_results.json"

DATASET_NAME = "neuralchemy/Prompt-injection-dataset"


def normalize_frame(df):
    """Validate and normalize dataset columns."""
    if "text" not in df.columns or "label" not in df.columns:
        raise ValueError(
            f"Expected text and label columns; found {list(df.columns)}"
        )

    df = df[["text", "label"]].copy()
    df["text"] = df["text"].fillna("").astype(str).str.strip()
    df["label"] = pd.to_numeric(df["label"], errors="raise").astype(int)

    df = df[df["text"] != ""]
    df = df[df["label"].isin([0, 1])]

    return df.drop_duplicates(subset=["text", "label"])


def main():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)

    if not EXTRA_DATA.exists():
        raise FileNotFoundError(
            f"Missing {EXTRA_DATA}. Run ml/create_stage8_data.py first."
        )

    print("Loading original dataset...")
    dataset = load_dataset(DATASET_NAME, "core")

    if "train" not in dataset or "test" not in dataset:
        raise ValueError(
            f"Unexpected dataset splits: {list(dataset.keys())}"
        )

    validation_key = (
        "validation" if "validation" in dataset
        else "val" if "val" in dataset
        else None
    )
    if validation_key is None:
        raise ValueError(
            f"No validation split found. Available: {list(dataset.keys())}"
        )

    original_train = normalize_frame(
        pd.DataFrame(dataset["train"])
    )
    validation = normalize_frame(
        pd.DataFrame(dataset[validation_key])
    )
    test = normalize_frame(
        pd.DataFrame(dataset["test"])
    )
    extra = normalize_frame(pd.read_csv(EXTRA_DATA))

    # Only add the curated examples to training data.
    training = pd.concat(
        [original_train, extra],
        ignore_index=True,
    ).drop_duplicates(subset=["text", "label"])

    print(f"Original training rows: {len(original_train)}")
    print(f"Additional examples:    {len(extra)}")
    print(f"Combined training rows: {len(training)}")
    print(f"Validation rows:        {len(validation)}")
    print(f"Test rows reserved:     {len(test)}")

    # Word features capture phrases; character features can help
    # with spelling variation and some obfuscation.
    model = Pipeline([
        ("features", FeatureUnion([
            ("word", TfidfVectorizer(
                analyzer="word",
                ngram_range=(1, 2),
                max_features=50000,
                min_df=2,
                sublinear_tf=True,
                strip_accents=None,
            )),
            ("char", TfidfVectorizer(
                analyzer="char",
                ngram_range=(3, 5),
                max_features=50000,
                min_df=2,
                sublinear_tf=True,
            )),
        ])),
        ("classifier", LogisticRegression(
            max_iter=1200,
            class_weight="balanced",
            random_state=42,
        )),
    ])

    print("\nTraining word + character TF-IDF classifier...")
    model.fit(training["text"], training["label"])

    # Validation is for diagnostics only; the test split is untouched.
    predictions = model.predict(validation["text"])
    probabilities = model.predict_proba(validation["text"])[:, 1]

    report = {
        "dataset": DATASET_NAME,
        "training_rows_original": int(len(original_train)),
        "training_rows_added": int(len(extra)),
        "training_rows_combined": int(len(training)),
        "validation_rows": int(len(validation)),
        "test_rows_reserved": int(len(test)),
        "validation_metrics": {
            "accuracy": float(accuracy_score(
                validation["label"], predictions
            )),
            "precision": float(precision_score(
                validation["label"], predictions, zero_division=0
            )),
            "recall": float(recall_score(
                validation["label"], predictions, zero_division=0
            )),
            "f1": float(f1_score(
                validation["label"], predictions, zero_division=0
            )),
        },
        "validation_probability_min": float(probabilities.min()),
        "validation_probability_max": float(probabilities.max()),
        "model_features": "word and character TF-IDF",
    }

    joblib.dump(model, MODEL_PATH)

    with REPORT_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\nValidation metrics:")
    for key, value in report["validation_metrics"].items():
        print(f"{key:12}: {value:.4f}")

    print(f"\nModel saved: {MODEL_PATH}")
    print(f"Report saved: {REPORT_PATH}")
    print("The test split was not used for training or threshold selection.")


if __name__ == "__main__":
    main()
