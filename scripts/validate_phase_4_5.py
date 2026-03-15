from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VENV_SITE_PACKAGES = PROJECT_ROOT / ".venv" / "lib" / "python3.14" / "site-packages"
for candidate in [PROJECT_ROOT, VENV_SITE_PACKAGES]:
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import types

if "openai" not in sys.modules:
    fake_openai = types.ModuleType("openai")

    class DummyOpenAI:
        def __init__(self, *args, **kwargs):
            pass

        class embeddings:
            @staticmethod
            def create(*args, **kwargs):
                raise RuntimeError("DummyOpenAI embeddings should not be used in this validation script.")

    fake_openai.OpenAI = DummyOpenAI
    sys.modules["openai"] = fake_openai

from src.config import OllamaSettings, RagSettings
from src.providers import ollama_provider as ollama_module
from src.providers.ollama_provider import OllamaProvider
from src.rag.loaders import LoadedDocument
from src.rag.prompting import estimate_rag_context_budget_chars, inject_rag_context
from src.rag.service import (
    build_source_metadata,
    clear_persisted_rag_index,
    get_indexed_documents,
    inspect_vector_backend_status,
    remove_documents_from_rag_index,
    retrieve_relevant_chunks_detailed,
    upsert_documents_in_rag_index,
)
from src.rag.vector_store import ChromaVectorStore


class FakeEmbeddingProvider:
    def create_embeddings(self, texts: list[str], model: str) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for text in texts:
            lowered = text.lower()
            embeddings.append(
                [
                    float(lowered.count("python") + lowered.count("codigo") + lowered.count("função") + 1),
                    float(lowered.count("clima") + lowered.count("tempo") + lowered.count("chuva") + 1),
                    float(len(text) % 17 + 1),
                ]
            )
        return embeddings



def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)



def validate_rag_flow() -> str:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        settings = RagSettings(
            embedding_model="fake-embed",
            chunk_size=80,
            chunk_overlap=10,
            top_k=2,
            store_path=tmp_path / ".rag_store.json",
            chroma_path=tmp_path / ".chroma_rag",
            rerank_pool_size=4,
            rerank_lexical_weight=0.4,
            context_budget_ratio=0.25,
            context_budget_min_chars=200,
            context_budget_max_chars=600,
        )
        embedding_provider = FakeEmbeddingProvider()
        documents = [
            LoadedDocument(
                name="manual_python.md",
                file_type="md",
                text=(
                    "Python é útil para automação e código. "
                    "Uma função bem definida ajuda a organizar o código. "
                )
                * 8,
                file_hash="doc-python",
            ),
            LoadedDocument(
                name="clima.txt",
                file_type="txt",
                text=(
                    "O clima hoje tem chuva fraca e previsão do tempo instável. "
                    "O relatório de clima ajuda no planejamento. "
                )
                * 8,
                file_hash="doc-clima",
            ),
        ]

        rag_index, sync_status = upsert_documents_in_rag_index(
            documents=documents,
            settings=settings,
            embedding_provider=embedding_provider,
        )
        assert_true(sync_status.get("backend") in {"chroma", "local_fallback"}, "A sincronização vetorial deve reportar status explícito.")
        indexed_documents = get_indexed_documents(rag_index, settings)
        assert_true(len(indexed_documents) == 2, "O catálogo multi-arquivo deve conter 2 documentos.")
        assert_true(len(rag_index.get("chunks", [])) >= 2, "A indexação precisa gerar chunks.")

        retrieval = retrieve_relevant_chunks_detailed(
            query="Como organizar código em Python?",
            rag_index=rag_index,
            settings=settings,
            embedding_provider=embedding_provider,
            document_ids=["doc-python"],
            file_types=["md"],
        )
        retrieved = retrieval["chunks"]
        assert_true(retrieved, "A recuperação precisa retornar ao menos um chunk.")
        assert_true(all(chunk.get("document_id") == "doc-python" for chunk in retrieved), "O filtro por documento deve ser respeitado.")
        assert_true(retrieval.get("reranking_applied") is True, "O retrieval deve expor reranking híbrido ativo.")
        assert_true((retrieval.get("candidate_pool_size") or 0) >= settings.top_k, "O candidate pool do reranking deve ser maior ou igual ao top-k final.")

        prompt_messages, prompt_details = inject_rag_context(
            [{"role": "user", "content": "Explique o documento."}],
            retrieved,
            context_window=1024,
            settings=settings,
        )
        assert_true(len(prompt_messages) >= 2, "O prompt precisa receber contexto documental injetado.")
        assert_true(prompt_details.get("budget_chars") == estimate_rag_context_budget_chars(1024, settings), "O budget operacional deve ser calculado de forma determinística.")
        assert_true(prompt_details.get("used_chunks") >= 1, "Ao menos um chunk deve caber no orçamento do prompt.")

        sources = build_source_metadata(prompt_details.get("context_chunks") or retrieved)
        assert_true(bool(sources) and sources[0].get("source"), "As fontes precisam ser geradas para o chat.")

        chroma_status = retrieval.get("backend_used")
        try:
            chroma_store = ChromaVectorStore(settings.chroma_path)
            chroma_results = chroma_store.similarity_search([5.0, 1.0, 2.0], top_k=2)
            assert_true(len(chroma_results) >= 1, "O Chroma local precisa responder consultas top-k.")
            chroma_status = "chroma"
        except Exception:
            chroma_status = "fallback"

        updated_rag_index, removal_status = remove_documents_from_rag_index(
            rag_index=rag_index,
            settings=settings,
            document_ids=["doc-clima"],
        )
        assert_true(removal_status.get("backend") in {"chroma", "local_fallback"}, "A remoção deve ressincar o backend vetorial.")
        assert_true(updated_rag_index is not None, "A remoção seletiva não deve limpar toda a base quando sobra 1 documento.")
        remaining_docs = get_indexed_documents(updated_rag_index, settings)
        assert_true(len(remaining_docs) == 1, "A remoção seletiva deve deixar apenas um documento.")
        backend_status = inspect_vector_backend_status(updated_rag_index, settings)
        assert_true(backend_status.get("status") in {"sincronizado", "fallback_local"}, "O projeto deve expor o estado do backend vetorial após a remoção.")

        clear_status = clear_persisted_rag_index(settings)
        assert_true(clear_status.get("persist_dir_exists") is False, "O clear da Fase 4.5 deve apagar fisicamente a pasta do Chroma.")
        assert_true(not settings.chroma_path.exists(), "O persist dir do Chroma não deve permanecer em disco após o clear físico.")

        return chroma_status



def validate_ollama_native_path() -> None:
    settings = OllamaSettings(
        project_name="AI Workbench Local",
        base_url="http://localhost:11434/v1",
        default_model="qwen2.5-coder:7b",
        default_temperature=0.2,
        default_context_window=8192,
        default_prompt_profile="neutro",
        available_models_env=[],
        history_path=Path(".chat_history.json"),
    )
    provider = OllamaProvider(settings)

    captured: dict[str, object] = {}

    class DummyResponse:
        def __iter__(self):
            return iter(())

    original_urlopen = ollama_module.urllib_request.urlopen
    try:
        def fake_urlopen(request, timeout=300):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return DummyResponse()

        ollama_module.urllib_request.urlopen = fake_urlopen
        provider.stream_chat_completion(
            messages=[{"role": "user", "content": "teste"}],
            model="qwen2.5-coder:7b",
            temperature=0.3,
            context_window=16384,
        )
    finally:
        ollama_module.urllib_request.urlopen = original_urlopen

    assert_true(str(captured.get("url", "")).endswith("/api/chat"), "O caminho nativo do Ollama deve usar /api/chat.")
    body = captured.get("body")
    assert_true(isinstance(body, dict), "O payload do Ollama deve ser JSON.")
    body = body or {}
    assert_true(body.get("options", {}).get("num_ctx") == 16384, "O payload nativo precisa enviar num_ctx.")

    provider._native_json_request = lambda path, payload: {
        "model_info": {"llama.context_length": 32768},
        "modified_at": "2026-03-13T00:00:00Z",
    }
    provider._read_ollama_ps_context = lambda model: 16384
    inspection = provider.inspect_context_window("qwen2.5-coder:7b", requested_context_window=16384)
    assert_true(inspection.get("declared_context_length") == 32768, "A inspeção deve ler o contexto declarado do modelo.")
    assert_true(inspection.get("ollama_ps_context") == 16384, "A inspeção deve incorporar o contexto observado no runtime.")



def main() -> None:
    chroma_status = validate_rag_flow()
    if chroma_status == "chroma":
        print("[ok] Fluxo RAG multi-arquivo validado com Chroma, reranking híbrido, budget de contexto e clear físico.")
    else:
        print("[ok] Fluxo RAG multi-arquivo validado com fallback seguro, reranking híbrido, budget de contexto e clear físico.")

    validate_ollama_native_path()
    print("[ok] Caminho nativo do Ollama validado com envio de num_ctx e inspeção técnica.")
    print("[ok] Fase 4.5: validação técnica automatizada concluída.")


if __name__ == "__main__":
    main()
