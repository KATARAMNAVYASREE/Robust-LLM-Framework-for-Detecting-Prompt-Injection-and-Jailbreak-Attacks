from datasets import load_dataset


DATASET_NAME = "neuralchemy/Prompt-injection-dataset"


def main():

    print("Loading dataset...")

    dataset = load_dataset(
        DATASET_NAME,
        "core"
    )

    print("\nDataset loaded successfully.")

    print("\nAvailable splits:")
    print(dataset)

    for split_name in dataset.keys():

        split = dataset[split_name]

        print(f"\n--- {split_name} ---")
        print("Rows:", len(split))
        print("Columns:", split.column_names)

        print("\nFirst sample:")
        print(split[0])


if __name__ == "__main__":
    main()