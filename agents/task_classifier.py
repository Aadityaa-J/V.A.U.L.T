from models.llm import generate
from models.router import select_model


class TaskClassifier:
    def __init__(self):
        self.task_type = "classification"

    def classify(self, task: str) -> str:
        """
        Classify a user task into the appropriate V.A.U.L.T. agent.

        Supported categories:
        - document
        - coding
        - engineering
        - general
        """

        model = select_model(self.task_type)

        prompt = f"""
You are the task classifier for V.A.U.L.T.

Classify the user's task into exactly ONE of these categories:

- document
- coding
- engineering
- general

Definitions:

document:
Tasks specifically involving reading, analyzing, summarizing,
extracting, searching, or interpreting a document or file.

coding:
Tasks involving writing, debugging, modifying, executing,
or explaining computer code.

engineering:
Tasks involving engineering calculations, measurements,
equipment analysis, formulas, physical quantities, technical
parameters, or engineering interpretation.

general:
Normal conversation, greetings, questions about the user,
follow-up conversation, general knowledge questions, or any
task that does not clearly belong to document, coding,
or engineering.

Important rules:

- Do NOT classify normal conversation as document.
- Only choose document when the user explicitly refers to a
  document, file, or document-related task.
- Only choose coding when the task is clearly about programming
  or software development.
- Only choose engineering when the task is clearly an engineering
  or technical calculation/problem.
- If uncertain, choose general.

User task:
{task}

Respond with ONLY the category name.
"""

        response = generate(
            prompt=prompt,
            model=model
        )

        result = response.strip().lower()

        valid_categories = {
            "document",
            "coding",
            "engineering",
            "general",
        }

        if result not in valid_categories:
            # Safe fallback: normal/general conversation.
            return "general"

        return result