"""FinBERT sentiment model -- requires ``transformers`` and ``torch``.

Falls back gracefully when dependencies are not installed: the model
registers itself in the :class:`NLPModelRegistry`, but ``is_available``
returns ``False`` so the pipeline can fall back to the baseline.

Supports fine-tuning on custom earnings-call data.
"""

from __future__ import annotations

import logging

from models.nlp_signals.base import BaseNLPSignalModel, NLPModelRegistry, NLPSignal

logger = logging.getLogger(__name__)


def _check_transformers() -> bool:
    """Return True when both transformers and torch are importable."""
    try:
        import transformers  # noqa: F401
        import torch  # noqa: F401

        return True
    except ImportError:
        return False


class FinBERTModel(BaseNLPSignalModel):
    """FinBERT sentiment model.

    Requires ``transformers`` and ``torch``.  When those packages are not
    installed, ``is_available`` returns ``False`` and ``predict_sentiment``
    raises a clear ``ImportError``.
    """

    MODEL_NAME = "ProsusAI/finbert"  # Default pretrained model

    def __init__(self, model_path: str | None = None) -> None:
        self._model_path = model_path or self.MODEL_NAME
        self._pipeline = None

    # -- BaseNLPSignalModel interface ----------------------------------------

    @property
    def name(self) -> str:
        return "finbert"

    @property
    def is_available(self) -> bool:
        return _check_transformers()

    def _load_pipeline(self) -> None:
        if self._pipeline is not None:
            return
        if not self.is_available:
            raise ImportError(
                "transformers and torch required for FinBERT. "
                "pip install transformers torch"
            )
        from transformers import pipeline  # type: ignore[import-untyped]

        self._pipeline = pipeline(
            "sentiment-analysis",
            model=self._model_path,
            tokenizer=self._model_path,
            truncation=True,
            max_length=512,
        )
        logger.info("FinBERT loaded from %s", self._model_path)

    def predict_sentiment(
        self, text: str, ticker: str = "", date: str = ""
    ) -> NLPSignal:
        self._load_pipeline()
        result = self._pipeline(text[:512])[0]  # type: ignore[index]
        label = result["label"].lower()
        score_raw: float = result["score"]

        # Map FinBERT labels to signal values
        if label == "positive":
            signal_value = score_raw
        elif label == "negative":
            signal_value = -score_raw
        else:  # neutral
            signal_value = 0.0

        return NLPSignal(
            ticker=ticker,
            date=date,
            signal_value=signal_value,
            confidence=score_raw,
            model_name=self.name,
            metadata={"raw_label": label, "raw_score": score_raw},
        )

    def predict_batch(self, texts: list[dict]) -> list[NLPSignal]:
        self._load_pipeline()
        text_list = [t["text"][:512] for t in texts]
        results = self._pipeline(text_list)  # type: ignore[misc]
        signals: list[NLPSignal] = []
        for t, r in zip(texts, results):
            label = r["label"].lower()
            score: float = r["score"]
            if label == "positive":
                sv = score
            elif label == "negative":
                sv = -score
            else:
                sv = 0.0
            signals.append(
                NLPSignal(
                    ticker=t.get("ticker", ""),
                    date=t.get("date", ""),
                    signal_value=sv,
                    confidence=score,
                    model_name=self.name,
                    metadata={"raw_label": label, "raw_score": score},
                )
            )
        return signals

    # -- Fine-tuning ---------------------------------------------------------

    def fine_tune(
        self,
        training_data: list[dict],
        output_dir: str = "models/fine_tuned/finbert",
        epochs: int = 3,
        batch_size: int = 16,
        learning_rate: float = 2e-5,
        **kwargs,
    ) -> dict:
        """Fine-tune FinBERT on custom data.

        Parameters
        ----------
        training_data:
            List of ``{"text": str, "label": "positive"|"negative"|"neutral"}``.
        output_dir:
            Where to save the fine-tuned model.
        epochs:
            Number of training epochs.
        batch_size:
            Per-device batch size.
        learning_rate:
            Peak learning rate.

        Returns
        -------
        dict with ``loss``, ``epochs``, and ``output_dir``.
        """
        if not self.is_available:
            raise ImportError("transformers and torch required for fine-tuning")

        from transformers import (  # type: ignore[import-untyped]
            AutoModelForSequenceClassification,
            AutoTokenizer,
            Trainer,
            TrainingArguments,
        )
        import torch  # type: ignore[import-untyped]

        tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
        model = AutoModelForSequenceClassification.from_pretrained(
            self.MODEL_NAME, num_labels=3
        )

        label_map = {"positive": 0, "negative": 1, "neutral": 2}

        class FinDataset(torch.utils.data.Dataset):  # type: ignore[type-arg]
            def __init__(self, data: list[dict], tok) -> None:  # noqa: ANN001
                self.encodings = tok(
                    [d["text"] for d in data],
                    truncation=True,
                    padding=True,
                    max_length=512,
                    return_tensors="pt",
                )
                self.labels = torch.tensor(
                    [label_map.get(d["label"], 2) for d in data]
                )

            def __len__(self) -> int:
                return len(self.labels)

            def __getitem__(self, idx: int) -> dict:
                item = {k: v[idx] for k, v in self.encodings.items()}
                item["labels"] = self.labels[idx]
                return item

        dataset = FinDataset(training_data, tokenizer)

        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            learning_rate=learning_rate,
            save_strategy="epoch",
            logging_steps=10,
        )

        trainer = Trainer(
            model=model, args=training_args, train_dataset=dataset
        )
        train_result = trainer.train()
        trainer.save_model(output_dir)
        tokenizer.save_pretrained(output_dir)

        # Reset so next predict loads the fine-tuned model
        self._model_path = output_dir
        self._pipeline = None

        return {
            "loss": train_result.training_loss,
            "epochs": epochs,
            "output_dir": output_dir,
        }

    # -- Persistence ---------------------------------------------------------

    def save(self, path: str) -> None:
        if self._pipeline and hasattr(self._pipeline.model, "save_pretrained"):
            self._pipeline.model.save_pretrained(path)

    def load(self, path: str) -> None:
        self._model_path = path
        self._pipeline = None  # Will reload on next predict


NLPModelRegistry.register(FinBERTModel)
