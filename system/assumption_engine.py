"""
V.A.U.L.T. Engineering Assumption Engine

Provides intelligent default assumptions for:

- Physical constants
- Engineering calculations
- Natural values
- Standard conditions

IMPORTANT:

The engine should not silently invent values.

Every assumption is recorded and can be shown
to the user.
"""


import re

from typing import Dict, Any, List


# =========================================================
# STANDARD CONSTANTS
# =========================================================

STANDARD_CONSTANTS = {

    "gravity": {

        "value": 9.81,

        "unit": "m/s²",

        "symbol": "g",

        "description":
            "standard gravitational acceleration",

    },

    "atmospheric_pressure": {

        "value": 101325,

        "unit": "Pa",

        "symbol": "P_atm",

        "description":
            "standard atmospheric pressure",

    },

    "water_density": {

        "value": 1000,

        "unit": "kg/m³",

        "symbol": "ρ",

        "description":
            "approximate density of water",

    },

    "air_density": {

        "value": 1.225,

        "unit": "kg/m³",

        "symbol": "ρ_air",

        "description":
            "standard air density at sea level",

    },

}


# =========================================================
# ASSUMPTION ENGINE
# =========================================================

class AssumptionEngine:

    """
    Detect missing information and determine
    whether scientifically reasonable assumptions
    can be applied.
    """

    def analyze(

        self,

        prompt: str,

        task_type: str = None,

    ) -> Dict[str, Any]:

        if not isinstance(

            prompt,

            str,

        ):

            return {

                "assumptions": [],

                "modified_prompt": prompt,

            }

        prompt_lower = (

            prompt
            .lower()

        )

        assumptions = []

        # =================================================
        # FORCE / ACCELERATION
        # =================================================

        if self._is_force_problem(

            prompt_lower

        ):

            result = (

                self._check_force_assumptions(

                    prompt_lower

                )

            )

            assumptions.extend(

                result

            )

        # =================================================
        # GRAVITY / WEIGHT
        # =================================================

        if self._mentions_gravity(

            prompt_lower

        ):

            assumptions.append(

                self._create_gravity_assumption()

            )

        # =================================================
        # WATER PROBLEMS
        # =================================================

        if self._mentions_water(

            prompt_lower

        ):

            assumptions.append(

                {

                    "variable":

                        "water_density",

                    "symbol":

                        "ρ",

                    "value":

                        STANDARD_CONSTANTS[
                            "water_density"
                        ][
                            "value"
                        ],

                    "unit":

                        STANDARD_CONSTANTS[
                            "water_density"
                        ][
                            "unit"
                        ],

                    "reason":

                        "Standard water density assumed.",

                }

            )

        # =================================================
        # BUILD ENHANCED PROMPT
        # =================================================

        modified_prompt = (

            self._build_modified_prompt(

                prompt,

                assumptions,

            )

        )

        return {

            "assumptions":

                assumptions,

            "modified_prompt":

                modified_prompt,

            "assumption_count":

                len(

                    assumptions

                ),

        }

    # =====================================================
    # FORCE DETECTION
    # =====================================================

    def _is_force_problem(

        self,

        prompt: str,

    ) -> bool:

        keywords = [

            "calculate the force",

            "calculate force",

            "find the force",

            "force required",

            "force needed",

            "force acting",

        ]

        return any(

            keyword in prompt

            for keyword in keywords

        )

    # =====================================================
    # CHECK FORCE ASSUMPTIONS
    # =====================================================

    def _check_force_assumptions(

        self,

        prompt: str,

    ) -> List[Dict[str, Any]]:

        assumptions = []

        # -------------------------------------------------
        # DOES PROMPT ALREADY CONTAIN ACCELERATION?
        # -------------------------------------------------

        acceleration_patterns = [

            r"\d+\s*m/s",

            r"\d+\s*m/s\^2",

            r"\d+\s*m/s²",

            r"acceleration\s*(is|=)?\s*\d+",

        ]

        acceleration_found = any(

            re.search(

                pattern,

                prompt,

            )

            for pattern

            in acceleration_patterns

        )

        if acceleration_found:

            return assumptions

        # -------------------------------------------------
        # GRAVITY CONTEXT
        # -------------------------------------------------

        gravity_context = [

            "gravity",

            "gravitational",

            "falling",

            "free fall",

            "weight",

            "earth",

            "dropped",

        ]

        if any(

            keyword in prompt

            for keyword in gravity_context

        ):

            assumptions.append(

                self._create_gravity_assumption()

            )

            return assumptions

        # -------------------------------------------------
        # GENERIC FORCE QUESTION
        #
        # DEVELOPMENT DEFAULT:
        #
        # Assume standard gravity.
        #
        # This is configurable and clearly reported.
        # -------------------------------------------------

        assumptions.append(

            {

                "variable":

                    "acceleration",

                "symbol":

                    "a",

                "value":

                    9.81,

                "unit":

                    "m/s²",

                "reason":

                    (
                        "No acceleration was provided. "
                        "Using standard gravitational "
                        "acceleration as the engineering "
                        "default assumption."
                    ),

                "confidence":

                    "medium",

            }

        )

        return assumptions

    # =====================================================
    # GRAVITY DETECTION
    # =====================================================

    def _mentions_gravity(

        self,

        prompt: str,

    ) -> bool:

        keywords = [

            "gravity",

            "gravitational",

            "free fall",

            "falling",

            "weight",

            "earth gravity",

        ]

        return any(

            keyword in prompt

            for keyword in keywords

        )

    # =====================================================
    # WATER DETECTION
    # =====================================================

    def _mentions_water(

        self,

        prompt: str,

    ) -> bool:

        keywords = [

            "water",

            "hydraulic",

            "fluid water",

        ]

        return any(

            keyword in prompt

            for keyword in keywords

        )

    # =====================================================
    # GRAVITY ASSUMPTION
    # =====================================================

    def _create_gravity_assumption(

        self,

    ) -> Dict[str, Any]:

        return {

            "variable":

                "gravity",

            "symbol":

                "g",

            "value":

                STANDARD_CONSTANTS[
                    "gravity"
                ][
                    "value"
                ],

            "unit":

                STANDARD_CONSTANTS[
                    "gravity"
                ][
                    "unit"
                ],

            "reason":

                (
                    "Standard gravitational "
                    "acceleration assumed."
                ),

            "confidence":

                "high",

        }

    # =====================================================
    # BUILD ENHANCED PROMPT
    # =====================================================

    def _build_modified_prompt(

        self,

        original_prompt: str,

        assumptions:

            List[
                Dict[str, Any]
            ],

    ) -> str:

        if not assumptions:

            return original_prompt

        assumption_text = []

        for assumption in assumptions:

            variable = (

                assumption.get(

                    "variable"

                )

            )

            value = (

                assumption.get(

                    "value"

                )

            )

            unit = (

                assumption.get(

                    "unit"

                )

            )

            assumption_text.append(

                f"{variable} = "

                f"{value} "

                f"{unit}"

            )

        assumptions_string = (

            "\n".join(

                assumption_text

            )

        )

        return (

            f"{original_prompt}\n\n"

            "SYSTEM ENGINEERING ASSUMPTIONS:\n"

            f"{assumptions_string}\n\n"

            "Use these assumptions only because "
            "the original problem does not provide "
            "the required values. Clearly state "
            "all assumptions in the final answer."

        )


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. ASSUMPTION ENGINE TEST"
    )

    print("=" * 60)

    engine = AssumptionEngine()

    test_prompts = [

        (
            "Calculate the force required to "
            "accelerate a 10 kg object."
        ),

        (
            "Calculate the weight of a "
            "20 kg object."
        ),

        (
            "Calculate the pressure at the "
            "bottom of a water tank."
        ),

    ]

    for prompt in test_prompts:

        print()

        print("-" * 60)

        print(

            f"PROMPT: {prompt}"

        )

        print()

        result = engine.analyze(

            prompt,

            task_type="engineering",

        )

        print(

            "ASSUMPTIONS:"

        )

        print(

            result["assumptions"]

        )

        print()

        print(

            "MODIFIED PROMPT:"

        )

        print(

            result["modified_prompt"]

        )

    print()

    print("=" * 60)

    print(

        "ASSUMPTION ENGINE TEST COMPLETE"

    )

    print("=" * 60)