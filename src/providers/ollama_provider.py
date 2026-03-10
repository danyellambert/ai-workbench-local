import subprocess

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

    def stream_chat_completion(self, messages: list[dict[str, str]], model: str, temperature: float):
        return self.client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temperature,
            stream=True,
        )

    def create_embeddings(self, texts: list[str], model: str) -> list[list[float]]:
        response = self.client.embeddings.create(model=model, input=texts)
        return [item.embedding for item in response.data]

    @staticmethod
    def iter_stream_text(stream):
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