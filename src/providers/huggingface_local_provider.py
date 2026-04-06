from __future__ import annotations

from src.config import HuggingFaceSettings


class HuggingFaceLocalProvider:
    def __init__(self, settings: HuggingFaceSettings):
        self.settings = settings
        self._generation_pipelines: dict[str, object] = {}
        self._embedding_models: dict[str, object] = {}
        self._last_usage_metrics: dict[str, object] = {}

    def reset_last_usage_metrics(self) -> None:
        self._last_usage_metrics = {}

    def get_last_usage_metrics(self) -> dict[str, object]:
        return dict(self._last_usage_metrics)

    @staticmethod
    def supports_generation_runtime() -> bool:
        try:
            import transformers  # noqa: F401
        except Exception:
            return False
        return True

    @staticmethod
    def supports_embedding_runtime() -> bool:
        try:
            import sentence_transformers  # noqa: F401
        except Exception:
            return False
        return True

    def list_available_models(self) -> list[str]:
        ordered_models: list[str] = []
        for model in [self.settings.model, *self.settings.available_models_env]:
            if model and model not in ordered_models:
                ordered_models.append(model)
        return ordered_models

    def list_available_embedding_models(self) -> list[str]:
        ordered_models: list[str] = []
        for model in [self.settings.embedding_model, *self.settings.available_embedding_models_env]:
            if model and model not in ordered_models:
                ordered_models.append(model)
        return ordered_models

    def inspect_context_window(self, model: str, requested_context_window: int | None = None) -> dict[str, object]:
        return {
            "runtime": "huggingface_local",
            "generation_task": self.settings.generation_task,
            "requested_num_ctx": int(requested_context_window) if requested_context_window else None,
            "model": model,
            "prompt_serialization_mode": "tokenizer_chat_template_if_available_else_manual_role_prompt",
            "chat_template_verification": "runtime_checked_during_generation",
            "validation_summary": (
                "Local Transformers-based providers do not expose a universal equivalent to Ollama's `num_ctx`. "
                "The value configured in the app works as an operational budget and observability reference. "
                "When the local tokenizer exposes a chat template, the provider uses it; otherwise it falls back to manual role-based serialization."
            ),
        }

    def inspect_embedding_context_window(self, model: str, requested_context_window: int | None = None) -> dict[str, object]:
        return {
            "runtime": "huggingface_local",
            "requested_num_ctx": int(requested_context_window) if requested_context_window else None,
            "model": model,
            "validation_summary": (
                "Embeddings through the Hugging Face ecosystem depend on the concrete model implementation. "
                "The app records the configured value as operational metadata without assuming universal context control."
            ),
        }

    def _format_messages_as_prompt(self, messages: list[dict[str, str]], tokenizer: object | None = None) -> tuple[str, dict[str, object]]:
        if tokenizer is not None and hasattr(tokenizer, "apply_chat_template") and getattr(tokenizer, "chat_template", None):
            try:
                prompt = tokenizer.apply_chat_template(  # type: ignore[attr-defined]
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
                if isinstance(prompt, str) and prompt.strip():
                    return prompt, {
                        "prompt_serialization_mode": "tokenizer_chat_template",
                        "chat_template_used": True,
                        "chat_template_source": "transformers_tokenizer",
                    }
            except Exception:
                pass

        lines: list[str] = []
        for message in messages:
            role = str(message.get("role") or "user").upper()
            content = str(message.get("content") or "").strip()
            if content:
                lines.append(f"{role}: {content}")
        lines.append("ASSISTANT:")
        return "\n".join(lines), {
            "prompt_serialization_mode": "manual_role_prompt",
            "chat_template_used": False,
            "chat_template_source": None,
        }

    def _load_generation_pipeline(self, model: str):
        cached = self._generation_pipelines.get(model)
        if cached is not None:
            return cached
        if not self.supports_generation_runtime():
            raise RuntimeError("Transformers is not installed, so the local Hugging Face provider cannot be enabled.")
        from transformers import pipeline

        pipe = pipeline(self.settings.generation_task, model=model)
        self._generation_pipelines[model] = pipe
        return pipe

    def stream_chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        context_window: int | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
        think: bool | None = None,
    ):
        self.reset_last_usage_metrics()
        pipe = self._load_generation_pipeline(model)
        prompt, prompt_metadata = self._format_messages_as_prompt(
            messages,
            tokenizer=getattr(pipe, "tokenizer", None),
        )
        self._last_usage_metrics = {
            **self._last_usage_metrics,
            **prompt_metadata,
            "usage_source": "huggingface_local_runtime_metadata",
        }
        resolved_top_p = top_p if top_p is not None else self.settings.top_p
        resolved_max_tokens = max_tokens if max_tokens is not None else self.settings.max_new_tokens
        generate_kwargs: dict[str, object] = {
            "max_new_tokens": int(resolved_max_tokens),
            "do_sample": bool(temperature and temperature > 0.0),
        }
        if temperature and temperature > 0.0:
            generate_kwargs["temperature"] = max(float(temperature), 0.1)
        if resolved_top_p is not None:
            generate_kwargs["top_p"] = float(resolved_top_p)
        result = pipe(prompt, **generate_kwargs)
        generated_text = ""
        if isinstance(result, list) and result:
            first_item = result[0]
            if isinstance(first_item, dict):
                generated_text = str(first_item.get("generated_text") or "")
            else:
                generated_text = str(first_item)
        else:
            generated_text = str(result)
        if generated_text.startswith(prompt):
            generated_text = generated_text[len(prompt):]
        return [generated_text.strip()]

    def create_embeddings(
        self,
        texts: list[str],
        model: str,
        context_window: int | None = None,
        truncate: bool = True,
    ) -> list[list[float]]:
        if not texts:
            return []
        if not self.supports_embedding_runtime():
            raise RuntimeError("sentence-transformers is not installed for local Hugging Face embeddings.")
        cached = self._embedding_models.get(model)
        if cached is None:
            from sentence_transformers import SentenceTransformer

            cached = SentenceTransformer(model)
            self._embedding_models[model] = cached
        embeddings = cached.encode(texts, normalize_embeddings=False)
        return [vector.tolist() for vector in embeddings]

    @staticmethod
    def iter_stream_text(stream):
        for chunk in stream:
            if isinstance(chunk, bytes):
                text = chunk.decode("utf-8", errors="ignore")
            else:
                text = str(chunk)
            if text:
                yield text

    def format_error(self, model: str, error: Exception) -> str:
        return (
            f"Could not get a response from the local Hugging Face provider using model `{model}`. "
            f"Details: {error}"
        )