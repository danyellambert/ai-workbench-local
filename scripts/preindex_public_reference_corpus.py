#!/usr/bin/env python3
"""Build the hidden public-reference corpus index used by fast Nextcloud demo imports.

Run this once on the machine that has Ollama/Nextcloud credentials. The script
writes a separate RAG JSON store, so the visible document library stays empty
until a user imports documents from Nextcloud in the UI.

When ``--force-vlm`` is enabled, PDFs are additionally enriched with page-level
visual descriptions from an Ollama vision-language model. This is intentionally
kept in the one-time preindexing script so the public CPU-only demo can reuse
the extracted text and embeddings without calling the VLM again.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import replace as dataclass_replace
from pathlib import Path
from typing import Any, Iterable
from urllib import error as urllib_error
from urllib import request as urllib_request

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.app.product_bootstrap import build_product_bootstrap
from src.product.preindexed_corpus import get_preindexed_store_path
from src.product.service import index_loaded_documents
from src.rag.loaders import LoadedDocument, load_document
from src.services.evidenceops_external_targets import (
    download_nextcloud_repository_document,
    list_nextcloud_repository_documents,
)
from src.services.runtime_controls import build_effective_rag_settings
from src.storage.rag_store import load_rag_store, save_rag_store

SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md", ".csv", ".py"}

PDF_VLM_SYSTEM_PROMPT = (
    "You are enriching a PDF page for a retrieval-augmented demo index. "
    "Inspect only the visible page image. Do not invent facts. "
    "Capture details that plain OCR may miss: headings, table structure, labels, "
    "charts, diagrams, checklists, dates, owners, obligations, risks, controls, "
    "numbers, pass/fail status, signatures, and visual relationships. "
    "Return concise Markdown. Preserve exact visible terms when possible. "
    "Use the document language when obvious; otherwise use English."
)


class _MemoryUpload:
    def __init__(self, name: str, content: bytes):
        self.name = name
        self._content = bytes(content)

    def getvalue(self) -> bytes:
        return self._content


def _truthy_env(name: str, default: bool) -> bool:
    raw = str(os.getenv(name, "")).strip().lower()
    if not raw:
        return default
    return raw not in {"0", "false", "no", "off"}


def _int_env(name: str, default: int) -> int:
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _normalize_identity_key(value: object) -> str:
    return "/".join(str(value or "").strip().replace("\\", "/").strip("/").split()).lower()




def _load_pdf_vlm_page_routes(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[pdf_vlm_routes] could not read {path}: {exc}", flush=True)
        return {}
    if not isinstance(payload, dict):
        return {}
    documents = payload.get("documents")
    if isinstance(documents, dict):
        return documents
    return {}


def _page_route_candidates(raw: dict[str, Any], filename: str) -> list[str]:
    candidates: list[str] = []
    for value in (
        raw.get("relative_path"),
        raw.get("nextcloud_relative_path"),
        raw.get("source_relative_path"),
        raw.get("document_id"),
        filename,
        Path(filename).name,
    ):
        normalized = _normalize_identity_key(value)
        if normalized and normalized not in candidates:
            candidates.append(normalized)
    return candidates


def _coerce_page_list(value: object) -> list[int]:
    pages: set[int] = set()
    if isinstance(value, list):
        for item in value:
            if isinstance(item, int):
                if item > 0:
                    pages.add(item)
            elif isinstance(item, str):
                pages.update(_coerce_page_list(item))
    elif isinstance(value, str):
        for part in value.replace(";", ",").split(","):
            token = part.strip()
            if not token:
                continue
            if "-" in token:
                left, right = token.split("-", 1)
                try:
                    start, end = int(left.strip()), int(right.strip())
                except ValueError:
                    continue
                for page in range(max(1, start), max(start, end) + 1):
                    pages.add(page)
            else:
                try:
                    page = int(token)
                except ValueError:
                    continue
                if page > 0:
                    pages.add(page)
    return sorted(pages)


def _resolve_manifest_entry(raw: dict[str, Any], filename: str, routes: dict[str, Any]) -> dict[str, Any] | None:
    if not routes:
        return None
    normalized_routes = {_normalize_identity_key(key): value for key, value in routes.items() if isinstance(value, dict)}
    for candidate in _page_route_candidates(raw, filename):
        entry = normalized_routes.get(candidate)
        if isinstance(entry, dict):
            return entry
    return None


def _resolve_pdf_vlm_page_selection(
    *,
    raw: dict[str, Any],
    filename: str,
    routes: dict[str, Any],
    route_policy: str,
    fallback_max_pages: int | None,
) -> tuple[list[int] | None, str, str | None]:
    """Return selected 1-indexed PDF pages for cloud VLM.

    None means legacy first-N/all behavior. [] means do not call cloud VLM.
    """
    policy = str(route_policy or "manifest").strip().lower()
    if policy in {"off", "none", "disabled"}:
        return [], "off", None
    if policy == "first-n":
        return None, "first-n", None
    if policy == "all":
        return None if fallback_max_pages is None else list(range(1, fallback_max_pages + 1)), "all", None
    entry = _resolve_manifest_entry(raw, filename, routes)
    if entry is None:
        if policy == "manifest-only":
            return [], "manifest-only:no-entry", None
        return None, "manifest:fallback-first-n", None
    pages = _coerce_page_list(entry.get("cloud_vlm_pages") or entry.get("pages") or [])
    reason = str(entry.get("reason") or entry.get("notes") or "").strip() or None
    return pages, "manifest", reason

def _completed_preindex_hashes(output_path: Path) -> set[str]:
    payload = load_rag_store(output_path) or {}
    documents = payload.get("documents") if isinstance(payload, dict) else None
    chunks = payload.get("chunks") if isinstance(payload, dict) else None
    if not isinstance(documents, list):
        return set()

    chunk_document_ids: set[str] = set()
    if isinstance(chunks, list):
        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue
            chunk_id = str(chunk.get("document_id") or chunk.get("file_hash") or "").strip()
            if chunk_id:
                chunk_document_ids.add(chunk_id)

    completed: set[str] = set()
    for document in documents:
        if not isinstance(document, dict):
            continue
        document_id = str(document.get("document_id") or document.get("file_hash") or "").strip()
        file_hash = str(document.get("file_hash") or document_id or "").strip()
        try:
            chunk_count = int(document.get("chunk_count") or 0)
        except (TypeError, ValueError):
            chunk_count = 0
        if not file_hash or chunk_count <= 0:
            continue
        if chunk_document_ids and document_id and document_id not in chunk_document_ids and file_hash not in chunk_document_ids:
            continue
        completed.add(file_hash)
    return completed


def _checkpoint_dir_for_output(output_path: Path) -> Path:
    raw = str(os.getenv("EVIDENCEOPS_PREINDEX_CHECKPOINT_DIR") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (output_path.parent / f"{output_path.stem}_checkpoints").resolve()


def _checkpoint_path(checkpoint_dir: Path, file_hash: str) -> Path:
    return checkpoint_dir / "documents" / f"{file_hash}.json"


def _safe_cache_part(value: object) -> str:
    raw = str(value or "").strip().lower()
    safe = []
    for char in raw:
        if char.isalnum() or char in {"-", "_", "."}:
            safe.append(char)
        else:
            safe.append("_")
    compact = "".join(safe).strip("._") or "default"
    return compact[:80]



def _pdf_vlm_page_cache_path(*, checkpoint_dir: Path, file_hash: str, model: str, dpi: int, scope: str) -> Path:
    model_part = _safe_cache_part(model)
    scope_part = _safe_cache_part(scope)
    return checkpoint_dir / "pdf_vlm_pages" / f"{file_hash}.{model_part}.{scope_part}.dpi_{dpi}.json"


def _pdf_vlm_page_cache_glob(*, checkpoint_dir: Path, file_hash: str, model: str, dpi: int) -> list[Path]:
    model_part = _safe_cache_part(model)
    return sorted((checkpoint_dir / "pdf_vlm_pages").glob(f"{file_hash}.{model_part}.*.dpi_{dpi}.json"))


def _load_pdf_vlm_page_cache(
    *,
    checkpoint_dir: Path | None,
    file_hash: str,
    model: str,
    dpi: int,
) -> dict[int, str]:
    if not checkpoint_dir or not file_hash:
        return {}
    cached: dict[int, str] = {}
    for cache_path in _pdf_vlm_page_cache_glob(
        checkpoint_dir=checkpoint_dir,
        file_hash=file_hash,
        model=model,
        dpi=dpi,
    ):
        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        pages = payload.get("pages")
        if not isinstance(pages, list):
            continue
        for item in pages:
            if not isinstance(item, dict):
                continue
            try:
                page = int(item.get("page") or 0)
            except (TypeError, ValueError):
                page = 0
            content = str(item.get("content") or "").strip()
            if page > 0 and content:
                cached[page] = content
    return cached


def _save_pdf_vlm_page_cache(
    *,
    checkpoint_dir: Path | None,
    file_hash: str,
    filename: str,
    model: str,
    dpi: int,
    scope: str,
    pages: dict[int, str],
) -> None:
    if not checkpoint_dir or not file_hash:
        return
    cache_path = _pdf_vlm_page_cache_path(
        checkpoint_dir=checkpoint_dir,
        file_hash=file_hash,
        model=model,
        dpi=dpi,
        scope=scope,
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "kind": "evidenceops_preindex_pdf_vlm_page_cache.v2",
        "file_hash": file_hash,
        "filename": filename,
        "model": model,
        "dpi": dpi,
        "scope": scope,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "pages": [{"page": page, "content": pages[page]} for page in sorted(pages)],
    }
    tmp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    tmp_path.replace(cache_path)

def _loaded_document_to_checkpoint(document: LoadedDocument) -> dict[str, object]:
    return {
        "kind": "evidenceops_preindex_loaded_document_checkpoint.v1",
        "name": document.name,
        "file_type": document.file_type,
        "file_hash": document.file_hash,
        "text": document.text,
        "metadata": document.metadata or {},
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def _loaded_document_from_checkpoint(payload: dict[str, object]) -> LoadedDocument | None:
    if not isinstance(payload, dict):
        return None
    file_hash = str(payload.get("file_hash") or "").strip()
    text = str(payload.get("text") or "")
    if not file_hash or not text.strip():
        return None
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    return LoadedDocument(
        name=str(payload.get("name") or "document"),
        file_type=str(payload.get("file_type") or "txt"),
        file_hash=file_hash,
        text=text,
        metadata=dict(metadata or {}),
    )


def _load_document_checkpoint(raw: dict[str, Any], checkpoint_dir: Path | None) -> LoadedDocument | None:
    file_hash = str(raw.get("preindex_file_hash") or "").strip()
    if not checkpoint_dir or not file_hash:
        return None
    path = _checkpoint_path(checkpoint_dir, file_hash)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    document = _loaded_document_from_checkpoint(payload)
    if not document or document.file_hash != file_hash:
        return None
    metadata = _public_metadata(raw, document)
    return dataclass_replace(document, metadata=metadata)


def _save_document_checkpoint(document: LoadedDocument, checkpoint_dir: Path | None) -> None:
    if not checkpoint_dir or not document.file_hash:
        return
    path = _checkpoint_path(checkpoint_dir, document.file_hash)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(_loaded_document_to_checkpoint(document), indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    tmp_path.replace(path)


def _iter_documents_to_process(
    raw_documents: Iterable[dict[str, Any]],
    *,
    output_path: Path,
    resume: bool,
    limit: int | None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    completed_hashes = _completed_preindex_hashes(output_path) if resume else set()
    if resume:
        print(f"[resume] enabled: {len(completed_hashes)} completed document hash(es) found in {output_path}", flush=True)
    else:
        print("[resume] disabled; matching documents will be reprocessed.", flush=True)

    selected: list[dict[str, Any]] = []
    skipped = 0
    seen = 0
    for raw in raw_documents:
        seen += 1
        content = bytes(raw.get("content") or b"")
        filename = str(raw.get("filename") or f"document-{seen}").strip()
        file_hash = hashlib.sha256(content).hexdigest() if content else ""
        raw["preindex_file_hash"] = file_hash
        if resume and file_hash and file_hash in completed_hashes:
            skipped += 1
            rel = _normalize_identity_key(raw.get("relative_path"))
            suffix = f" ({rel})" if rel and rel != filename.lower() else ""
            print(f"[skip] {seen}: {filename}{suffix} already fully indexed.", flush=True)
            continue
        selected.append(raw)
        if limit is not None and len(selected) >= limit:
            break
    return selected, {"seen": seen, "selected": len(selected), "skipped": skipped, "completed": len(completed_hashes)}


def _iter_local_documents(source_root: Path, *, limit: int | None = None) -> Iterable[dict[str, Any]]:
    count = 0
    for path in sorted(source_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        relative_path = path.relative_to(source_root).as_posix()
        yield {
            "content": path.read_bytes(),
            "filename": path.name,
            "title": path.stem,
            "relative_path": relative_path,
            "category": relative_path.split("/", 1)[0] if "/" in relative_path else "Public Reference Corpus",
            "size_bytes": path.stat().st_size,
            "document_id": relative_path,
        }
        count += 1
        if limit is not None and count >= limit:
            return


def _iter_nextcloud_documents(*, limit: int | None = None) -> Iterable[dict[str, Any]]:
    documents = list_nextcloud_repository_documents(limit=limit or 1000, allowed_suffixes=set(SUPPORTED_SUFFIXES))
    count = 0
    for document in documents if isinstance(documents, list) else []:
        if not isinstance(document, dict):
            continue
        remote = download_nextcloud_repository_document(
            relative_path=str(document.get("relative_path") or "").strip() or None,
            document_id=str(document.get("document_id") or "").strip() or None,
            filename=str(document.get("filename") or "").strip() or None,
            title=str(document.get("title") or "").strip() or None,
            category=str(document.get("category") or "").strip() or None,
            webdav_url=str(document.get("webdav_url") or "").strip() or None,
        )
        yield {
            "content": bytes(remote.get("content") or b""),
            "filename": str(remote.get("filename") or document.get("filename") or "document"),
            "title": str(remote.get("title") or document.get("title") or Path(str(remote.get("filename") or "document")).stem),
            "relative_path": str(remote.get("relative_path") or document.get("relative_path") or ""),
            "category": str(remote.get("category") or document.get("category") or "Public Reference Corpus"),
            "size_bytes": int(remote.get("size_bytes") or document.get("size_bytes") or len(bytes(remote.get("content") or b""))),
            "document_id": str(remote.get("document_id") or document.get("document_id") or document.get("relative_path") or ""),
            "webdav_url": str(document.get("webdav_url") or ""),
        }
        count += 1
        if limit is not None and count >= limit:
            return


def _public_metadata(raw: dict[str, Any], loaded: LoadedDocument) -> dict[str, object]:
    relative_path = str(raw.get("relative_path") or loaded.name).strip()
    filename = str(raw.get("filename") or Path(relative_path).name or loaded.name).strip()
    title = str(raw.get("title") or Path(filename).stem or filename).strip()
    category = str(raw.get("category") or "Public Reference Corpus").strip()
    return {
        **(loaded.metadata or {}),
        "source_type": "nextcloud",
        "relative_path": relative_path,
        "nextcloud_relative_path": relative_path,
        "source_relative_path": relative_path,
        "filename": filename,
        "title": title,
        "category": category,
        "size_bytes": int(raw.get("size_bytes") or len(raw.get("content") or b"")),
        "preindex": {
            "relative_path": relative_path,
            "filename": filename,
            "title": title,
            "category": category,
            "document_id": str(raw.get("document_id") or loaded.file_hash),
            "webdav_url": str(raw.get("webdav_url") or ""),
        },
    }


def _native_ollama_base_url(base_url: str | None) -> str:
    normalized = str(base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).strip().rstrip("/")
    if not normalized:
        normalized = "http://localhost:11434"
    if normalized.endswith("/v1"):
        normalized = normalized[:-3]
    elif normalized.endswith("/api"):
        normalized = normalized[:-4]
    return normalized.rstrip("/")


def _ollama_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    api_key = str(os.getenv("OLLAMA_API_KEY") or os.getenv("OLLAMA_CLOUD_API_KEY") or "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _resolve_pdf_vlm_model(rag_settings, explicit_model: str | None) -> str:
    return (
        str(explicit_model or "").strip()
        or str(os.getenv("EVIDENCEOPS_PREINDEX_PDF_VLM_MODEL", "")).strip()
        or str(os.getenv("EVIDENCE_VL_MODEL", "")).strip()
        or str(getattr(rag_settings, "evidence_vl_model", "") or "").strip()
        or "qwen3-vl:235b-cloud"
    )


def _call_ollama_vlm(*, image_path: Path, model: str, prompt: str, base_url: str) -> str:
    image_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt, "images": [image_b64]}],
        "stream": False,
        "options": {"temperature": 0.0},
    }
    req = urllib_request.Request(
        url=f"{base_url.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers=_ollama_headers(),
        method="POST",
    )
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            with urllib_request.urlopen(req, timeout=900) as resp:
                response = json.loads(resp.read().decode("utf-8"))
            return str((response.get("message") or {}).get("content") or "").strip()
        except (TimeoutError, socket.timeout, urllib_error.URLError) as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(2.0)
                continue
            break
        except urllib_error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore") if hasattr(exc, "read") else ""
            raise RuntimeError(f"Ollama VLM HTTP error {exc.code}: {body or exc.reason}") from exc
    raise RuntimeError(f"Ollama VLM request failed: {last_error}") from last_error


def _resize_image_for_vlm(image_path: Path, *, max_side: int = 1800) -> None:
    with Image.open(image_path) as image:
        width, height = image.size
        largest = max(width, height)
        if largest <= max_side:
            return
        scale = max_side / float(largest)
        resized = image.resize((max(1, int(width * scale)), max(1, int(height * scale))))
        resized.save(image_path)



def _first_n_page_numbers(page_count: int, max_pages: int | None) -> list[int]:
    limit = page_count if max_pages is None else min(max_pages, page_count)
    return list(range(1, max(0, limit) + 1))


def _render_with_pypdfium2(pdf_path: Path, output_dir: Path, *, page_numbers: list[int], dpi: int) -> dict[int, Path]:
    import pypdfium2 as pdfium  # type: ignore

    pdf = pdfium.PdfDocument(str(pdf_path))
    rendered: dict[int, Path] = {}
    scale = max(0.5, dpi / 72.0)
    try:
        for page_number in page_numbers:
            if page_number < 1 or page_number > len(pdf):
                continue
            page = pdf[page_number - 1]
            bitmap = page.render(scale=scale)
            image = bitmap.to_pil()
            output_path = output_dir / f"page-{page_number:04d}.png"
            image.save(output_path)
            rendered[page_number] = output_path
    finally:
        try:
            pdf.close()
        except Exception:
            pass
    return rendered


def _render_with_pymupdf(pdf_path: Path, output_dir: Path, *, page_numbers: list[int], dpi: int) -> dict[int, Path]:
    import fitz  # type: ignore

    doc = fitz.open(str(pdf_path))
    rendered: dict[int, Path] = {}
    matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    try:
        for page_number in page_numbers:
            if page_number < 1 or page_number > len(doc):
                continue
            page = doc[page_number - 1]
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            output_path = output_dir / f"page-{page_number:04d}.png"
            pixmap.save(str(output_path))
            rendered[page_number] = output_path
    finally:
        doc.close()
    return rendered


def _render_with_ghostscript(pdf_path: Path, output_dir: Path, *, page_numbers: list[int], dpi: int) -> dict[int, Path]:
    gs_binary = shutil.which("gs")
    if not gs_binary:
        raise RuntimeError("Ghostscript binary 'gs' not found")
    rendered: dict[int, Path] = {}
    for page_number in page_numbers:
        output_path = output_dir / f"page-{page_number:04d}.png"
        command = [
            gs_binary,
            "-dNOPAUSE",
            "-dBATCH",
            "-sDEVICE=png16m",
            f"-r{dpi}",
            f"-dFirstPage={page_number}",
            f"-dLastPage={page_number}",
            f"-sOutputFile={output_path}",
            str(pdf_path),
        ]
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if output_path.exists():
            rendered[page_number] = output_path
    return rendered


def _pdf_page_count(file_bytes: bytes, *, filename: str) -> int | None:
    with tempfile.TemporaryDirectory(prefix="evidenceops_pdf_count_") as tmp:
        pdf_path = Path(tmp) / (Path(filename).name or "document.pdf")
        pdf_path.write_bytes(file_bytes)
        try:
            import pypdfium2 as pdfium  # type: ignore

            pdf = pdfium.PdfDocument(str(pdf_path))
            try:
                return len(pdf)
            finally:
                try:
                    pdf.close()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            import fitz  # type: ignore

            doc = fitz.open(str(pdf_path))
            try:
                return len(doc)
            finally:
                doc.close()
        except Exception:
            return None


def _render_pdf_pages_for_vlm(file_bytes: bytes, *, filename: str, page_numbers: list[int], dpi: int) -> tuple[tempfile.TemporaryDirectory[str], dict[int, Path], str]:
    temp = tempfile.TemporaryDirectory(prefix="evidenceops_pdf_vlm_")
    temp_dir = Path(temp.name)
    pdf_path = temp_dir / (Path(filename).name or "document.pdf")
    pdf_path.write_bytes(file_bytes)
    output_dir = temp_dir / "pages"
    output_dir.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    for renderer_name, renderer in (("pypdfium2", _render_with_pypdfium2), ("pymupdf", _render_with_pymupdf), ("ghostscript", _render_with_ghostscript)):
        try:
            pages = renderer(pdf_path, output_dir, page_numbers=page_numbers, dpi=dpi)
            if pages:
                for page_path in pages.values():
                    _resize_image_for_vlm(page_path)
                return temp, pages, renderer_name
        except Exception as exc:
            errors.append(f"{renderer_name}: {exc}")
            for stale_page in output_dir.glob("page-*.png"):
                stale_page.unlink(missing_ok=True)
    temp.cleanup()
    raise RuntimeError("Could not render PDF pages for Ollama VLM. " + " | ".join(errors))


def _append_pdf_vlm_enrichment(
    *,
    raw: dict[str, Any],
    document: LoadedDocument,
    rag_settings,
    model: str | None,
    base_url: str,
    max_pages: int | None,
    dpi: int,
    checkpoint_dir: Path | None,
    file_hash: str,
    routes: dict[str, Any],
    route_policy: str,
) -> LoadedDocument:
    filename = str(raw.get("filename") or document.name or "document.pdf")
    resolved_model = _resolve_pdf_vlm_model(rag_settings, model)
    file_bytes = bytes(raw.get("content") or b"")
    page_count = _pdf_page_count(file_bytes, filename=filename)
    selected_pages, route_source, route_reason = _resolve_pdf_vlm_page_selection(
        raw=raw,
        filename=filename,
        routes=routes,
        route_policy=route_policy,
        fallback_max_pages=max_pages,
    )
    if selected_pages is None:
        selected_pages = _first_n_page_numbers(page_count or 0, max_pages)
    if page_count:
        selected_pages = [page for page in selected_pages if 1 <= page <= page_count]
    selected_pages = sorted(set(selected_pages))
    if not selected_pages:
        print(f"[pdf_vlm] {filename}: skipped by route policy ({route_source}); Docling/text extraction only.", flush=True)
        metadata = dict(document.metadata or {})
        metadata["preindex_pdf_vlm"] = {
            "enabled": False,
            "skipped": True,
            "route_source": route_source,
            "route_reason": route_reason,
            "page_count": page_count,
        }
        return dataclass_replace(document, metadata=metadata)

    scope_hash = hashlib.sha1((route_source + ":" + ",".join(str(p) for p in selected_pages)).encode("utf-8")).hexdigest()[:12]
    cache_scope = f"pages_selected_{scope_hash}"
    cached_pages = _load_pdf_vlm_page_cache(
        checkpoint_dir=checkpoint_dir,
        file_hash=file_hash,
        model=resolved_model,
        dpi=dpi,
    )
    missing_pages = [page for page in selected_pages if page not in cached_pages]
    page_paths: dict[int, Path] = {}
    renderer_name = "cache"
    if missing_pages:
        print(
            f"[pdf_vlm] {filename}: rendering {len(missing_pages)} selected page(s) for Ollama VLM ({resolved_model}) via {route_source}: {missing_pages}.",
            flush=True,
        )
        temp, page_paths, renderer_name = _render_pdf_pages_for_vlm(file_bytes, filename=filename, page_numbers=missing_pages, dpi=dpi)
    else:
        temp = None
        print(f"[pdf_vlm] {filename}: all selected page(s) already cached: {selected_pages}.", flush=True)
    page_summaries: list[dict[str, object]] = []
    try:
        for page_number in selected_pages:
            page_prompt = (
                f"{PDF_VLM_SYSTEM_PROMPT}\n\n"
                f"Document: {filename}\n"
                f"Page: {page_number}/{page_count or '?'}\n"
                f"Routing: {route_source}\n"
                f"Reason: {route_reason or 'selected for visual enrichment'}\n\n"
                "Return Markdown with this structure:\n"
                "### Visual extraction\n"
                "- Important visible text and headings\n"
                "- Tables/checklists/forms, with row or field meanings\n"
                "- Diagrams/charts/logos/stamps/signatures and what they indicate\n"
                "- Key facts useful for search and question answering\n"
            )
            if page_number in cached_pages:
                print(f"[pdf_vlm] {filename}: page {page_number}/{page_count or '?'} -> cached", flush=True)
                content = cached_pages[page_number]
            else:
                page_path = page_paths.get(page_number)
                if not page_path:
                    print(f"[pdf_vlm] {filename}: page {page_number}/{page_count or '?'} -> render missing, skipped", flush=True)
                    continue
                print(f"[pdf_vlm] {filename}: page {page_number}/{page_count or '?'} -> {resolved_model}", flush=True)
                content = _call_ollama_vlm(image_path=page_path, model=resolved_model, prompt=page_prompt, base_url=base_url)
                cached_pages[page_number] = content
                _save_pdf_vlm_page_cache(
                    checkpoint_dir=checkpoint_dir,
                    file_hash=file_hash,
                    filename=filename,
                    model=resolved_model,
                    dpi=dpi,
                    scope=cache_scope,
                    pages={page: cached_pages[page] for page in selected_pages if page in cached_pages},
                )
            page_summaries.append({"page": page_number, "content": content})
    finally:
        if temp is not None:
            temp.cleanup()

    visual_sections = [
        f"[PDF VISUAL ENRICHMENT - OLLAMA VLM]\n"
        f"Model: {resolved_model}\n"
        f"Renderer: {renderer_name}\n"
        f"Route source: {route_source}\n"
        f"Pages described: {', '.join(str(page) for page in selected_pages)}"
    ]
    if route_reason:
        visual_sections.append(f"Route reason: {route_reason}")
    for item in page_summaries:
        content = str(item.get("content") or "").strip()
        if content:
            visual_sections.append(f"\n## Page {item.get('page')} visual notes\n{content}")
    enrichment_text = "\n\n".join(visual_sections).strip()
    combined_text = (document.text.rstrip() + "\n\n" + enrichment_text).strip() if enrichment_text else document.text
    metadata = dict(document.metadata or {})
    metadata["preindex_pdf_vlm"] = {
        "enabled": True,
        "provider": "ollama",
        "model": resolved_model,
        "base_url": base_url,
        "renderer": renderer_name,
        "route_source": route_source,
        "route_reason": route_reason,
        "page_count": page_count,
        "pages_described": selected_pages,
        "page_count_described": len(page_summaries),
        "max_pages_fallback": max_pages,
        "dpi": dpi,
        "summary_chars": sum(len(str(item.get("content") or "")) for item in page_summaries),
    }
    return dataclass_replace(document, text=combined_text, metadata=metadata)

def _load_documents(
    raw_documents: Iterable[dict[str, Any]],
    rag_settings,
    *,
    continue_on_error: bool,
    pdf_vlm_enabled: bool,
    pdf_vlm_model: str | None,
    pdf_vlm_base_url: str,
    pdf_vlm_max_pages: int | None,
    pdf_vlm_dpi: int,
    pdf_vlm_routes: dict[str, Any] | None = None,
    pdf_vlm_route_policy: str = "manifest",
    checkpoint_dir: Path | None = None,
) -> tuple[list[LoadedDocument], list[dict[str, str]]]:
    loaded: list[LoadedDocument] = []
    errors: list[dict[str, str]] = []
    for index, raw in enumerate(raw_documents, start=1):
        filename = str(raw.get("filename") or f"document-{index}").strip()
        file_hash = str(raw.get("preindex_file_hash") or "").strip()
        if not file_hash:
            file_hash = hashlib.sha256(bytes(raw.get("content") or b"")).hexdigest()
            raw["preindex_file_hash"] = file_hash
        checkpointed = _load_document_checkpoint(raw, checkpoint_dir)
        if checkpointed is not None:
            print(f"[checkpoint] {index}: {filename} extracted/VLM text already saved; skipping extraction and PDF VLM.", flush=True)
            loaded.append(checkpointed)
            continue
        print(f"[extract] {index}: {filename}", flush=True)
        try:
            document = load_document(_MemoryUpload(filename, bytes(raw.get("content") or b"")), rag_settings)
            suffix = Path(filename).suffix.lower()
            if pdf_vlm_enabled and suffix == ".pdf":
                document = _append_pdf_vlm_enrichment(raw=raw, document=document, rag_settings=rag_settings, model=pdf_vlm_model, base_url=pdf_vlm_base_url, max_pages=pdf_vlm_max_pages, dpi=pdf_vlm_dpi, checkpoint_dir=checkpoint_dir, file_hash=file_hash, routes=pdf_vlm_routes or {}, route_policy=pdf_vlm_route_policy)
            metadata = _public_metadata(raw, document)
            document = dataclass_replace(document, metadata=metadata)
            _save_document_checkpoint(document, checkpoint_dir)
            loaded.append(document)
        except Exception as exc:  # pragma: no cover - operational CLI path
            errors.append({"filename": filename, "error": str(exc)})
            print(f"[error] {filename}: {exc}", flush=True)
            if not continue_on_error:
                raise
    return loaded, errors


def _configure_preindex_settings(base_settings, *, output_path: Path, force_vlm: bool):
    chroma_path = output_path.parent / "preindexed_public_corpus_chroma"
    settings = dataclass_replace(base_settings, store_path=output_path, chroma_path=chroma_path)
    if force_vlm:
        settings = dataclass_replace(
            settings,
            pdf_docling_enabled=True,
            pdf_docling_ocr_enabled=True,
            # Avoid Docling's default local SmolVLM path; explicit Ollama VLM enrichment runs below.
            pdf_docling_picture_description=_truthy_env("EVIDENCEOPS_PREINDEX_ALLOW_DOCLING_LOCAL_VLM", False),
            pdf_evidence_pipeline_enabled=True,
            pdf_evidence_pipeline_rollout_percentage=100,
            pdf_evidence_pipeline_use_for_cv_like=True,
            pdf_evidence_pipeline_use_for_strong_scan_like=True,
            pdf_max_selective_docling_pages=max(int(getattr(settings, "pdf_max_selective_docling_pages", 12) or 12), 12),
        )
    return settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Preindex EvidenceOps public reference documents for fast Nextcloud demo imports.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source-root", type=Path, help="Local folder that mirrors the Nextcloud Public Reference Corpus.")
    source.add_argument("--from-nextcloud", action="store_true", help="Read and download documents directly from the configured Nextcloud repository.")
    parser.add_argument("--output", type=Path, default=None, help="Output RAG JSON store. Defaults to EVIDENCEOPS_PREINDEX_STORE_PATH or .runtime/state/rag/preindexed_public_corpus.json.")
    parser.add_argument("--limit", type=int, default=None, help="Optional maximum number of documents to preindex.")
    parser.add_argument("--force-vlm", action=argparse.BooleanOptionalAction, default=True, help="Force the richer PDF extraction path while preindexing.")
    parser.add_argument("--pdf-vlm", action=argparse.BooleanOptionalAction, default=None, help="Use Ollama VLM page enrichment for PDFs. Defaults to --force-vlm and EVIDENCEOPS_PREINDEX_PDF_VLM_ENABLED.")
    parser.add_argument("--pdf-vlm-model", default=None, help="Ollama VLM model for PDF page enrichment. Defaults to EVIDENCEOPS_PREINDEX_PDF_VLM_MODEL, EVIDENCE_VL_MODEL, then qwen3-vl:235b-cloud.")
    parser.add_argument("--pdf-vlm-max-pages", type=int, default=_int_env("EVIDENCEOPS_PREINDEX_PDF_VLM_MAX_PAGES", 20), help="Maximum pages per PDF to send to the VLM. Use 0 for all pages.")
    parser.add_argument("--pdf-vlm-dpi", type=int, default=_int_env("EVIDENCEOPS_PREINDEX_PDF_VLM_DPI", 180), help="PDF rasterization DPI for VLM page images.")
    parser.add_argument("--pdf-vlm-page-routes", type=Path, default=Path(__file__).with_name("preindex_public_reference_corpus_page_routes.json"), help="JSON manifest that hardcodes which PDF pages should go to cloud VLM. Defaults to the bundled public-corpus route manifest.")
    parser.add_argument("--pdf-vlm-route-policy", default=os.getenv("EVIDENCEOPS_PREINDEX_PDF_VLM_ROUTE_POLICY", "manifest"), choices=["manifest", "manifest-only", "first-n", "all", "off"], help="How to choose PDF pages for cloud VLM. manifest uses the route JSON and falls back to first-N for unknown PDFs.")
    parser.add_argument("--continue-on-error", action="store_true", help="Keep indexing the remaining documents if one extraction fails.")
    parser.add_argument("--reset", action="store_true", help="Delete the output JSON store before starting.")
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=_truthy_env("EVIDENCEOPS_PREINDEX_RESUME", True), help="Skip documents that are already fully indexed in the output store. Enabled by default unless --reset is used.")
    args = parser.parse_args()

    bootstrap = build_product_bootstrap()
    output_path = (args.output or get_preindexed_store_path(bootstrap.workspace_root)).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if args.reset and output_path.exists():
        output_path.unlink()

    checkpoint_dir = _checkpoint_dir_for_output(output_path)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    print(f"[checkpoint] enabled: {checkpoint_dir}", flush=True)

    effective_settings = build_effective_rag_settings(default_settings=bootstrap.rag_settings, workspace_root=bootstrap.workspace_root)
    preindex_settings = _configure_preindex_settings(effective_settings, output_path=output_path, force_vlm=bool(args.force_vlm))

    resume_enabled = bool(args.resume) and not bool(args.reset)
    source_listing_limit = None if resume_enabled else args.limit
    if args.from_nextcloud:
        raw_document_iter = _iter_nextcloud_documents(limit=source_listing_limit)
        source_label = "nextcloud"
    else:
        source_root = args.source_root.expanduser().resolve()
        if not source_root.exists():
            raise FileNotFoundError(f"Source root does not exist: {source_root}")
        raw_document_iter = _iter_local_documents(source_root, limit=source_listing_limit)
        source_label = str(source_root)

    raw_documents, resume_stats = _iter_documents_to_process(
        raw_document_iter,
        output_path=output_path,
        resume=resume_enabled,
        limit=args.limit,
    )

    env_pdf_vlm_enabled = _truthy_env("EVIDENCEOPS_PREINDEX_PDF_VLM_ENABLED", True)
    pdf_vlm_enabled = bool(args.force_vlm) and env_pdf_vlm_enabled if args.pdf_vlm is None else bool(args.pdf_vlm)
    pdf_vlm_max_pages = None if int(args.pdf_vlm_max_pages or 0) <= 0 else int(args.pdf_vlm_max_pages)
    pdf_vlm_dpi = max(72, int(args.pdf_vlm_dpi or 180))
    pdf_vlm_base_url = _native_ollama_base_url(os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    pdf_vlm_model = _resolve_pdf_vlm_model(preindex_settings, args.pdf_vlm_model)

    pdf_vlm_routes = _load_pdf_vlm_page_routes(args.pdf_vlm_page_routes.expanduser().resolve() if args.pdf_vlm_page_routes else None)
    if pdf_vlm_enabled:
        route_count = len(pdf_vlm_routes) if isinstance(pdf_vlm_routes, dict) else 0
        print(f"[pdf_vlm] enabled: model={pdf_vlm_model}, base_url={pdf_vlm_base_url}, route_policy={args.pdf_vlm_route_policy}, routes={route_count}, fallback_max_pages={pdf_vlm_max_pages or 'all'}, dpi={pdf_vlm_dpi}", flush=True)
    else:
        print("[pdf_vlm] disabled; PDFs will use textual extraction only.", flush=True)

    errors: list[dict[str, str]] = []
    indexed_documents = 0
    index_status: dict[str, Any] = {"ok": True, "message": "No new documents were indexed."}
    for doc_position, raw_document in enumerate(raw_documents, start=1):
        loaded_documents, load_errors = _load_documents(
            [raw_document],
            preindex_settings,
            continue_on_error=bool(args.continue_on_error),
            pdf_vlm_enabled=pdf_vlm_enabled,
            pdf_vlm_model=pdf_vlm_model,
            pdf_vlm_base_url=pdf_vlm_base_url,
            pdf_vlm_max_pages=pdf_vlm_max_pages,
            pdf_vlm_dpi=pdf_vlm_dpi,
            pdf_vlm_routes=pdf_vlm_routes,
            pdf_vlm_route_policy=str(args.pdf_vlm_route_policy or "manifest"),
            checkpoint_dir=checkpoint_dir,
        )
        errors.extend(load_errors)
        if not loaded_documents:
            continue
        document_name = loaded_documents[0].name
        print(f"[index] creating embeddings for {document_name} ({doc_position}/{len(raw_documents)}) into {output_path}", flush=True)
        _, index_status = index_loaded_documents(
            loaded_documents,
            rag_settings=preindex_settings,
            provider_registry=bootstrap.provider_registry,
            progress_callback=lambda stage, payload: print(f"[{stage}] {payload.get('detail') or payload.get('status')}", flush=True),
        )
        indexed_documents += len(loaded_documents)

    if indexed_documents <= 0:
        if resume_stats.get("skipped"):
            status = {
                "ok": True,
                "message": f"No new documents to index; {resume_stats.get('skipped')} already indexed document(s) were skipped.",
                "resume": resume_stats,
            }
            print(json.dumps({"ok": True, "output": str(output_path), "status": status, "errors": errors}, indent=2, ensure_ascii=False))
            return 0
        raise RuntimeError("No supported documents were loaded for preindexing.")

    payload = load_rag_store(output_path) or {}
    if isinstance(payload, dict):
        payload["kind"] = "evidenceops_preindexed_corpus.v1"
        payload["preindex"] = {
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": source_label,
            "document_count": len(payload.get("documents") or []),
            "chunk_count": len(payload.get("chunks") or []),
            "embedding_provider": preindex_settings.embedding_provider,
            "embedding_model": preindex_settings.embedding_model,
            "evidence_vl_model": preindex_settings.evidence_vl_model,
            "force_vlm": bool(args.force_vlm),
            "pdf_vlm": {
                "enabled": pdf_vlm_enabled,
                "provider": "ollama" if pdf_vlm_enabled else None,
                "model": pdf_vlm_model if pdf_vlm_enabled else None,
                "base_url": pdf_vlm_base_url if pdf_vlm_enabled else None,
                "max_pages": pdf_vlm_max_pages,
                "dpi": pdf_vlm_dpi,
                "route_policy": str(args.pdf_vlm_route_policy or "manifest"),
                "route_manifest": str(args.pdf_vlm_page_routes) if args.pdf_vlm_page_routes else None,
            },
            "resume": resume_stats,
            "checkpoint_dir": str(checkpoint_dir),
            "errors": errors,
        }
        save_rag_store(output_path, payload)

    print(json.dumps({"ok": True, "output": str(output_path), "status": index_status, "indexed_documents": indexed_documents, "resume": resume_stats, "errors": errors}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
