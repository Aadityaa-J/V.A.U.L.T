from typing import Dict, Any


class HumanIntervention:
    """
    Represents the optional human intervention layer
    in V.A.U.L.T.

    Human intervention may provide:
    - additional context
    - corrections
    - revision requests
    - approval
    - rejection

    The component itself does not decide whether the
    human input is correct. It only provides a structured
    contract for passing that input into the validation
    workflow.
    """

    def __init__(self):
        self.last_input: Dict[str, Any] = {
            "status": "none",
            "input": ""
        }

    def provide_input(
        self,
        user_input: str
    ) -> Dict[str, Any]:

        if not user_input.strip():
            self.last_input = {
                "status": "none",
                "input": ""
            }

        else:
            self.last_input = {
                "status": "feedback",
                "input": user_input.strip()
            }

        return self.last_input.copy()

    def approve(
        self,
        comment: str = ""
    ) -> Dict[str, Any]:

        self.last_input = {
            "status": "approve",
            "input": comment.strip()
        }

        return self.last_input.copy()

    def reject(
        self,
        reason: str
    ) -> Dict[str, Any]:

        self.last_input = {
            "status": "reject",
            "input": reason.strip()
        }

        return self.last_input.copy()

    def clear(self) -> Dict[str, Any]:

        self.last_input = {
            "status": "none",
            "input": ""
        }

        return self.last_input.copy()

    def get_last_input(self) -> Dict[str, Any]:

        return self.last_input.copy()