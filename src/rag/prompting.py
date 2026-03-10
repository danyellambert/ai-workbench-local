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


def inject_rag_context(messages: list[dict[str, str]], chunks: list[dict[str, object]]) -> list[dict[str, str]]:
    if not chunks:
        return messages

    context_block = build_rag_context(chunks)
    if not context_block:
        return messages

    rag_instruction = {
        "role": "system",
        "content": (
            "Use o contexto recuperado abaixo para responder com base no documento sempre que ele for relevante. "
            "Se a resposta não estiver no contexto, diga isso claramente.\n\n"
            f"Contexto recuperado:\n{context_block}"
        ),
    }

    return [messages[0], rag_instruction, *messages[1:]] if messages else [rag_instruction]