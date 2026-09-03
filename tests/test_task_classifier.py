from agents.task_classifier import TaskClassifier


def main():
    classifier = TaskClassifier()

    tasks = [
        "Summarize this inspection report.",
        "Write a Python function to calculate factorial.",
        "Calculate the pump efficiency from the given measurements."
    ]

    for task in tasks:
        result = classifier.classify(task)

        print("\nTask:", task)
        print("Classification:", result)


if __name__ == "__main__":
    main()