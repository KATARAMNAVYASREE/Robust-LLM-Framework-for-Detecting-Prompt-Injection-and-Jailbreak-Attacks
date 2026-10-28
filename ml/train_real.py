import os
import joblib

from datasets import load_dataset

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    accuracy_score
)


DATASET_NAME = "neuralchemy/Prompt-injection-dataset"

MODEL_DIR = os.path.join(
    os.path.dirname(__file__),
    "artifacts"
)

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "prompt_injection_model.joblib"
)


def main():

    print("Loading real dataset...")

    dataset = load_dataset(
        DATASET_NAME,
        "core"
    )

    train_data = dataset["train"]
    validation_data = dataset["validation"]

    X_train = train_data["text"]
    y_train = train_data["label"]

    X_val = validation_data["text"]
    y_val = validation_data["label"]

    print("\nTraining samples:", len(X_train))
    print("Validation samples:", len(X_val))

    print("\nTraining TF-IDF + Logistic Regression...")

    model = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                lowercase=True,
                strip_accents="unicode",
                ngram_range=(1, 2),
                min_df=2,
                max_features=50000,
                sublinear_tf=True
            )
        ),

        (
            "classifier",
            LogisticRegression(
                max_iter=1000,
                class_weight="balanced"
            )
        )
    ])

    model.fit(
        X_train,
        y_train
    )

    print("Training complete.")

    # -------------------------------------------------
    # Validation
    # -------------------------------------------------

    predictions = model.predict(X_val)

    precision = precision_score(
        y_val,
        predictions,
        zero_division=0
    )

    recall = recall_score(
        y_val,
        predictions,
        zero_division=0
    )

    f1 = f1_score(
        y_val,
        predictions,
        zero_division=0
    )

    accuracy = accuracy_score(
        y_val,
        predictions
    )

    print("\nValidation Results")
    print("------------------")

    print(
        f"Accuracy : {accuracy:.4f}"
    )

    print(
        f"Precision: {precision:.4f}"
    )

    print(
        f"Recall   : {recall:.4f}"
    )

    print(
        f"F1       : {f1:.4f}"
    )

    # -------------------------------------------------
    # Save model
    # -------------------------------------------------

    os.makedirs(
        MODEL_DIR,
        exist_ok=True
    )

    joblib.dump(
        model,
        MODEL_PATH
    )

    print("\nModel saved to:")

    print(MODEL_PATH)


if __name__ == "__main__":
    main()