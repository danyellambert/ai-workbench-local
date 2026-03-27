from __future__ import annotations


SUPPORTED_CHUNKING_STRATEGIES = ("manual", "langchain_recursive")


def _normalize_text(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def describe_chunking_strategy(strategy: str) -> str:
    labels = {
        "manual": "Manual local",
        "langchain_recursive": "LangChain Recursive (experimental)",
    }
    return labels.get((strategy or "").strip().lower(), strategy or "manual")


def resolve_chunking_strategy(strategy: str | None) -> tuple[str, str, str | None]:
    requested = (strategy or "manual").strip().lower() or "manual"
    if requested == "manual":
        return requested, "manual", None
    if requested == "langchain_recursive":
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter  # noqa: F401
        except Exception:
            return requested, "manual", "langchain_text_splitters_not_installed"
        return requested, "langchain_recursive", None
    return requested, "manual", "unknown_strategy"


def _build_chunk_record(
    *,
    chunk_id: int,
    source_name: str,
    text: str,
    start_char: int,
    end_char: int,
    requested_strategy: str,
    effective_strategy: str,
    fallback_reason: str | None,
) -> dict[str, object]:
    record = {
        "chunk_id": chunk_id,
        "source": source_name,
        "text": text,
        "start_char": start_char,
        "end_char": end_char,
        "snippet": text[:400],
        "chunking_strategy_requested": requested_strategy,
        "chunking_strategy_used": effective_strategy,
    }
    if fallback_reason:
        record["chunking_strategy_fallback_reason"] = fallback_reason
    return record


def _chunk_text_manual(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    source_name: str,
    *,
    requested_strategy: str,
    effective_strategy: str,
    fallback_reason: str | None,
) -> list[dict[str, object]]:
    normalized_text = _normalize_text(text)
    if not normalized_text:
        return []

    chunk_size = max(chunk_size, 200)
    chunk_overlap = min(max(chunk_overlap, 0), chunk_size // 2)
    step = max(chunk_size - chunk_overlap, 1)

    chunks: list[dict[str, object]] = []
    start = 0
    chunk_id = 1

    while start < len(normalized_text):
        end = min(start + chunk_size, len(normalized_text))
        chunk_text_value = normalized_text[start:end].strip()
        if chunk_text_value:
            chunks.append(
                _build_chunk_record(
                    chunk_id=chunk_id,
                    source_name=source_name,
                    text=chunk_text_value,
                    start_char=start,
                    end_char=end,
                    requested_strategy=requested_strategy,
                    effective_strategy=effective_strategy,
                    fallback_reason=fallback_reason,
                )
            )
            chunk_id += 1

        if end >= len(normalized_text):
            break
        start += step

    return chunks


def _chunk_text_langchain_recursive(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    source_name: str,
    *,
    requested_strategy: str,
    fallback_reason: str | None,
) -> list[dict[str, object]]:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    normalized_text = _normalize_text(text)
    if not normalized_text:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max(chunk_size, 200),
        chunk_overlap=min(max(chunk_overlap, 0), max(chunk_size, 200) // 2),
        add_start_index=True,
    )
    documents = splitter.create_documents([normalized_text])

    chunks: list[dict[str, object]] = []
    cursor = 0
    for chunk_id, document in enumerate(documents, start=1):
        chunk_text_value = str(document.page_content or "").strip()
        if not chunk_text_value:
            continue
        metadata = getattr(document, "metadata", {}) or {}
        start_char = metadata.get("start_index")
        if not isinstance(start_char, int) or start_char < 0:
            start_char = normalized_text.find(chunk_text_value, cursor)
            if start_char < 0:
                start_char = cursor
        end_char = min(start_char + len(chunk_text_value), len(normalized_text))
        cursor = end_char
        chunks.append(
            _build_chunk_record(
                chunk_id=chunk_id,
                source_name=source_name,
                text=chunk_text_value,
                start_char=start_char,
                end_char=end_char,
                requested_strategy=requested_strategy,
                effective_strategy="langchain_recursive",
                fallback_reason=fallback_reason,
            )
        )
    return chunks


def chunk_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    source_name: str,
    *,
    strategy: str = "manual",
) -> list[dict[str, object]]:
    requested_strategy, effective_strategy, fallback_reason = resolve_chunking_strategy(strategy)
    if effective_strategy == "langchain_recursive":
        return _chunk_text_langchain_recursive(
            text,
            chunk_size,
            chunk_overlap,
            source_name,
            requested_strategy=requested_strategy,
            fallback_reason=fallback_reason,
        )

    return _chunk_text_manual(
        text,
        chunk_size,
        chunk_overlap,
        source_name,
        requested_strategy=requested_strategy,
        effective_strategy=effective_strategy,
        fallback_reason=fallback_reason,
    )