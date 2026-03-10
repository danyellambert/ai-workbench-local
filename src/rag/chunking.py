def chunk_text(text: str, chunk_size: int, chunk_overlap: int, source_name: str) -> list[dict[str, object]]:
    normalized_text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
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
                {
                    "chunk_id": chunk_id,
                    "source": source_name,
                    "text": chunk_text_value,
                    "start_char": start,
                    "end_char": end,
                    "snippet": chunk_text_value[:400],
                }
            )
            chunk_id += 1

        if end >= len(normalized_text):
            break
        start += step

    return chunks