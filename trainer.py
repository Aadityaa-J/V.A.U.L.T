"""
V.A.U.L.T. Fine-Tuning Trainer

Supports:

- Mock training
- Real Hugging Face fine-tuning
- LoRA / QLoRA
- CUDA
- 4-bit quantization
- JSON / JSONL datasets

The public FineTuningTrainer interface remains backend-agnostic.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

import hashlib
import json
import os
from pathlib import Path


# ==========================================================
# BASE TRAINING BACKEND
# ==========================================================

class FineTuningBackend(ABC):

    @abstractmethod
    def train(
        self,
        job: Dict[str, Any],
    ) -> Dict[str, Any]:

        pass


# ==========================================================
# MOCK TRAINER
# ==========================================================

class MockTrainer(FineTuningBackend):

    def __init__(
        self,
        should_fail: bool = False,
    ):

        self.should_fail = should_fail

    def train(
        self,
        job: Dict[str, Any],
    ) -> Dict[str, Any]:

        if self.should_fail:

            return {
                "success": False,
                "error": "Mock training failure.",
                "artifact": None,
            }

        base_model = job.get(
            "base_model",
            "unknown-model",
        )

        task_type = job.get(
            "task_type",
            "general",
        )

        dataset_version = job.get(
            "dataset_version",
            "unknown",
        )

        timestamp = datetime.now().isoformat()

        unique_source = (
            f"{base_model}|"
            f"{task_type}|"
            f"{dataset_version}|"
            f"{timestamp}"
        )

        model_hash = hashlib.sha256(
            unique_source.encode("utf-8")
        ).hexdigest()[:12]

        model_name = (
            f"vault-{task_type}-{model_hash}"
        )

        artifact = {
            "model_name": model_name,
            "artifact_id": model_hash,
            "base_model": base_model,
            "task_type": task_type,
            "dataset_version": dataset_version,
            "created_at": timestamp,
            "runtime": "mock",
            "status": "trained",
        }

        return {
            "success": True,
            "artifact": artifact,
            "error": None,
        }


# ==========================================================
# REAL QLORA TRAINER
# ==========================================================

class QLoRATrainer(FineTuningBackend):

    """
    Real Hugging Face QLoRA trainer.

    Designed for low-VRAM NVIDIA GPUs.
    """

    DEFAULT_MODEL = (
        "Qwen/Qwen2.5-1.5B-Instruct"
    )

    def train(
        self,
        job: Dict[str, Any],
    ) -> Dict[str, Any]:

        try:

            import torch

            from datasets import Dataset

            from transformers import (
                AutoModelForCausalLM,
                AutoTokenizer,
                BitsAndBytesConfig,
                TrainingArguments,
                Trainer,
                DataCollatorForLanguageModeling,
            )

            from peft import (
                LoraConfig,
                get_peft_model,
                prepare_model_for_kbit_training,
            )

        except ImportError as exc:

            return {
                "success": False,
                "error": (
                    "Required training dependency "
                    f"is missing: {exc}"
                ),
                "artifact": None,
            }

        # --------------------------------------------------
        # CUDA CHECK
        # --------------------------------------------------

        if not torch.cuda.is_available():

            return {
                "success": False,
                "error": (
                    "CUDA GPU is required for "
                    "QLoRA training."
                ),
                "artifact": None,
            }

        # --------------------------------------------------
        # MODEL
        # --------------------------------------------------

        base_model = job.get(
            "base_model",
            self.DEFAULT_MODEL,
        )

        # Convert old Ollama-style model name.
        if base_model == "qwen3:4b":

            base_model = self.DEFAULT_MODEL

        # --------------------------------------------------
        # DATASET
        # --------------------------------------------------

        dataset_path = job.get(
            "dataset_path"
        )

        if not dataset_path:

            return {
                "success": False,
                "error": (
                    "dataset_path is required."
                ),
                "artifact": None,
            }

        dataset_file = self._find_dataset_file(
            dataset_path
        )

        if dataset_file is None:

            return {
                "success": False,
                "error": (
                    "No JSON or JSONL dataset "
                    f"found in: {dataset_path}"
                ),
                "artifact": None,
            }

        training_examples = (
            self._load_dataset(
                dataset_file
            )
        )

        if not training_examples:

            return {
                "success": False,
                "error": (
                    "Dataset contains no training "
                    "examples."
                ),
                "artifact": None,
            }

        # --------------------------------------------------
        # TOKENIZER
        # --------------------------------------------------

        tokenizer = (
            AutoTokenizer.from_pretrained(
                base_model,
                trust_remote_code=True,
            )
        )

        if tokenizer.pad_token is None:

            tokenizer.pad_token = (
                tokenizer.eos_token
            )

        # --------------------------------------------------
        # 4-BIT QUANTIZATION
        # --------------------------------------------------

        compute_dtype = torch.float16

        quantization_config = (
            BitsAndBytesConfig(

                load_in_4bit=True,

                bnb_4bit_quant_type="nf4",

                bnb_4bit_compute_dtype=(
                    compute_dtype
                ),

                bnb_4bit_use_double_quant=True,

            )
        )

        # --------------------------------------------------
        # LOAD MODEL
        # --------------------------------------------------

        model = (
            AutoModelForCausalLM
            .from_pretrained(

                base_model,

                quantization_config=(
                    quantization_config
                ),

                device_map="auto",

                trust_remote_code=True,

            )
        )

        model.config.use_cache = False

        model = (
            prepare_model_for_kbit_training(
                model
            )
        )

        # --------------------------------------------------
        # LORA CONFIGURATION
        # --------------------------------------------------

        lora_config = LoraConfig(

            r=8,

            lora_alpha=16,

            lora_dropout=0.05,

            bias="none",

            task_type="CAUSAL_LM",

            target_modules=[
                "q_proj",
                "k_proj",
                "v_proj",
                "o_proj",
            ],

        )

        model = get_peft_model(

            model,

            lora_config,

        )

        # --------------------------------------------------
        # DATASET PREPARATION
        # --------------------------------------------------

        dataset = Dataset.from_list(
            training_examples
        )

        def tokenize(example):

            text = example["text"]

            result = tokenizer(

                text,

                truncation=True,

                max_length=512,

                padding="max_length",

            )

            result["labels"] = (
                result["input_ids"].copy()
            )

            return result

        tokenized_dataset = (

            dataset.map(

                tokenize,

                remove_columns=(
                    dataset.column_names
                ),

            )

        )

        # --------------------------------------------------
        # OUTPUT DIRECTORY
        # --------------------------------------------------

        task_type = job.get(

            "task_type",

            "general",

        )

        timestamp = (
            datetime.now()
            .strftime(
                "%Y%m%d_%H%M%S"
            )
        )

        output_dir = Path(

            "models"
        ) / (

            "fine_tuned"
        ) / (

            f"{task_type}_{timestamp}"

        )

        output_dir.mkdir(

            parents=True,

            exist_ok=True,

        )

        # --------------------------------------------------
        # TRAINING ARGUMENTS
        # --------------------------------------------------

        training_args = TrainingArguments(

            output_dir=str(
                output_dir
            ),

            num_train_epochs=1,

            per_device_train_batch_size=1,

            gradient_accumulation_steps=8,

            learning_rate=2e-4,

            fp16=True,

            logging_steps=1,

            save_strategy="epoch",

            save_total_limit=1,

            report_to="none",

            optim="paged_adamw_8bit",

            warmup_ratio=0.03,

        )

        # --------------------------------------------------
        # TRAINER
        # --------------------------------------------------

        data_collator = (

            DataCollatorForLanguageModeling(

                tokenizer=tokenizer,

                mlm=False,

            )

        )

        trainer = Trainer(

            model=model,

            args=training_args,

            train_dataset=(
                tokenized_dataset
            ),

            data_collator=(
                data_collator
            ),

        )

        # --------------------------------------------------
        # TRAIN
        # --------------------------------------------------

        trainer.train()

        # --------------------------------------------------
        # SAVE LORA ADAPTER
        # --------------------------------------------------

        model.save_pretrained(

            output_dir

        )

        tokenizer.save_pretrained(

            output_dir

        )

        # --------------------------------------------------
        # CREATE ARTIFACT
        # --------------------------------------------------

        artifact_id = (

            hashlib.sha256(

                str(
                    output_dir
                )
                .encode("utf-8")

            )
            .hexdigest()[:12]

        )

        artifact = {

            "model_name":
                f"vault-{task_type}-{artifact_id}",

            "artifact_id":
                artifact_id,

            "base_model":
                base_model,

            "task_type":
                task_type,

            "dataset_version":
                job.get(
                    "dataset_version"
                ),

            "dataset_path":
                str(dataset_file),

            "training_examples":
                len(training_examples),

            "created_at":
                datetime.now().isoformat(),

            "runtime":
                "qlora",

            "status":
                "trained",

            "adapter_path":
                str(output_dir),

        }

        # --------------------------------------------------
        # GPU CLEANUP
        # --------------------------------------------------

        del trainer
        del model

        torch.cuda.empty_cache()

        return {

            "success": True,

            "artifact": artifact,

            "error": None,

        }

    # ======================================================
    # FIND DATASET
    # ======================================================

    def _find_dataset_file(

        self,

        dataset_path: str,

    ) -> Optional[Path]:

        path = Path(
            dataset_path
        )

        if path.is_file():

            if path.suffix.lower() in (
                ".json",
                ".jsonl",
            ):

                return path

        if path.is_dir():

            files = (

                list(
                    path.glob("*.jsonl")
                )

                +

                list(
                    path.glob("*.json")
                )

            )

            if files:

                return files[0]

        return None

    # ======================================================
    # LOAD DATASET
    # ======================================================

    def _load_dataset(

        self,

        dataset_file: Path,

    ) -> list:

        examples = []

        # --------------------------------------------------
        # JSONL
        # --------------------------------------------------

        if dataset_file.suffix.lower() == (
            ".jsonl"
        ):

            with open(

                dataset_file,

                "r",

                encoding="utf-8",

            ) as file:

                for line in file:

                    line = line.strip()

                    if not line:

                        continue

                    item = json.loads(
                        line
                    )

                    example = (
                        self._convert_example(
                            item
                        )
                    )

                    if example:

                        examples.append(
                            example
                        )

        # --------------------------------------------------
        # JSON
        # --------------------------------------------------

        elif dataset_file.suffix.lower() == (
            ".json"
        ):

            with open(

                dataset_file,

                "r",

                encoding="utf-8",

            ) as file:

                data = json.load(
                    file
                )

            if isinstance(

                data,

                dict,

            ):

                data = data.get(

                    "data",

                    data.get(

                        "examples",

                        []

                    ),

                )

            if isinstance(

                data,

                list,

            ):

                for item in data:

                    example = (

                        self._convert_example(

                            item

                        )

                    )

                    if example:

                        examples.append(

                            example

                        )

        return examples

    # ======================================================
    # NORMALIZE TRAINING EXAMPLE
    # ======================================================

    def _convert_example(

        self,

        item: Dict[str, Any],

    ) -> Optional[Dict[str, str]]:

        if not isinstance(

            item,

            dict,

        ):

            return None

        # Already formatted.
        if "text" in item:

            text = str(
                item["text"]
            ).strip()

            if text:

                return {

                    "text": text

                }

        # Instruction format.
        instruction = item.get(

            "instruction",

            item.get(

                "prompt",

                ""

            ),

        )

        response = item.get(

            "response",

            item.get(

                "output",

                item.get(

                    "completion",

                    ""

                ),

            ),

        )

        if instruction and response:

            text = (

                "### Instruction\n"

                f"{instruction}\n\n"

                "### Response\n"

                f"{response}"

            )

            return {

                "text": text

            }

        return None


# ==========================================================
# TRAINING MANAGER
# ==========================================================

class FineTuningTrainer:

    """
    Coordinates fine-tuning jobs.
    """

    def __init__(

        self,

        backend: Optional[
            FineTuningBackend
        ] = None,

    ):

        self.backend = (

            backend

            or MockTrainer()

        )

    # ======================================================
    # CREATE JOB
    # ======================================================

    def create_job(

        self,

        base_model: str,

        task_type: str,

        dataset_version: Any,

        dataset_path: str,

    ) -> Dict[str, Any]:

        if not base_model:

            raise ValueError(

                "base_model cannot be empty."

            )

        if not task_type:

            raise ValueError(

                "task_type cannot be empty."

            )

        return {

            "job_id":

                self._generate_job_id(

                    base_model,

                    task_type,

                    dataset_version,

                ),

            "base_model":

                base_model,

            "task_type":

                task_type,

            "dataset_version":

                dataset_version,

            "dataset_path":

                dataset_path,

            "created_at":

                datetime.now()
                .isoformat(),

            "status":

                "pending",

        }

    # ======================================================
    # TRAIN
    # ======================================================

    def train(

        self,

        job: Dict[str, Any],

    ) -> Dict[str, Any]:

        if not isinstance(

            job,

            dict,

        ):

            raise TypeError(

                "Training job must be a dictionary."

            )

        try:

            result = (

                self.backend.train(

                    job

                )

            )

        except Exception as exc:

            return {

                "success": False,

                "error":

                    str(exc),

                "artifact":

                    None,

            }

        if not isinstance(

            result,

            dict,

        ):

            return {

                "success": False,

                "error":

                    "Training backend returned an invalid result.",

                "artifact":

                    None,

            }

        return result

    # ======================================================
    # JOB ID
    # ======================================================

    def _generate_job_id(

        self,

        base_model: str,

        task_type: str,

        dataset_version: Any,

    ) -> str:

        source = (

            f"{base_model}|"
            f"{task_type}|"
            f"{dataset_version}|"
            f"{datetime.now().isoformat()}"

        )

        return (

            hashlib.sha256(

                source.encode(
                    "utf-8"
                )

            )

            .hexdigest()[:16]

        )


# ==========================================================
# REAL QLORA TEST
# ==========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "V.A.U.L.T. QLORA TRAINER TEST"
    )

    print("=" * 60)

    trainer = FineTuningTrainer(

        backend=QLoRATrainer()

    )

    job = trainer.create_job(

        base_model=(
            "Qwen/Qwen2.5-1.5B-Instruct"
        ),

        task_type="engineering",

        dataset_version=1,

        dataset_path=(
            "data/fine_tuning"
        ),

    )

    print()

    print("TRAINING JOB")

    print("-" * 60)

    print(job)

    print()

    print(
        "STARTING REAL QLORA TRAINING..."
    )

    result = trainer.train(

        job

    )

    print()

    print("TRAINING RESULT")

    print("-" * 60)

    print(result)

    print()

    print("=" * 60)

    print(
        "QLORA TRAINER TEST COMPLETE"
    )

    print("=" * 60)