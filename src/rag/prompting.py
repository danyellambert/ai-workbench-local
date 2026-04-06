from __future__ import annotations

from src.config import RagSettings


def estimate_rag_context_budget_chars(context_window: int, settings: RagSettings) -> int:
    estimated = int(max(context_window, 1) * max(settings.context_chars_per_token, 1.0) * max(settings.context_budget_ratio, 0.05))
    estimated = max(estimated, settings.context_budget_min_chars)
    if settings.context_budget_max_chars > 0:
        estimated = min(estimated, settings.context_budget_max_chars)
    return estimated



def build_rag_context(chunks: list[dict[str, object]]) -> str:
    if not chunks:
        return ""

    parts = []
    for index, chunk in enumerate(chunks, start=1):
        source = chunk.get("source", "documento")
        chunk_id = chunk.get("chunk_id", index)
        text = chunk.get("text", "")
        parts.append(f"[Fonte {index} | {source} | chunk {chunk_id}]\n{text}")

    return "\n\n".join(parts)



def select_chunks_for_prompt_budget(
    chunks: list[dict[str, object]],
    budget_chars: int,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    if not chunks:
        return [], {
            "budget_chars": budget_chars,
            "used_chars": 0,
            "used_chunks": 0,
            "dropped_chunks": 0,
            "truncated": False,
        }

    selected_chunks: list[dict[str, object]] = []
    used_chars = 0

    for index, chunk in enumerate(chunks, start=1):
        source = chunk.get("source", "documento")
        chunk_id = chunk.get("chunk_id", index)
        text = str(chunk.get("text", ""))
        chunk_block = f"[Fonte {index} | {source} | chunk {chunk_id}]\n{text}"
        block_size = len(chunk_block) + (2 if selected_chunks else 0)

        if selected_chunks and used_chars + block_size > budget_chars:
            break
        if not selected_chunks and block_size > budget_chars:
            truncated_text = text[: max(budget_chars - 120, 300)]
            selected_chunks.append({**chunk, "text": truncated_text, "snippet": truncated_text[:400]})
            used_chars = len(f"[Fonte {index} | {source} | chunk {chunk_id}]\n{truncated_text}")
            break

        selected_chunks.append(chunk)
        used_chars += block_size

    details = {
        "budget_chars": budget_chars,
        "used_chars": used_chars,
        "used_chunks": len(selected_chunks),
        "dropped_chunks": max(len(chunks) - len(selected_chunks), 0),
        "truncated": len(selected_chunks) < len(chunks),
    }
    return selected_chunks, details



def inject_rag_context(
    messages: list[dict[str, str]],
    chunks: list[dict[str, object]],
    *,
    context_window: int,
    settings: RagSettings,
) -> tuple[list[dict[str, str]], dict[str, object]]:
    if not chunks:
        budget = estimate_rag_context_budget_chars(context_window, settings)
        return messages, {
            "budget_chars": budget,
            "used_chars": 0,
            "used_chunks": 0,
            "dropped_chunks": 0,
            "truncated": False,
            "context_injected": False,
        }

    budget_chars = estimate_rag_context_budget_chars(context_window, settings)
    selected_chunks, budget_details = select_chunks_for_prompt_budget(chunks, budget_chars)
    context_block = build_rag_context(selected_chunks)
    if not context_block:
        return messages, {
            **budget_details,
            "context_injected": False,
            "context_chunks": [],
        }

    rag_instruction = {
        "role": "system",
        "content": (
            "Use o contexto recuperado abaixo para responder com base no documento sempre que ele for relevante. "
            "Se a resposta não estiver no contexto, diga isso claramente.\n\n"
            f"Contexto recuperado:\n{context_block}"
        ),
    }

    injected_messages = [messages[0], rag_instruction, *messages[1:]] if messages else [rag_instruction]
    return injected_messages, {
        **budget_details,
        "context_injected": True,
        "context_chunks": selected_chunks,
        "context_preview_chars": len(context_block),
    }
