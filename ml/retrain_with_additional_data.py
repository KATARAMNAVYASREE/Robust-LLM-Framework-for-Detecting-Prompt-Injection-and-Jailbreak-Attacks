
import sys
import shutil
from pathlib import Path

import joblib
import pandas as pd

from datasets import load_dataset
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)

# Make the project root importable when running this script directly.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.additional_training_data import ADDITIONAL_TRAINING_DATA

MODEL_PATH = ROOT / "ml" / "artifacts" / "prompt_injection_model.joblib"
BACKUP_PATH = ROOT / "ml" / "artifacts" / "prompt_injection_model_backup.joblib"


import shutil
from pathlib import Path

import joblib
import pandas as pd

from datasets import load_dataset
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)

from ml.additional_training_data import ADDITIONAL_TRAINING_DATA


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "ml" / "artifacts" / "prompt_injection_model.joblib"
BACKUP_PATH = ROOT / "ml" / "artifacts" / "prompt_injection_model_backup.joblib"


def main():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Existing model not found: {MODEL_PATH}"
        )

    print("Loading the real dataset...")
    dataset = load_dataset(
        "neuralchemy/Prompt-injection-dataset",
        "core",
    )

    train_df = pd.DataFrame(dataset["train"])
    validation_df = pd.DataFrame(dataset["validation"])

    required = {"text", "label"}
    if not required.issubset(train_df.columns):
        raise ValueError(
            f"Training data must contain columns: {required}"
        )

    # Backup before replacing the current model.
    shutil.copy2(MODEL_PATH, BACKUP_PATH)
    print(f"Backup saved: {BACKUP_PATH}")

    extra_df = pd.DataFrame(
        ADDITIONAL_TRAINING_DATA,
        columns=["text", "label"],
    )

    # Train only on the original training split plus added examples.
    # Keep the original validation split separate.
    combined_df = pd.concat(
        [
            train_df[["text", "label"]],
            extra_df,
        ],
        ignore_index=True,
    )

    combined_df["text"] = combined_df["text"].astype(str)
    combined_df["label"] = combined_df["label"].astype(int)

    print("Original training rows:", len(train_df))
    print("Supplementary rows:", len(extra_df))
    print("Combined training rows:", len(combined_df))

    model = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                lowercase=True,
                strip_accents="unicode",
                ngram_range=(1, 2),
                min_df=1,
                max_features=50000,
                sublinear_tf=True,
            ),
        ),
        (
            "classifier",
            LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
            ),
        ),
    ])

    print("\nTraining updated model...")
    model.fit(
        combined_df["text"].tolist(),
        combined_df["label"].tolist(),
    )

    # This validation split is useful for checking general performance,
    # but it does not replace multilingual robustness testing.
    X_val = validation_df["text"].astype(str).tolist()
    y_val = validation_df["label"].astype(int).tolist()
    predictions = model.predict(X_val)

    print("\nOriginal validation split")
    print("-------------------------")
    print(f"Accuracy : {accuracy_score(y_val, predictions):.4f}")
    print(
        "Precision:",
        f"{precision_score(y_val, predictions, zero_division=0):.4f}",
    )
    print(
        "Recall   :",
        f"{recall_score(y_val, predictions, zero_division=0):.4f}",
    )
    print(
        "F1       :",
        f"{f1_score(y_val, predictions, zero_division=0):.4f}",
    )

    # Save to a temporary path first, then replace the model.
    temporary_path = MODEL_PATH.with_suffix(".tmp")
    joblib.dump(model, temporary_path)
    temporary_path.replace(MODEL_PATH)

    print(f"\nUpdated model saved: {MODEL_PATH}")
    print("Backup retained. Run multilingual evaluation next.")


if __name__ == "__main__":
    main()
