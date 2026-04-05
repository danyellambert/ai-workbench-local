from __future__ import annotations

import hashlib
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_EVIDENCEOPS_REPOSITORY_SUFFIXES = {
    ".pdf",
    ".txt",
    ".md",
    ".csv",
    ".json",
}

_QUERY_SPLIT_REGEX = re.compile(r"\s+")


def _extract_document_id(path: Path) -> str | None:
    prefix = path.stem.split("_", 1)[0].strip()
    if not prefix:
        return None
    if "-" in prefix and any(character.isdigit() for character in prefix):
        return prefix
    return None


def _build_title(path: Path) -> str:
    stem = path.stem.strip()
    document_id = _extract_document_id(path)
    if document_id and stem.startswith(f"{document_id}_"):
        stem = stem[len(document_id) + 1 :]
    return stem.replace("_", " ").strip() or path.name


def _resolve_category(root: Path, path: Path) -> str:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return "external"
    if len(relative.parts) <= 1:
        return "root"
    return str(relative.parts[0])


def _normalize_optional_str(value: object) -> str:
    return str(value or "").strip()


def _normalize_suffix(value: object) -> str:
    normalized = _normalize_optional_str(value).lower()
    if not normalized:
        return ""
    return normalized if normalized.startswith(".") else f".{normalized}"


def _tokenize_query(query: str | None) -> list[str]:
    normalized = _normalize_optional_str(query).lower()
    if not normalized:
        return []
    return [token for token in _QUERY_SPLIT_REGEX.split(normalized) if token]


def _compute_document_fingerprint(path: Path) -> str:
    hasher = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except OSError:
        fallback = f"{path}:{path.stat().st_size if path.exists() else 0}:{int(path.stat().st_mtime) if path.exists() else 0}"
        return hashlib.sha256(fallback.encode("utf-8")).hexdigest()


def _compute_match_score(*, tokens: list[str], document: dict[str, Any]) -> float:
    if not tokens:
        return 0.0

    document_id = _normalize_optional_str(document.get("document_id")).lower()
    title = _normalize_optional_str(document.get("title")).lower()
    relative_path = _normalize_optional_str(document.get("relative_path")).lower()
    category = _normalize_optional_str(document.get("category")).lower()
    suffix = _normalize_optional_str(document.get("suffix")).lower()
    full_query = " ".join(tokens)
    score = 0.0

    for token in tokens:
        token_score = 0.0
        if document_id and token in document_id:
            token_score = max(token_score, 5.0)
        if title and token in title:
            token_score = max(token_score, 4.0)
        if relative_path and token in relative_path:
            token_score = max(token_score, 3.0)
        if category and token in category:
            token_score = max(token_score, 2.0)
        if suffix and token in suffix:
            token_score = max(token_score, 1.0)
        if token_score <= 0:
            return 0.0
        score += token_score

    if full_query and full_query in title:
        score += 2.5
    elif full_query and full_query in relative_path:
        score += 1.5
    return round(score, 3)


def _build_document_entry(
    root: Path,
    candidate: Path,
    *,
    include_fingerprint: bool = False,
) -> dict[str, Any]:
    document_category = _resolve_category(root, candidate)
    relative_path = str(candidate.relative_to(root))
    document_id = _extract_document_id(candidate)
    title = _build_title(candidate)
    stat = candidate.stat()
    payload = {
        "document_id": document_id,
        "title": title,
        "category": document_category,
        "relative_path": relative_path,
        "path": str(candidate),
        "suffix": candidate.suffix.lower(),
        "size_bytes": int(stat.st_size),
        "modified_at": int(stat.st_mtime),
    }
    if include_fingerprint:
        payload["fingerprint"] = _compute_document_fingerprint(candidate)
    return payload


def list_evidenceops_repository_documents(
    root: Path,
    *,
    query: str | None = None,
    category: str | None = None,
    suffix: str | None = None,
    document_id: str | None = None,
    limit: int | None = None,
    allowed_suffixes: set[str] | None = None,
    include_fingerprint: bool = False,
) -> list[dict[str, Any]]:
    if not root.exists() or not root.is_dir():
        return []

    query_tokens = _tokenize_query(query)
    normalized_category = _normalize_optional_str(category).lower()
    normalized_document_id = _normalize_optional_str(document_id).lower()
    normalized_suffix = _normalize_suffix(suffix)
    suffixes = {suffix.lower() for suffix in (allowed_suffixes or DEFAULT_EVIDENCEOPS_REPOSITORY_SUFFIXES)}

    documents: list[dict[str, Any]] = []
    for candidate in sorted(root.rglob("*")):
        if not candidate.is_file():
            continue
        if candidate.name.startswith("."):
            continue
        if candidate.suffix.lower() not in suffixes:
            continue

        document_category = _resolve_category(root, candidate)
        if normalized_category and document_category.lower() != normalized_category:
            continue
        if normalized_suffix and candidate.suffix.lower() != normalized_suffix:
            continue
        entry = _build_document_entry(root, candidate, include_fingerprint=include_fingerprint)
        entry_document_id = _normalize_optional_str(entry.get("document_id")).lower()
        if normalized_document_id and entry_document_id != normalized_document_id:
            continue
        match_score = _compute_match_score(tokens=query_tokens, document=entry)
        if query_tokens and match_score <= 0:
            continue
        if query_tokens:
            entry["match_score"] = match_score
        documents.append(entry)

    if query_tokens:
        documents = sorted(
            documents,
            key=lambda item: (
                -float(item.get("match_score") or 0.0),
                -int(item.get("modified_at") or 0),
                str(item.get("relative_path") or ""),
            ),
        )
    else:
        documents = sorted(documents, key=lambda item: str(item.get("relative_path") or ""))

    if isinstance(limit, int) and limit > 0:
        documents = documents[:limit]

    return documents


def search_evidenceops_repository_documents(
    root: Path,
    *,
    query: str,
    category: str | None = None,
    suffix: str | None = None,
    document_id: str | None = None,
    limit: int | None = None,
    allowed_suffixes: set[str] | None = None,
) -> list[dict[str, Any]]:
    return list_evidenceops_repository_documents(
        root,
        query=query,
        category=category,
        suffix=suffix,
        document_id=document_id,
        limit=limit,
        allowed_suffixes=allowed_suffixes,
    )


def build_evidenceops_repository_snapshot(
    root: Path,
    *,
    allowed_suffixes: set[str] | None = None,
) -> dict[str, Any]:
    documents = list_evidenceops_repository_documents(
        root,
        allowed_suffixes=allowed_suffixes,
        include_fingerprint=True,
    )
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "repository_root": str(root),
        "documents": [
            {
                "document_id": item.get("document_id"),
                "title": item.get("title"),
                "category": item.get("category"),
                "relative_path": item.get("relative_path"),
                "suffix": item.get("suffix"),
                "size_bytes": int(item.get("size_bytes") or 0),
                "modified_at": int(item.get("modified_at") or 0),
                "fingerprint": item.get("fingerprint"),
            }
            for item in documents
        ],
        "summary": summarize_evidenceops_repository_documents(documents),
    }


def diff_evidenceops_repository_snapshots(
    previous_snapshot: dict[str, Any] | None,
    current_snapshot: dict[str, Any] | None,
    *,
    detail_limit: int = 10,
) -> dict[str, Any]:
    previous_documents = previous_snapshot.get("documents") if isinstance(previous_snapshot, dict) else []
    current_documents = current_snapshot.get("documents") if isinstance(current_snapshot, dict) else []
    previous_map = {
        str(item.get("relative_path") or ""): item
        for item in previous_documents
        if isinstance(item, dict) and str(item.get("relative_path") or "").strip()
    }
    current_map = {
        str(item.get("relative_path") or ""): item
        for item in current_documents
        if isinstance(item, dict) and str(item.get("relative_path") or "").strip()
    }
    previous_paths = set(previous_map)
    current_paths = set(current_map)
    new_paths = sorted(current_paths - previous_paths)
    removed_paths = sorted(previous_paths - current_paths)
    changed_paths = sorted(
        path
        for path in (current_paths & previous_paths)
        if str(current_map[path].get("fingerprint") or "") != str(previous_map[path].get("fingerprint") or "")
    )

    def _snapshot_item_summary(item: dict[str, Any], *, previous: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {
            "document_id": item.get("document_id"),
            "title": item.get("title"),
            "category": item.get("category"),
            "relative_path": item.get("relative_path"),
            "suffix": item.get("suffix"),
            "size_bytes": int(item.get("size_bytes") or 0),
            "modified_at": int(item.get("modified_at") or 0),
        }
        if isinstance(previous, dict):
            payload["previous_modified_at"] = int(previous.get("modified_at") or 0)
            payload["previous_size_bytes"] = int(previous.get("size_bytes") or 0)
        return payload

    return {
        "has_previous_snapshot": bool(previous_map),
        "previous_captured_at": previous_snapshot.get("captured_at") if isinstance(previous_snapshot, dict) else None,
        "current_captured_at": current_snapshot.get("captured_at") if isinstance(current_snapshot, dict) else None,
        "previous_total_documents": len(previous_map),
        "current_total_documents": len(current_map),
        "new_documents_count": len(new_paths),
        "removed_documents_count": len(removed_paths),
        "changed_documents_count": len(changed_paths),
        "unchanged_documents_count": max(len(current_paths & previous_paths) - len(changed_paths), 0),
        "has_drift": bool(new_paths or removed_paths or changed_paths),
        "new_documents": [_snapshot_item_summary(current_map[path]) for path in new_paths[:detail_limit]],
        "removed_documents": [_snapshot_item_summary(previous_map[path]) for path in removed_paths[:detail_limit]],
        "changed_documents": [
            _snapshot_item_summary(current_map[path], previous=previous_map[path])
            for path in changed_paths[:detail_limit]
        ],
    }


def summarize_evidenceops_repository_documents(documents: list[dict[str, Any]]) -> dict[str, Any]:
    if not documents:
        return {
            "total_documents": 0,
            "total_categories": 0,
            "total_size_bytes": 0,
            "category_counts": {},
            "suffix_counts": {},
            "latest_document": None,
        }

    category_counter: Counter[str] = Counter()
    suffix_counter: Counter[str] = Counter()
    total_size_bytes = 0
    latest_document = None
    latest_modified_at = -1

    for document in documents:
        category = str(document.get("category") or "root").strip() or "root"
        suffix = str(document.get("suffix") or "").strip().lower()
        size_bytes = int(document.get("size_bytes") or 0)
        modified_at = int(document.get("modified_at") or 0)
        category_counter[category] += 1
        if suffix:
            suffix_counter[suffix] += 1
        total_size_bytes += size_bytes
        if modified_at >= latest_modified_at:
            latest_modified_at = modified_at
            latest_document = {
                "document_id": document.get("document_id"),
                "title": document.get("title"),
                "category": document.get("category"),
                "relative_path": document.get("relative_path"),
            }

    return {
        "total_documents": len(documents),
        "total_categories": len(category_counter),
        "total_size_bytes": total_size_bytes,
        "category_counts": dict(category_counter),
        "suffix_counts": dict(suffix_counter),
        "latest_document": latest_document,
    }