"""
V.A.U.L.T. Fine-Tuning Evaluator

Responsible for evaluating candidate fine-tuned models.

A trained model is NOT automatically approved.

The evaluator compares:

Base Model Score
        vs
Candidate Model Score

Only improved models can be accepted.
"""


from abc import ABC, abstractmethod

from typing import Any, Dict, Optional


# ==========================================================
# BASE EVALUATION BACKEND
# ==========================================================

class EvaluationBackend(ABC):

    """
    Abstract interface for model evaluation.

    Different evaluation systems can later be used:

    - Local benchmark evaluator
    - Engineering test suite
    - Document evaluation suite
    - LLM evaluation
    - Human evaluation
    """

    @abstractmethod
    def evaluate(
        self,
        model: Dict[str, Any],
        evaluation_dataset: Any,
    ) -> Dict[str, Any]:

        pass


# ==========================================================
# MOCK EVALUATOR
# ==========================================================

class MockEvaluationBackend(
    EvaluationBackend
):

    """
    Development evaluation backend.

    Allows the complete V.A.U.L.T.
    fine-tuning lifecycle to be tested without
    loading or running real models.
    """

    def __init__(
        self,
        scores: Optional[
            Dict[str, float]
        ] = None,
        should_fail: bool = False,
    ):

        self.scores = scores or {}

        self.should_fail = should_fail

    def evaluate(
        self,
        model: Dict[str, Any],
        evaluation_dataset: Any,
    ) -> Dict[str, Any]:

        # --------------------------------------------------
        # SIMULATE FAILURE
        # --------------------------------------------------

        if self.should_fail:

            raise RuntimeError(
                "Mock evaluation failure."
            )

        # --------------------------------------------------
        # GET MODEL NAME
        # --------------------------------------------------

        model_name = model.get(
            "model_name"
        )

        if not model_name:

            raise ValueError(
                "Model name is required "
                "for evaluation."
            )

        # --------------------------------------------------
        # GET SCORE
        # --------------------------------------------------

        score = self.scores.get(
            model_name,
            0.0,
        )

        return {

            "success": True,

            "model_name":
                model_name,

            "score":
                float(score),

            "evaluation_dataset":
                evaluation_dataset,

        }


# ==========================================================
# FINE-TUNING EVALUATOR
# ==========================================================

class FineTuningEvaluator:

    """
    Compare a base model against a candidate
    fine-tuned model.

    The candidate must perform better than the
    base model to be accepted.
    """

    def __init__(
        self,
        backend: Optional[
            EvaluationBackend
        ] = None,
        minimum_improvement: float = 0.0,
    ):

        self.backend = (

            backend
            or MockEvaluationBackend()

        )

        self.minimum_improvement = (
            float(
                minimum_improvement
            )
        )

    # ======================================================
    # EVALUATE MODELS
    # ======================================================

    def evaluate_candidate(
        self,
        base_model: Dict[str, Any],
        candidate_model: Dict[str, Any],
        evaluation_dataset: Any,
    ) -> Dict[str, Any]:

        """
        Evaluate both models and decide whether
        the candidate should be accepted.
        """

        try:

            # ------------------------------------------------
            # EVALUATE BASE MODEL
            # ------------------------------------------------

            base_result = (

                self.backend.evaluate(

                    model=base_model,

                    evaluation_dataset=(
                        evaluation_dataset
                    ),

                )

            )

            # ------------------------------------------------
            # EVALUATE CANDIDATE MODEL
            # ------------------------------------------------

            candidate_result = (

                self.backend.evaluate(

                    model=candidate_model,

                    evaluation_dataset=(
                        evaluation_dataset
                    ),

                )

            )

        except Exception as exc:

            # ----------------------------------------------
            # FAIL SAFE
            # ----------------------------------------------

            return {

                "accepted": False,

                "status":
                    "rejected",

                "reason":
                    (
                        "Evaluation failed: "
                        f"{exc}"
                    ),

                "base_score":
                    None,

                "candidate_score":
                    None,

                "improvement":
                    None,

            }

        # --------------------------------------------------
        # VALIDATE RESULTS
        # --------------------------------------------------

        if not (

            base_result.get(
                "success"
            )

            and

            candidate_result.get(
                "success"
            )

        ):

            return {

                "accepted": False,

                "status":
                    "rejected",

                "reason":
                    (
                        "One or more model "
                        "evaluations failed."
                    ),

                "base_score":
                    None,

                "candidate_score":
                    None,

                "improvement":
                    None,

            }

        # --------------------------------------------------
        # SCORES
        # --------------------------------------------------

        base_score = float(

            base_result.get(
                "score",
                0.0,
            )

        )

        candidate_score = float(

            candidate_result.get(
                "score",
                0.0,
            )

        )

        improvement = (

            candidate_score
            -
            base_score

        )

        # --------------------------------------------------
        # ACCEPT
        # --------------------------------------------------

        if (

            improvement
            >
            self.minimum_improvement

        ):

            return {

                "accepted": True,

                "status":
                    "accepted",

                "reason":
                    (
                        "Candidate model performed "
                        "better than the base model."
                    ),

                "base_score":
                    base_score,

                "candidate_score":
                    candidate_score,

                "improvement":
                    improvement,

            }

        # --------------------------------------------------
        # REJECT
        # --------------------------------------------------

        return {

            "accepted": False,

            "status":
                "rejected",

            "reason":
                (
                    "Candidate model did not meet "
                    "the required improvement."
                ),

            "base_score":
                base_score,

            "candidate_score":
                candidate_score,

            "improvement":
                improvement,

        }


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. FINE-TUNING EVALUATOR TEST"
    )

    print("=" * 60)

    # ------------------------------------------------------
    # MODELS
    # ------------------------------------------------------

    base_model = {

        "model_name":
            "qwen3:4b",

    }

    better_model = {

        "model_name":
            "vault-engineering-v1",

    }

    worse_model = {

        "model_name":
            "vault-engineering-bad",

    }

    evaluation_dataset = (
        "data/evaluation"
    )

    # ------------------------------------------------------
    # MOCK SCORES
    # ------------------------------------------------------

    backend = (

        MockEvaluationBackend(

            scores={

                "qwen3:4b":
                    0.80,

                "vault-engineering-v1":
                    0.91,

                "vault-engineering-bad":
                    0.72,

            }

        )

    )

    evaluator = (

        FineTuningEvaluator(

            backend=backend

        )

    )

    # ------------------------------------------------------
    # TEST 1
    # BETTER MODEL
    # ------------------------------------------------------

    result = (

        evaluator.evaluate_candidate(

            base_model=base_model,

            candidate_model=better_model,

            evaluation_dataset=(
                evaluation_dataset
            ),

        )

    )

    print()

    print(
        "TEST 1: BETTER MODEL"
    )

    print("-" * 60)

    print(result)

    # ------------------------------------------------------
    # TEST 2
    # WORSE MODEL
    # ------------------------------------------------------

    result = (

        evaluator.evaluate_candidate(

            base_model=base_model,

            candidate_model=worse_model,

            evaluation_dataset=(
                evaluation_dataset
            ),

        )

    )

    print()

    print(
        "TEST 2: WORSE MODEL"
    )

    print("-" * 60)

    print(result)

    # ------------------------------------------------------
    # TEST 3
    # EVALUATION FAILURE
    # ------------------------------------------------------

    failing_evaluator = (

        FineTuningEvaluator(

            backend=(

                MockEvaluationBackend(

                    should_fail=True

                )

            )

        )

    )

    result = (

        failing_evaluator.evaluate_candidate(

            base_model=base_model,

            candidate_model=better_model,

            evaluation_dataset=(
                evaluation_dataset
            ),

        )

    )

    print()

    print(
        "TEST 3: EVALUATION FAILURE"
    )

    print("-" * 60)

    print(result)

    print()

    print("=" * 60)

    print(
        "EVALUATOR TEST COMPLETE"
    )

    print("=" * 60)