from typing import Dict, Any

from models.llm import generate
from models.router import select_model


class PeerReviewer:
    """
    AI reviewer responsible for independently evaluating
    another AI-generated result.
    """

    def __init__(self):
        self.task_type = "review"

        self.system_prompt = """
You are the Peer Reviewer in V.A.U.L.T., a sovereign
on-premise industrial AI system.

Your responsibility is to independently review an
AI-generated result.

Do not blindly accept the submitted answer.

Evaluate the result for:

1. Factual consistency
2. Logical consistency
3. Calculation correctness
4. Unit consistency
5. Unsupported assumptions
6. Missing information
7. Potential hallucinations
8. Whether the result actually answers the task

You must distinguish between:
- Correct
- Incorrect
- Uncertain

If the result contains a significant issue,
explain what is wrong and what should be corrected.

Respond using exactly this structure:

VERDICT: PASS
REASON: <reason>

or

VERDICT: REVISE
REASON: <reason>
CORRECTIONS: <required corrections>

Do not invent evidence that is not present in
the task or submitted result.
"""

    def review(
        self,
        task: str,
        result: str
    ) -> Dict[str, Any]:

        model = select_model(
            "classification"
        )

        prompt = f"""
{self.system_prompt}

Original task:
{task}

AI-generated result:
{result}

Perform an independent review now.
"""

        response = generate(
            prompt=prompt,
            model=model
        )

        return self._parse_review(
            response
        )

    def _parse_review(
        self,
        response: str
    ) -> Dict[str, Any]:

        lines = [
            line.strip()
            for line in response.splitlines()
            if line.strip()
        ]

        verdict = "UNKNOWN"
        reason = ""
        corrections = ""

        for line in lines:

            if line.upper().startswith(
                "VERDICT:"
            ):
                verdict = line.split(
                    ":",
                    1
                )[1].strip().upper()

            elif line.upper().startswith(
                "REASON:"
            ):
                reason = line.split(
                    ":",
                    1
                )[1].strip()

            elif line.upper().startswith(
                "CORRECTIONS:"
            ):
                corrections = line.split(
                    ":",
                    1
                )[1].strip()

        if verdict not in {
            "PASS",
            "REVISE",
            "UNKNOWN"
        }:
            verdict = "UNKNOWN"

        return {
            "verdict": verdict,
            "reason": reason,
            "corrections": corrections,
            "raw_response": response
        }