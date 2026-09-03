from models.llm import generate
from models.router import select_model


class TaskClassifier:
    def __init__(self):
        self.task_type = "classification"

    def classify(self, task: str) -> str:
        model = select_model(self.task_type)

        prompt = f"""
You are the task classifier for V.A.U.L.T.

Classify the user's task into exactly ONE of these categories:

- document
- coding
- engineering

Definitions:

document:
Tasks involving reading, analyzing, summarizing, extracting,
or interpreting documents.

coding:
Tasks involving writing, debugging, modifying, or explaining code.

engineering:
Tasks involving engineering calculations, measurements,
equipment analysis, formulas, technical parameters, or
engineering interpretation.

User task:
{task}

Respond with ONLY the category name.
"""

        response = generate(
            prompt=prompt,
            model=model
        )

        result = response.strip().lower()

        if result not in {
            "document",
            "coding",
            "engineering"
        }:
            raise ValueError(
                f"Invalid task classification: {result}"
            )

        return result