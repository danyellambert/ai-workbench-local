import json
import subprocess
from urllib import request as urllib_request

from openai import OpenAI

from src.config import OllamaSettings


class OllamaProvider:
    FALLBACK_MODELS = [
        "qwen2.5-coder:7b",
        "qwen2.5-coder:14b",
        "deepseek-coder:6.7b",
        "qwen3-coder:480b-cloud",
    ]

    def __init__(self, settings: OllamaSettings):
        self.settings = settings
        self.client = OpenAI(base_url=settings.base_url, api_key="ollama")
        self.native_base_url = self._build_native_base_url(settings.base_url)

    @staticmethod
    def _build_native_base_url(base_url: str) -> str:
        normalized = base_url.rstrip("/")
        if normalized.endswith("/v1"):
            normalized = normalized[:-3]
        return normalized

    def list_available_models(self) -> list[str]:
        discovered_models: list[str] = []

        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines()[1:]:
                    parts = line.split()
                    if parts:
                        discovered_models.append(parts[0])
        except OSError:
            pass

        ordered_models: list[str] = []
        for model in [
            self.settings.default_model,
            *self.settings.available_models_env,
            *discovered_models,
            *self.FALLBACK_MODELS,
        ]:
            if model and model not in ordered_models:
                ordered_models.append(model)

        return ordered_models

    def stream_chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        context_window: int | None = None,
    ):
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
            },
        }

        if context_window:
            payload["options"]["num_ctx"] = int(context_window)

        request = urllib_request.Request(
            url=f"{self.native_base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        return urllib_request.urlopen(request, timeout=300)

    def create_embeddings(self, texts: list[str], model: str) -> list[list[float]]:
        response = self.client.embeddings.create(model=model, input=texts)
        return [item.embedding for item in response.data]

    @staticmethod
    def iter_stream_text(stream):
        if hasattr(stream, "__iter__") and not hasattr(stream, "choices"):
            for raw_line in stream:
                if isinstance(raw_line, bytes):
                    line = raw_line.decode("utf-8", errors="ignore").strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    message = payload.get("message")
                    if isinstance(message, dict):
                        content = message.get("content") or ""
                        if content:
                            yield content
            return

        for chunk in stream:
            if not getattr(chunk, "choices", None):
                continue

            delta = getattr(chunk.choices[0], "delta", None)
            content = getattr(delta, "content", None) or ""
            if content:
                yield content

    def format_error(self, model: str, error: Exception) -> str:
        return (
            "Não foi possível obter resposta do Ollama.\n\n"
            "Verifique se:\n"
            f"- o servidor está ativo em `{self.settings.base_url}`\n"
            f"- o modelo `{model}` está instalado\n"
            "- o Ollama está respondendo normalmente\n\n"
            f"Detalhes técnicos: {error}"
        )