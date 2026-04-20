from __future__ import annotations

import base64
import csv
import hashlib
import json
import mimetypes
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from src.config import (
    EvidenceOpsExternalSettings,
    NextcloudWebDavSettings,
    NotionSettings,
    TrelloSettings,
    get_evidenceops_external_settings,
)
from src.product.action_plan_presenter import build_action_plan_view
from src.product.models import ProductWorkflowResult
from src.services.evidenceops_repository import (
    DEFAULT_EVIDENCEOPS_REPOSITORY_SUFFIXES,
    diff_evidenceops_repository_snapshots,
    summarize_evidenceops_repository_documents,
)
from src.services.evidenceops_worklog import build_evidenceops_worklog_entry
from src.structured.base import CVAnalysisPayload, DocumentAgentPayload


DEFAULT_PHASE95_PRIMARY_CORPUS_RELATIVE_PATH = Path("data/corpus_revisado/option_b_synthetic_premium")
DEFAULT_PHASE95_PUBLIC_CORPUS_RELATIVE_PATH = Path("data/corpus_revisado/option_a_public_corpus_v2")
DEFAULT_PHASE95_CORPUS_REVIEW_ROOT = Path("data/corpus_revisado")
DEFAULT_PHASE95_OPTION_B_STORYLINES = Path("data/corpus_revisado/option_b_storylines.csv")
DEFAULT_PHASE95_OPTION_B_RELATIONAL_MANIFEST = Path("data/corpus_revisado/option_b_v2_relational_manifest.csv")
_QUERY_SPLIT_REGEX = re.compile(r"\s+")


@dataclass(frozen=True)
class Phase95CorpusMapping:
    official_demo_corpus_name: str
    corpus_primary_root: Path
    corpus_public_root: Path
    nextcloud_directories: list[dict[str, Any]]
    trello_storylines: list[dict[str, Any]]
    notion_registers: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "official_demo_corpus_name": self.official_demo_corpus_name,
            "corpus_primary_root": str(self.corpus_primary_root),
            "corpus_public_root": str(self.corpus_public_root),
            "nextcloud_directories": self.nextcloud_directories,
            "trello_storylines": self.trello_storylines,
            "notion_registers": self.notion_registers,
        }


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _split_semicolon_values(value: object) -> list[str]:
    return [part.strip() for part in str(value or "").split(";") if part.strip()]


def _quote_path_segments(path: str) -> str:
    segments = [urllib.parse.quote(segment) for segment in str(path or "").split("/") if segment]
    return "/".join(segments)


def _build_basic_auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


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


def _extract_document_id_from_name(file_name: str) -> str | None:
    prefix = Path(file_name).stem.split("_", 1)[0].strip()
    if not prefix:
        return None
    if "-" in prefix and any(character.isdigit() for character in prefix):
        return prefix
    return None


def _build_title_from_name(file_name: str) -> str:
    stem = Path(file_name).stem.strip()
    document_id = _extract_document_id_from_name(file_name)
    if document_id and stem.startswith(f"{document_id}_"):
        stem = stem[len(document_id) + 1 :]
    return stem.replace("_", " ").strip() or file_name


def _resolve_category_from_relative_path(relative_path: str) -> str:
    normalized = str(relative_path or "").strip("/")
    if not normalized:
        return "root"
    parts = normalized.split("/")
    return parts[0] if len(parts) > 1 else "root"


def _http_date_to_timestamp(value: object) -> int:
    normalized = _normalize_optional_str(value)
    if not normalized:
        return 0
    try:
        parsed = parsedate_to_datetime(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp())
    except (TypeError, ValueError, OverflowError):
        return 0


def _compute_nextcloud_fingerprint(entry: dict[str, Any]) -> str:
    etag = _normalize_optional_str(entry.get("etag"))
    if etag:
        return etag
    fallback = json.dumps(
        {
            "relative_path": entry.get("relative_path"),
            "size_bytes": int(entry.get("size_bytes") or 0),
            "modified_at": int(entry.get("modified_at") or 0),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
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


def build_phase95_corpus_mapping(
    *,
    project_root: Path | None = None,
    settings: EvidenceOpsExternalSettings | None = None,
) -> Phase95CorpusMapping:
    resolved_settings = settings or get_evidenceops_external_settings()
    resolved_root = project_root or _project_root()
    storylines_rows = _read_csv_rows(resolved_root / DEFAULT_PHASE95_OPTION_B_STORYLINES)
    relational_rows = _read_csv_rows(resolved_root / DEFAULT_PHASE95_OPTION_B_RELATIONAL_MANIFEST)

    nextcloud_directories = []
    for local_subdir, remote_subdir in [
        ("policies", "policies"),
        ("contracts", "contracts"),
        ("audit", "audit"),
        ("templates", "templates"),
        ("metadata", "metadata"),
    ]:
        local_path = resolved_settings.corpus_primary_root / local_subdir
        file_count = len([item for item in local_path.iterdir() if item.is_file()]) if local_path.exists() else 0
        nextcloud_directories.append(
            {
                "local_subdir": local_subdir,
                "local_path": str(local_path),
                "remote_path": str(Path(resolved_settings.nextcloud.root_path) / remote_subdir).replace("\\", "/"),
                "file_count": file_count,
            }
        )

    trello_storylines = []
    for row in storylines_rows:
        storyline_id = str(row.get("storyline_id") or "").strip()
        if not storyline_id:
            continue
        trello_storylines.append(
            {
                "storyline_id": storyline_id,
                "name": str(row.get("name") or "").strip(),
                "goal": str(row.get("goal") or "").strip(),
                "card_title": f"[{storyline_id}] {str(row.get('name') or '').strip()}",
                "primary_documents": _split_semicolon_values(row.get("primary_documents")),
                "supporting_documents": _split_semicolon_values(row.get("supporting_documents")),
                "expected_action_items": _split_semicolon_values(row.get("expected_action_items")),
                "expected_review_flags": _split_semicolon_values(row.get("expected_review_flags")),
            }
        )

    notion_registers = [
        {
            "register_name": "EvidenceOps Storyline Register",
            "source_rows": len(storylines_rows),
            "primary_fields": [
                "storyline_id",
                "name",
                "goal",
                "primary_documents",
                "supporting_documents",
                "expected_findings",
                "expected_risks",
                "expected_action_items",
            ],
        },
        {
            "register_name": "EvidenceOps Document Register",
            "source_rows": len(relational_rows),
            "primary_fields": [
                "id",
                "title",
                "document_type",
                "status",
                "owner",
                "version",
                "classification",
                "storyline",
                "related_documents",
                "expected_findings",
            ],
        },
        {
            "register_name": "EvidenceOps Pack / Findings Register",
            "source_rows": len(relational_rows),
            "primary_fields": [
                "owner",
                "status",
                "risk_signals",
                "expected_use_cases",
                "gold_candidate",
                "difficulty_level",
            ],
        },
    ]

    return Phase95CorpusMapping(
        official_demo_corpus_name="option_b_synthetic_premium",
        corpus_primary_root=resolved_settings.corpus_primary_root,
        corpus_public_root=resolved_settings.corpus_public_root,
        nextcloud_directories=nextcloud_directories,
        trello_storylines=trello_storylines,
        notion_registers=notion_registers,
    )


def build_external_targets_status(
    settings: EvidenceOpsExternalSettings | None = None,
) -> dict[str, Any]:
    resolved_settings = settings or get_evidenceops_external_settings()

    nextcloud_missing = [
        field_name
        for field_name, value in {
            "base_url": resolved_settings.nextcloud.base_url,
            "username": resolved_settings.nextcloud.username,
            "app_password": resolved_settings.nextcloud.app_password,
        }.items()
        if not str(value or "").strip()
    ]
    trello_missing = [
        field_name
        for field_name, value in {
            "api_key": resolved_settings.trello.api_key,
            "token": resolved_settings.trello.token,
            "board_id": resolved_settings.trello.board_id,
            "list_open_id": resolved_settings.trello.list_open_id,
        }.items()
        if not str(value or "").strip()
    ]
    notion_missing = [
        field_name
        for field_name, value in {
            "api_key": resolved_settings.notion.api_key,
            "database_id": resolved_settings.notion.database_id,
        }.items()
        if not str(value or "").strip()
    ]
    return {
        "repository_backend": resolved_settings.repository_backend,
        "external_sync_enabled": bool(resolved_settings.external_sync_enabled),
        "official_demo_corpus": "option_b_synthetic_premium",
        "corpus_primary_root": str(resolved_settings.corpus_primary_root),
        "corpus_public_root": str(resolved_settings.corpus_public_root),
        "nextcloud": {
            "configured": not nextcloud_missing,
            "missing": nextcloud_missing,
            "root_path": resolved_settings.nextcloud.root_path,
        },
        "trello": {
            "configured": not trello_missing,
            "missing": trello_missing,
            "board_id": resolved_settings.trello.board_id or None,
        },
        "notion": {
            "configured": not notion_missing,
            "missing": notion_missing,
            "database_id": resolved_settings.notion.database_id or None,
        },
    }


class WebDavClient:
    def __init__(self, settings: NextcloudWebDavSettings) -> None:
        self.settings = settings

    def _build_url(self, remote_path: str) -> str:
        base_url = self.settings.base_url.rstrip("/")
        root_path = self.settings.root_path.strip("/")
        remote_suffix = str(remote_path or "").strip("/")
        if remote_suffix == root_path:
            remote_suffix = ""
        elif root_path and remote_suffix.startswith(f"{root_path}/"):
            remote_suffix = remote_suffix[len(root_path) + 1 :]
        parts = [part for part in [root_path, remote_suffix] if part]
        return f"{base_url}/{_quote_path_segments('/'.join(parts))}"

    def _root_url_path(self) -> str:
        return urllib.parse.unquote(urllib.parse.urlparse(self._build_url("")).path).rstrip("/")

    def _normalize_remote_relative_path(self, href: str) -> str:
        href_path = urllib.parse.unquote(urllib.parse.urlparse(str(href or "")).path).rstrip("/")
        root_url_path = self._root_url_path()
        if not href_path.startswith(root_url_path):
            return ""
        return href_path[len(root_url_path) :].lstrip("/")

    def _request(
        self,
        method: str,
        remote_path: str,
        *,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
        expected_statuses: tuple[int, ...] = (200, 201, 204, 207),
    ) -> tuple[int, bytes]:
        request_headers = {
            "Authorization": _build_basic_auth_header(self.settings.username, self.settings.app_password),
        }
        if headers:
            request_headers.update(headers)
        request = urllib.request.Request(
            self._build_url(remote_path),
            data=data,
            headers=request_headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
                status_code = int(getattr(response, "status", 200) or 200)
        except urllib.error.HTTPError as error:  # pragma: no cover - network integration
            status_code = int(error.code or 500)
            body = error.read()
            if status_code not in expected_statuses:
                raise
        if status_code not in expected_statuses:
            raise RuntimeError(f"Unexpected WebDAV status {status_code} for {remote_path}")
        return status_code, body

    def list_directory(self, remote_path: str = "") -> list[dict[str, Any]]:
        _, body = self._request(
            "PROPFIND",
            remote_path,
            headers={"Depth": "1", "Content-Type": "application/xml"},
            data=(
                b'<?xml version="1.0" encoding="utf-8" ?>\n'
                b"<d:propfind xmlns:d='DAV:'><d:prop><d:displayname/><d:getcontentlength/><d:getlastmodified/><d:getetag/><d:resourcetype/></d:prop></d:propfind>"
            ),
        )
        namespace = {"d": "DAV:"}
        root = ET.fromstring(body)
        entries: list[dict[str, Any]] = []
        for response_node in root.findall("d:response", namespace):
            href = response_node.findtext("d:href", default="", namespaces=namespace)
            display_name = response_node.findtext(
                "d:propstat/d:prop/d:displayname",
                default="",
                namespaces=namespace,
            )
            size_text = response_node.findtext(
                "d:propstat/d:prop/d:getcontentlength",
                default="0",
                namespaces=namespace,
            )
            modified_at = response_node.findtext(
                "d:propstat/d:prop/d:getlastmodified",
                default="",
                namespaces=namespace,
            )
            etag = response_node.findtext(
                "d:propstat/d:prop/d:getetag",
                default="",
                namespaces=namespace,
            )
            is_collection = (
                response_node.find(".//d:collection", namespace) is not None
                or str(href or "").rstrip().endswith("/")
            )
            entries.append(
                {
                    "href": href,
                    "display_name": display_name,
                    "size_bytes": int(size_text or 0),
                    "modified_at": modified_at,
                    "etag": etag,
                    "is_collection": bool(is_collection),
                    "relative_path": self._normalize_remote_relative_path(href),
                }
            )
        return entries

    def list_tree(self, remote_path: str = "") -> list[dict[str, Any]]:
        directories_to_visit = [str(remote_path or "").strip("/")]
        visited_directories: set[str] = set()
        files: list[dict[str, Any]] = []

        while directories_to_visit:
            current = directories_to_visit.pop(0)
            if current in visited_directories:
                continue
            visited_directories.add(current)
            for entry in self.list_directory(current):
                relative_path = str(entry.get("relative_path") or "").strip("/")
                if not relative_path:
                    continue
                if bool(entry.get("is_collection")):
                    if relative_path not in visited_directories:
                        directories_to_visit.append(relative_path)
                    continue
                files.append(entry)
        return files

    def ensure_collection(self, remote_path: str) -> dict[str, Any]:
        status_code, _ = self._request("MKCOL", remote_path, expected_statuses=(201, 301, 405))
        return {"remote_path": remote_path, "status_code": status_code}

    def upload_file(self, local_path: Path, remote_path: str) -> dict[str, Any]:
        content_type = mimetypes.guess_type(str(local_path))[0] or "application/octet-stream"
        status_code, _ = self._request(
            "PUT",
            remote_path,
            data=local_path.read_bytes(),
            headers={"Content-Type": content_type},
            expected_statuses=(200, 201, 204),
        )
        return {
            "local_path": str(local_path),
            "remote_path": remote_path,
            "status_code": status_code,
        }


class TrelloClient:
    base_url = "https://api.trello.com/1"

    def __init__(self, settings: TrelloSettings) -> None:
        self.settings = settings

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        parameters = {
            "key": self.settings.api_key,
            "token": self.settings.token,
        }
        if query:
            parameters.update({key: value for key, value in query.items() if value is not None})
        encoded_query = urllib.parse.urlencode(parameters)
        data = None
        headers: dict[str, str] = {}
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/{path.lstrip('/')}?{encoded_query}",
            data=data,
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(request, timeout=30) as response:  # pragma: no cover - network integration
            return json.loads(response.read().decode("utf-8"))

    def list_board_lists(self) -> list[dict[str, Any]]:
        response = self._request("GET", f"boards/{self.settings.board_id}/lists")
        return response if isinstance(response, list) else []

    def create_card(self, *, list_id: str, name: str, description: str, due: str | None = None) -> dict[str, Any]:
        return self._request(
            "POST",
            "cards",
            query={
                "idList": list_id,
                "name": name,
                "desc": description,
                "due": due,
            },
        )

    def update_card(self, card_id: str, *, list_id: str | None = None, name: str | None = None, description: str | None = None) -> dict[str, Any]:
        return self._request(
            "PUT",
            f"cards/{card_id}",
            query={"idList": list_id, "name": name, "desc": description},
        )

    def add_comment(self, card_id: str, text: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"cards/{card_id}/actions/comments",
            query={"text": text},
        )


def _trim_text(value: object, *, max_chars: int = 240) -> str:
    normalized = " ".join(str(value or "").split()).strip()
    if len(normalized) <= max_chars:
        return normalized
    if max_chars <= 1:
        return normalized[:max_chars]
    return normalized[: max_chars - 1].rstrip() + "…"


def _result_document_ids(result: ProductWorkflowResult) -> list[str]:
    document_ids: list[str] = []
    if result.grounding_preview is not None:
        document_ids.extend(str(item).strip() for item in result.grounding_preview.document_ids if str(item).strip())
    debug_source_documents = result.debug_metadata.get("source_documents") if isinstance(result.debug_metadata, dict) else []
    if isinstance(debug_source_documents, list):
        document_ids.extend(str(item).strip() for item in debug_source_documents if str(item).strip())
    return list(dict.fromkeys(document_ids))


def _result_requires_review(result: ProductWorkflowResult) -> bool:
    payload = result.structured_result.validated_output if result.structured_result is not None else None
    if isinstance(payload, DocumentAgentPayload) and payload.needs_review:
        return True
    return result.status == "warning"


def _first_configured_trello_list_id(*candidates: object) -> str:
    for candidate in candidates:
        normalized = str(candidate or "").strip()
        if normalized:
            return normalized
    raise ValueError("No Trello target list is configured for card creation.")


def _trello_list_label_for_id(list_id: str, settings: EvidenceOpsExternalSettings) -> str:
    catalog = {
        str(settings.trello.list_open_id or "").strip(): "Open",
        str(settings.trello.list_review_id or "").strip(): "Review",
        str(settings.trello.list_approved_id or "").strip(): "Approved",
        str(settings.trello.list_done_id or "").strip(): "Done",
    }
    return catalog.get(str(list_id or "").strip(), "Configured target")


def _resolve_trello_target_list_id(
    *,
    result: ProductWorkflowResult,
    settings: EvidenceOpsExternalSettings,
) -> str:
    if _result_requires_review(result) and str(settings.trello.list_review_id or "").strip():
        return str(settings.trello.list_review_id)
    return _first_configured_trello_list_id(
        settings.trello.list_open_id,
        settings.trello.list_review_id,
        settings.trello.list_approved_id,
        settings.trello.list_done_id,
    )


def _resolve_trello_target_list_id_for_action_item(
    *,
    action_item: dict[str, Any],
    result: ProductWorkflowResult,
    settings: EvidenceOpsExternalSettings,
) -> str:
    status = str(action_item.get("status") or "").strip().lower()
    kanban_stage = str(action_item.get("kanban_stage") or "").strip().lower()

    done_statuses = {"done", "completed", "closed", "resolved"}
    review_statuses = {
        "blocked",
        "review",
        "needs_review",
        "pending_review",
        "awaiting_review",
        "awaiting_approval",
        "pending_approval",
    }
    active_statuses = {"in_progress", "doing", "active", "executing", "approved"}
    open_statuses = {"open", "todo", "to_do", "suggested", "backlog", "pending"}

    if status in done_statuses or kanban_stage == "done":
        return _first_configured_trello_list_id(
            settings.trello.list_done_id,
            settings.trello.list_approved_id,
            settings.trello.list_open_id,
            settings.trello.list_review_id,
        )
    if status in review_statuses or kanban_stage in {"blocked", "review"}:
        return _first_configured_trello_list_id(
            settings.trello.list_review_id,
            settings.trello.list_open_id,
            settings.trello.list_approved_id,
            settings.trello.list_done_id,
        )
    if status in active_statuses or kanban_stage in {"doing", "in progress", "approved"}:
        return _first_configured_trello_list_id(
            settings.trello.list_approved_id,
            settings.trello.list_open_id,
            settings.trello.list_review_id,
            settings.trello.list_done_id,
        )
    if status in open_statuses or kanban_stage in {"to do", "todo", "open"}:
        return _first_configured_trello_list_id(
            settings.trello.list_open_id,
            settings.trello.list_approved_id,
            settings.trello.list_review_id,
            settings.trello.list_done_id,
        )
    if _result_requires_review(result) and str(settings.trello.list_review_id or "").strip():
        return str(settings.trello.list_review_id)
    return _resolve_trello_target_list_id(result=result, settings=settings)


def _build_trello_list_breakdown(cards: list[dict[str, Any]], settings: EvidenceOpsExternalSettings) -> list[dict[str, Any]]:
    ordered_ids = [
        str(settings.trello.list_open_id or "").strip(),
        str(settings.trello.list_review_id or "").strip(),
        str(settings.trello.list_approved_id or "").strip(),
        str(settings.trello.list_done_id or "").strip(),
    ]
    counts: dict[str, int] = {}
    for card in cards:
        list_id = str(card.get("list_id") or "").strip()
        if not list_id:
            continue
        counts[list_id] = counts.get(list_id, 0) + 1
    breakdown: list[dict[str, Any]] = []
    for list_id in ordered_ids:
        if not list_id or list_id not in counts:
            continue
        breakdown.append(
            {
                "list_id": list_id,
                "list_label": _trello_list_label_for_id(list_id, settings),
                "count": counts[list_id],
            }
        )
    for list_id, count in counts.items():
        if list_id in ordered_ids:
            continue
        breakdown.append({"list_id": list_id, "list_label": _trello_list_label_for_id(list_id, settings), "count": count})
    return breakdown


def _candidate_card_name(result: ProductWorkflowResult, payload: CVAnalysisPayload) -> str:
    candidate_name = _candidate_full_name(payload)
    if candidate_name:
        return _trim_text(f"Candidate brief — {candidate_name}", max_chars=120)
    return _trim_text(f"Candidate brief — {result.recommendation or result.summary or result.workflow_id}", max_chars=120)


def _build_product_result_card_description(
    *,
    result: ProductWorkflowResult,
    document_ids: list[str],
    action_item: dict[str, Any] | None = None,
    preview_payload: dict[str, Any] | None = None,
) -> str:
    del document_ids
    payload = result.structured_result.validated_output if result.structured_result is not None else None
    summary = _preview_string((preview_payload or {}).get("summary"), max_chars=220) or _trim_text(_derive_publish_summary(result), max_chars=220)
    highlights = _preview_items_from_keys(preview_payload, "highlights", "strengths", max_items=3) or _derive_publish_highlights(result)[:3]
    recommendation = _preview_string((preview_payload or {}).get("recommendation"), max_chars=220)
    if not recommendation:
        fallback_recommendation = _derive_publish_recommendation(result)
        recommendation = _trim_text(fallback_recommendation, max_chars=220) if fallback_recommendation else None
    evidence = _preview_documents(preview_payload, result)[:4]
    warnings = _preview_items_from_keys(preview_payload, "watchouts", max_items=3) or _derive_publish_warnings(result)[:3]
    interview_focus = _preview_items_from_keys(preview_payload, "interview_focus", "interview_questions", max_items=3)
    if not interview_focus and isinstance(payload, CVAnalysisPayload):
        interview_focus = _derive_candidate_interview_focus(payload)[:3]
    return _build_trello_markdown_sections(
        title=_derive_publish_title(result),
        summary=summary,
        highlights=highlights,
        recommendation=recommendation,
        evidence=evidence,
        warnings=warnings,
        action_item=action_item,
        interview_focus=interview_focus,
    )


def _build_product_result_trello_cards(
    *,
    result: ProductWorkflowResult,
    settings: EvidenceOpsExternalSettings,
    max_cards: int = 8,
    preview_payload: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], str]:
    document_ids = _result_document_ids(result)
    payload = result.structured_result.validated_output if result.structured_result is not None else None
    cards: list[dict[str, Any]] = []

    if result.workflow_id == "action_plan_evidence_review":
        try:
            action_plan_view = build_action_plan_view(result)
        except Exception:
            action_plan_view = {}
        items = action_plan_view.get("items") if isinstance(action_plan_view, dict) else None
        if isinstance(items, list):
            for item in items[:max_cards]:
                if not isinstance(item, dict):
                    continue
                action_name = _trim_text(item.get("title") or "Action plan item", max_chars=96)
                cards.append(
                    {
                        "name": _trim_text(f"[{result.workflow_label}] {action_name}", max_chars=120),
                        "description": _build_product_result_card_description(
                            result=result,
                            document_ids=document_ids,
                            action_item=item,
                            preview_payload=preview_payload,
                        ),
                        "list_id": _resolve_trello_target_list_id_for_action_item(
                            action_item=item,
                            result=result,
                            settings=settings,
                        ),
                    }
                )
            if cards:
                return cards, "action_plan_items"

    target_list_id = _resolve_trello_target_list_id(result=result, settings=settings)

    if isinstance(payload, DocumentAgentPayload):
        worklog_entry = build_evidenceops_worklog_entry(
            payload=payload,
            query=result.recommendation or result.summary,
            document_ids=document_ids,
            execution_metadata={
                "workflow_id": result.workflow_id,
                "workflow_label": result.workflow_label,
                "product_surface": "gradio",
            },
        )
        action_items = worklog_entry.get("action_items") if isinstance(worklog_entry.get("action_items"), list) else []
        for item in action_items[:max_cards]:
            if not isinstance(item, dict):
                continue
            action_name = _trim_text(item.get("description") or "EvidenceOps action", max_chars=96)
            cards.append(
                {
                    "name": _trim_text(f"[{result.workflow_label}] {action_name}", max_chars=120),
                    "description": _build_product_result_card_description(
                        result=result,
                        document_ids=document_ids,
                        action_item=item,
                    ),
                    "list_id": target_list_id,
                }
            )
        if cards:
            return cards, "action_items"

    if isinstance(payload, CVAnalysisPayload):
        card_name = _candidate_card_name(result, payload)
    else:
        card_name = _derive_publish_title(result)
    cards.append(
        {
            "name": card_name,
            "description": _build_product_result_card_description(result=result, document_ids=document_ids, preview_payload=preview_payload),
            "list_id": target_list_id,
        }
    )
    return cards, "summary"


def create_trello_cards_from_product_result(
    result: ProductWorkflowResult,
    *,
    settings: EvidenceOpsExternalSettings | None = None,
    dry_run: bool = True,
    max_cards: int = 8,
    preview_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(result, ProductWorkflowResult):
        raise ValueError("A valid ProductWorkflowResult is required to create Trello cards.")

    resolved_settings = settings or get_evidenceops_external_settings()
    missing_fields = [
        field_name
        for field_name, value in {
            "api_key": resolved_settings.trello.api_key,
            "token": resolved_settings.trello.token,
            "board_id": resolved_settings.trello.board_id,
            "list_open_id": resolved_settings.trello.list_open_id,
        }.items()
        if not str(value or "").strip()
    ]
    if missing_fields:
        raise ValueError(f"Trello is not fully configured. Missing: {', '.join(missing_fields)}")

    cards, card_mode = _build_product_result_trello_cards(
        result=result,
        settings=resolved_settings,
        max_cards=max_cards,
        preview_payload=preview_payload,
    )
    list_breakdown = _build_trello_list_breakdown(cards, resolved_settings)
    plan = {
        "status": "planned" if dry_run else "success",
        "dry_run": bool(dry_run),
        "workflow_id": result.workflow_id,
        "workflow_label": result.workflow_label,
        "card_mode": card_mode,
        "target_board_id": resolved_settings.trello.board_id or None,
        "board_url": (f"https://trello.com/b/{resolved_settings.trello.board_id}" if str(resolved_settings.trello.board_id or "").strip() else None),
        "planned_card_count": len(cards),
        "planned_cards": cards,
        "list_breakdown": list_breakdown,
    }
    if dry_run:
        plan.setdefault(
            "message",
            "Planned Trello publish by list: " + ", ".join(f"{item['list_label']}: {item['count']}" for item in list_breakdown) if list_breakdown else "Planned Trello publish.",
        )
        return plan

    trello = TrelloClient(resolved_settings.trello)
    created_cards = [
        trello.create_card(
            list_id=str(card.get("list_id") or resolved_settings.trello.list_open_id),
            name=str(card.get("name") or "EvidenceOps workflow result"),
            description=str(card.get("description") or ""),
        )
        for card in cards
    ]
    return {
        **plan,
        "status": "success",
        "dry_run": False,
        "message": (
            f"Published {len(created_cards)} card(s) to Trello"
            + (" — " + ", ".join(f"{item['list_label']}: {item['count']}" for item in list_breakdown) if list_breakdown else ".")
        ),
        "created_cards": created_cards,
        "created_card_count": len(created_cards),
        "created_card_urls": [
            str(item.get("url"))
            for item in created_cards
            if isinstance(item, dict) and str(item.get("url") or "").strip()
        ],
    }


def create_trello_smoke_card(
    *,
    settings: EvidenceOpsExternalSettings | None = None,
    dry_run: bool = False,
    title_prefix: str = "[TEST] Gradio Trello smoke",
    description: str = "Smoke test card created from the Gradio UI integration test.",
) -> dict[str, Any]:
    resolved_settings = settings or get_evidenceops_external_settings()
    missing_fields = [
        field_name
        for field_name, value in {
            "api_key": resolved_settings.trello.api_key,
            "token": resolved_settings.trello.token,
            "board_id": resolved_settings.trello.board_id,
            "list_open_id": resolved_settings.trello.list_open_id,
        }.items()
        if not str(value or "").strip()
    ]
    if missing_fields:
        raise ValueError(f"Trello is not fully configured. Missing: {', '.join(missing_fields)}")

    card_name = f"{_trim_text(title_prefix, max_chars=72)} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    plan = {
        "status": "planned" if dry_run else "success",
        "dry_run": bool(dry_run),
        "target_board_id": resolved_settings.trello.board_id or None,
        "target_list_id": resolved_settings.trello.list_open_id or None,
        "name": card_name,
        "description": description,
    }
    if dry_run:
        return plan

    trello = TrelloClient(resolved_settings.trello)
    created_card = trello.create_card(
        list_id=str(resolved_settings.trello.list_open_id),
        name=card_name,
        description=description,
    )
    return {
        **plan,
        "status": "success",
        "dry_run": False,
        "card": created_card,
        "card_url": created_card.get("url"),
        "card_id": created_card.get("id"),
    }


class NotionClient:
    base_url = "https://api.notion.com/v1"

    def __init__(self, settings: NotionSettings) -> None:
        self.settings = settings

    def _request(self, method: str, path: str, *, body: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Notion-Version": self.settings.api_version,
            "Content-Type": "application/json",
        }
        data = json.dumps(body or {}, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/{path.lstrip('/')}",
            data=data,
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(request, timeout=30) as response:  # pragma: no cover - network integration
            return json.loads(response.read().decode("utf-8"))

    def query_database(self, *, body: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("POST", f"databases/{self.settings.database_id}/query", body=body or {})

    def retrieve_database(self) -> dict[str, Any]:
        return self._request("GET", f"databases/{self.settings.database_id}")

    def create_page(self, *, title: str, properties: dict[str, Any], children: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        payload = {
            "parent": {"database_id": self.settings.database_id},
            "properties": {
                "Name": {
                    "title": [{"type": "text", "text": {"content": title}}],
                },
                **properties,
            },
        }
        if children:
            payload["children"] = children
        return self._request("POST", "pages", body=payload)


def _require_notion_settings(settings: EvidenceOpsExternalSettings) -> None:
    missing_fields = [
        field_name
        for field_name, value in {
            "api_key": settings.notion.api_key,
            "database_id": settings.notion.database_id,
        }.items()
        if not str(value or "").strip()
    ]
    if missing_fields:
        raise ValueError(f"Notion is not fully configured. Missing: {', '.join(missing_fields)}")


def _build_notion_rich_text(content: object) -> list[dict[str, Any]]:
    normalized = _trim_text(content, max_chars=1800)
    if not normalized:
        return []
    return [{"type": "text", "text": {"content": normalized}}]


def _build_notion_paragraph_block(content: object) -> dict[str, Any] | None:
    rich_text = _build_notion_rich_text(content)
    if not rich_text:
        return None
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": rich_text},
    }


def _extract_notion_page_title(page: dict[str, Any]) -> str:
    properties = page.get("properties") if isinstance(page.get("properties"), dict) else {}
    name_property = properties.get("Name") if isinstance(properties.get("Name"), dict) else {}
    title_items = name_property.get("title") if isinstance(name_property.get("title"), list) else []
    title = "".join(
        str(item.get("plain_text") or "")
        for item in title_items
        if isinstance(item, dict)
    ).strip()
    if title:
        return title
    for property_value in properties.values():
        if not isinstance(property_value, dict):
            continue
        title_items = property_value.get("title") if isinstance(property_value.get("title"), list) else []
        title = "".join(
            str(item.get("plain_text") or "")
            for item in title_items
            if isinstance(item, dict)
        ).strip()
        if title:
            return title
    return str(page.get("id") or "Untitled Notion page")


def _build_notion_heading_block(content: object, *, level: int = 2) -> dict[str, Any] | None:
    rich_text = _build_notion_rich_text(content)
    if not rich_text:
        return None
    block_type = "heading_3" if int(level) >= 3 else "heading_2"
    return {
        "object": "block",
        "type": block_type,
        block_type: {"rich_text": rich_text},
    }


def _build_notion_bulleted_list_item(content: object) -> dict[str, Any] | None:
    rich_text = _build_notion_rich_text(content)
    if not rich_text:
        return None
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": rich_text},
    }


def _normalize_notion_property_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())


def _looks_like_document_hash(value: object) -> bool:
    normalized = str(value or "").strip().lower()
    return bool(normalized) and len(normalized) >= 32 and all(character in "0123456789abcdef" for character in normalized)


def _candidate_full_name(payload: CVAnalysisPayload | None) -> str | None:
    if payload is None or payload.personal_info is None:
        return None
    full_name = _trim_text(getattr(payload.personal_info, "full_name", ""), max_chars=80)
    return full_name or None


def _extract_result_document_labels(result: ProductWorkflowResult) -> list[str]:
    payload = result.structured_result.validated_output if result.structured_result is not None else None
    labels: list[str] = []
    if isinstance(payload, DocumentAgentPayload):
        for source in payload.sources[:8]:
            source_label = _trim_text(getattr(source, "source", ""), max_chars=120)
            if source_label and not _looks_like_document_hash(source_label):
                labels.append(source_label)
        for name in payload.compared_documents[:6]:
            normalized = _trim_text(name, max_chars=120)
            if normalized and not _looks_like_document_hash(normalized):
                labels.append(normalized)
    if isinstance(payload, CVAnalysisPayload):
        candidate_name = _candidate_full_name(payload)
        if candidate_name:
            labels.append(f"{candidate_name} CV")
    debug_document_names = result.debug_metadata.get("documents") if isinstance(result.debug_metadata, dict) else None
    if isinstance(debug_document_names, list):
        for item in debug_document_names[:8]:
            normalized = _trim_text(item, max_chars=120)
            if normalized and not _looks_like_document_hash(normalized):
                labels.append(normalized)
    return list(dict.fromkeys(item for item in labels if item))


def _result_storyline_id(result: ProductWorkflowResult) -> str | None:
    workflow_id = str(result.workflow_id or "").strip()
    primary_document = next((item for item in _result_document_ids(result) if str(item).strip()), None)
    if workflow_id and primary_document:
        return f"{workflow_id}:{primary_document[:12]}"
    return workflow_id or None


def _result_corpus_label(result: ProductWorkflowResult) -> str | None:
    return "Hiring packet" if result.workflow_id == "candidate_review" else "Northwind vendor operations"


def _split_summary_sentences(text: object, *, limit: int = 3) -> list[str]:
    normalized = str(text or "").strip()
    if not normalized:
        return []
    pieces = [
        piece.strip(" -•\n\t")
        for piece in re.split(r"(?<=[.!?])\s+|\n+", normalized)
        if piece.strip(" -•\n\t")
    ]
    deduped: list[str] = []
    for piece in pieces:
        compact = _trim_text(piece, max_chars=220)
        if compact and compact not in deduped:
            deduped.append(compact)
        if len(deduped) >= limit:
            break
    return deduped


def _derive_publish_title(result: ProductWorkflowResult) -> str:
    payload = result.structured_result.validated_output if result.structured_result is not None else None
    document_labels = _extract_result_document_labels(result)
    if isinstance(payload, CVAnalysisPayload):
        candidate_name = _candidate_full_name(payload) or "Candidate"
        return _trim_text(f"Candidate brief — {candidate_name}", max_chars=120)
    if result.workflow_id == "policy_contract_comparison":
        if len(document_labels) >= 2:
            left = document_labels[0].replace('.pdf', '')
            right = document_labels[1].replace('.pdf', '')
            return _trim_text(f"Policy comparison — {left} vs {right}", max_chars=120)
        return _trim_text("Policy comparison — evidence and access governance", max_chars=120)
    if result.workflow_id == "document_review":
        if document_labels:
            return _trim_text(f"Document review — {document_labels[0].replace('.pdf', '')}", max_chars=120)
        return _trim_text(f"Document review — {result.recommendation or result.summary}", max_chars=120)
    if result.workflow_id == "action_plan_evidence_review":
        return _trim_text(f"Action plan — {result.recommendation or result.summary}", max_chars=120)
    if isinstance(payload, CVAnalysisPayload) and payload.personal_info is not None:
        full_name = _trim_text(getattr(payload.personal_info, "full_name", ""), max_chars=64)
        if full_name:
            return _trim_text(f"[{result.workflow_label}] {full_name}", max_chars=120)
    return _trim_text(f"[{result.workflow_label}] {result.recommendation or result.summary or result.workflow_id}", max_chars=120)


def _derive_publish_summary(result: ProductWorkflowResult) -> str:
    payload = result.structured_result.validated_output if result.structured_result is not None else None
    if isinstance(payload, CVAnalysisPayload):
        candidate_name = _candidate_full_name(payload) or "The candidate"
        strengths = list(dict.fromkeys(_trim_text(item, max_chars=80) for item in payload.strengths[:3] if str(item).strip()))
        bits = [f"{candidate_name} reads as a strong senior-profile candidate."]
        if strengths:
            bits.append(f"Best-supported strengths: {', '.join(strengths)}.")
        if result.recommendation:
            bits.append(_trim_text(result.recommendation, max_chars=220))
        return " ".join(bits)
    sentences = _split_summary_sentences(result.summary, limit=2)
    return " ".join(sentences) if sentences else _trim_text(result.summary, max_chars=280)


def _derive_publish_highlights(result: ProductWorkflowResult) -> list[str]:
    payload = result.structured_result.validated_output if result.structured_result is not None else None
    highlights: list[str] = []
    if isinstance(payload, CVAnalysisPayload):
        highlights.extend(_trim_text(item, max_chars=140) for item in (payload.strengths or [])[:4] if str(item).strip())
        if payload.improvement_areas:
            highlights.append("Validation focus: " + ", ".join(_trim_text(item, max_chars=40) for item in payload.improvement_areas[:3] if str(item).strip()))
    elif isinstance(payload, DocumentAgentPayload) and payload.key_points:
        highlights.extend(_trim_text(item, max_chars=160) for item in payload.key_points[:5] if str(item).strip())
    if not highlights:
        highlights.extend(_trim_text(item, max_chars=160) for item in result.highlights[:5] if str(item).strip())
    return list(dict.fromkeys(item for item in highlights if item))[:5]


def _derive_publish_recommendation(result: ProductWorkflowResult) -> str | None:
    if result.recommendation:
        return _trim_text(result.recommendation, max_chars=240)
    sentences = _split_summary_sentences(result.summary, limit=1)
    return sentences[0] if sentences else None


def _derive_candidate_interview_focus(payload: CVAnalysisPayload | None) -> list[str]:
    if payload is None:
        return []
    focus_items = [_trim_text(item, max_chars=120) for item in payload.improvement_areas[:4] if str(item).strip()]
    if not focus_items and payload.projects:
        focus_items = [_trim_text(item, max_chars=120) for item in payload.projects[:3] if str(item).strip()]
    return list(dict.fromkeys(item for item in focus_items if item))[:4]


def _derive_publish_warnings(result: ProductWorkflowResult) -> list[str]:
    payload = result.structured_result.validated_output if result.structured_result is not None else None
    warnings = [_trim_text(item, max_chars=160) for item in result.warnings[:4] if str(item).strip()]
    if isinstance(payload, DocumentAgentPayload):
        warnings.extend(_trim_text(item, max_chars=160) for item in payload.limitations[:3] if str(item).strip())
    return list(dict.fromkeys(item for item in warnings if item))[:4]


def _build_trello_markdown_sections(*, title: str, summary: str, highlights: list[str], recommendation: str | None, evidence: list[str], warnings: list[str], action_item: dict[str, Any] | None = None, interview_focus: list[str] | None = None) -> str:
    lines: list[str] = [f"## {title}", ""]
    if summary:
        lines.extend(["### Summary", summary, ""])
    if highlights:
        lines.append("### Highlights")
        lines.extend([f"- {item}" for item in highlights])
        lines.append("")
    if interview_focus:
        lines.append("### Interview focus")
        lines.extend([f"- {item}" for item in interview_focus if str(item).strip()])
        lines.append("")
    if action_item:
        action_details = []
        for label, key in [("Owner", "owner"), ("Due date", "due_date"), ("Status", "status"), ("Evidence", "evidence")]:
            value = _trim_text(action_item.get(key), max_chars=180)
            if value:
                action_details.append(f"- **{label}:** {value}")
        if action_details:
            lines.append("### Action details")
            lines.extend(action_details)
            lines.append("")
    if recommendation:
        lines.extend(["### Recommendation", recommendation, ""])
    if evidence:
        lines.append("### Evidence used")
        lines.extend([f"- {item}" for item in evidence])
        lines.append("")
    if warnings:
        lines.append("### Watchouts")
        lines.extend([f"- {item}" for item in warnings])
        lines.append("")
    return "\n".join(line for line in lines).strip()


def _build_notion_property_value(property_type: str, value: object) -> dict[str, Any] | None:
    normalized_type = str(property_type or "").strip().lower()
    if normalized_type == "title":
        rich_text = _build_notion_rich_text(value)
        return {"title": rich_text} if rich_text else None
    if normalized_type in {"rich_text", "text"}:
        rich_text = _build_notion_rich_text(value)
        return {"rich_text": rich_text} if rich_text else None
    if normalized_type == "select":
        name = _trim_text(value, max_chars=90)
        return {"select": {"name": name}} if name else None
    if normalized_type == "multi_select":
        if isinstance(value, list):
            items = [{"name": _trim_text(item, max_chars=90)} for item in value if _trim_text(item, max_chars=90)]
        else:
            items = [{"name": _trim_text(value, max_chars=90)}] if _trim_text(value, max_chars=90) else []
        return {"multi_select": items} if items else None
    if normalized_type == "url":
        url = str(value or "").strip()
        return {"url": url} if url else None
    return None


def _select_notion_property(database_properties: dict[str, Any], candidate_names: list[str], allowed_types: set[str]) -> tuple[str, str] | None:
    normalized_candidates = {_normalize_notion_property_key(item) for item in candidate_names if str(item).strip()}
    for property_name, property_payload in database_properties.items():
        if not isinstance(property_payload, dict):
            continue
        property_type = str(property_payload.get("type") or "").strip().lower()
        if property_type not in allowed_types:
            continue
        if _normalize_notion_property_key(property_name) in normalized_candidates:
            return property_name, property_type
    return None


def _build_notion_properties_for_result(*, result: ProductWorkflowResult, database_properties: dict[str, Any]) -> dict[str, Any]:
    payload = result.structured_result.validated_output if result.structured_result is not None else None
    summary = _derive_publish_summary(result)
    recommendation = _derive_publish_recommendation(result)
    document_labels = _extract_result_document_labels(result)
    primary_document = document_labels[0] if document_labels else None
    supporting_documents = document_labels[1:4] if len(document_labels) > 1 else []
    property_values: list[tuple[list[str], object]] = [
        (["Storyline ID", "StorylineID", "Storyline"], _result_storyline_id(result)),
        (["Corpus"], _result_corpus_label(result)),
        (["Primary Document", "Primary Documents"], primary_document),
        (["Supporting Documents", "Supporting Document"], supporting_documents if supporting_documents else None),
        (["Workflow"], result.workflow_label),
        (["Status", "Run status", "Run Status"], result.status.title()),
        (["Recommendation"], recommendation),
        (["Summary", "Executive Summary"], summary),
        (["Highlights", "Key Highlights"], _derive_publish_highlights(result)),
    ]
    if isinstance(payload, CVAnalysisPayload):
        interview_focus = _derive_candidate_interview_focus(payload)
        property_values.append((["Interview Focus", "Interview focus"], interview_focus if interview_focus else None))
        candidate_name = _candidate_full_name(payload)
        if candidate_name:
            property_values.append((["Candidate", "Candidate Name"], candidate_name))
    properties: dict[str, Any] = {}
    for candidate_names, raw_value in property_values:
        if raw_value in (None, "", [], {}):
            continue
        match = _select_notion_property(database_properties, candidate_names, {"rich_text", "select", "multi_select", "url", "title"})
        if not match:
            continue
        property_name, property_type = match
        property_payload = _build_notion_property_value(property_type, raw_value)
        if property_payload:
            properties[property_name] = property_payload
    return properties


def _build_notion_children_for_result(result: ProductWorkflowResult) -> list[dict[str, Any]]:
    payload = result.structured_result.validated_output if result.structured_result is not None else None
    summary = _derive_publish_summary(result)
    recommendation = _derive_publish_recommendation(result)
    highlights = _derive_publish_highlights(result)
    warnings = _derive_publish_warnings(result)
    document_labels = _extract_result_document_labels(result)
    interview_focus = _derive_candidate_interview_focus(payload) if isinstance(payload, CVAnalysisPayload) else []
    blocks: list[dict[str, Any] | None] = [
        _build_notion_heading_block("Executive summary", level=2),
        _build_notion_paragraph_block(summary),
    ]
    if highlights:
        blocks.append(_build_notion_heading_block("Key highlights", level=2))
        blocks.extend(_build_notion_bulleted_list_item(item) for item in highlights)
    if interview_focus:
        blocks.append(_build_notion_heading_block("Interview focus", level=2))
        blocks.extend(_build_notion_bulleted_list_item(item) for item in interview_focus)
    if recommendation:
        blocks.extend([
            _build_notion_heading_block("Recommendation", level=2),
            _build_notion_paragraph_block(recommendation),
        ])
    if document_labels:
        blocks.append(_build_notion_heading_block("Evidence used", level=2))
        blocks.extend(_build_notion_bulleted_list_item(item) for item in document_labels[:5])
    if warnings:
        blocks.append(_build_notion_heading_block("Watchouts", level=2))
        blocks.extend(_build_notion_bulleted_list_item(item) for item in warnings[:4])
    return [item for item in blocks if item is not None]


def list_notion_database_entries(
    *,
    settings: EvidenceOpsExternalSettings | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    resolved_settings = settings or get_evidenceops_external_settings()
    _require_notion_settings(resolved_settings)
    notion = NotionClient(resolved_settings.notion)
    response = notion.query_database(body={"page_size": max(1, min(int(limit), 100))})
    results = response.get("results") if isinstance(response.get("results"), list) else []
    entries = [
        {
            "id": str(item.get("id") or ""),
            "page_url": str(item.get("url") or "") or None,
            "title": _extract_notion_page_title(item) if isinstance(item, dict) else "Untitled",
            "created_time": str(item.get("created_time") or "") or None,
            "last_edited_time": str(item.get("last_edited_time") or "") or None,
        }
        for item in results
        if isinstance(item, dict)
    ]
    return {
        "status": "success",
        "database_id": resolved_settings.notion.database_id,
        "entry_count": len(entries),
        "entries": entries,
    }


def create_notion_smoke_page(
    *,
    settings: EvidenceOpsExternalSettings | None = None,
    dry_run: bool = False,
    title_prefix: str = "[TEST] Gradio Notion smoke",
) -> dict[str, Any]:
    resolved_settings = settings or get_evidenceops_external_settings()
    _require_notion_settings(resolved_settings)
    title = f"{_trim_text(title_prefix, max_chars=72)} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    children = [
        _build_notion_paragraph_block("Smoke test page created from the Gradio UI integration test."),
        _build_notion_paragraph_block("If this page exists in the configured database, the Notion integration is working."),
    ]
    children = [item for item in children if item is not None]
    plan = {
        "status": "planned" if dry_run else "success",
        "dry_run": bool(dry_run),
        "database_id": resolved_settings.notion.database_id,
        "title": title,
        "children_count": len(children),
    }
    if dry_run:
        return plan

    notion = NotionClient(resolved_settings.notion)
    page = notion.create_page(title=title, properties={}, children=children)
    return {
        **plan,
        "status": "success",
        "dry_run": False,
        "page_id": page.get("id"),
        "page_title": title,
        "page_url": page.get("url"),
    }



_PRODUCT_NOTION_TEMPLATE_CATALOG: dict[str, list[dict[str, str]]] = {
    "action_plan_evidence_review": [
        {"id": "action_register", "label": "Action register", "description": "Owners, priorities and due dates."},
        {"id": "executive_summary", "label": "Executive summary", "description": "Narrative handoff for stakeholders."},
        {"id": "evidence_gaps", "label": "Evidence gaps", "description": "Missing evidence before execution."},
    ],
    "candidate_review": [
        {"id": "candidate_brief", "label": "Candidate brief", "description": "Hiring summary with strengths and risks."},
        {"id": "interview_plan", "label": "Interview plan", "description": "Validation focus for interviewers."},
    ],
    "document_review": [
        {"id": "review_summary", "label": "Review summary", "description": "Decision summary and next steps."},
        {"id": "findings_register", "label": "Findings register", "description": "Structured finding log and remediation."},
    ],
    "policy_contract_comparison": [
        {"id": "comparison_memo", "label": "Comparison memo", "description": "Executive delta summary."},
        {"id": "remediation_register", "label": "Remediation register", "description": "Must-fix items and negotiation priorities."},
    ],
}


def _product_notion_template_options(workflow_id: str) -> list[dict[str, str]]:
    options = _PRODUCT_NOTION_TEMPLATE_CATALOG.get(str(workflow_id or "").strip(), [])
    if options:
        return [dict(item) for item in options]
    return [{"id": "executive_summary", "label": "Executive summary", "description": "Default workflow handoff."}]


def _resolve_product_notion_template(workflow_id: str, template_id: str | None) -> dict[str, str]:
    options = _product_notion_template_options(workflow_id)
    requested_template_id = str(template_id or "").strip()
    for option in options:
        if option.get("id") == requested_template_id:
            return dict(option)
    return dict(options[0])


def _preview_string(value: object, *, max_chars: int = 180) -> str | None:
    normalized = _trim_text(value, max_chars=max_chars)
    return normalized or None


def _preview_items_from_value(value: object, *, max_items: int = 6) -> list[str]:
    items: list[str] = []
    if isinstance(value, list):
        for entry in value:
            if isinstance(entry, dict):
                pieces = [_preview_string(entry.get(key), max_chars=72) for key in ("title", "name", "label", "summary", "detail", "impact", "recommendation", "owner", "priority", "status")]
                compact = " — ".join(piece for piece in pieces if piece)
                if compact:
                    items.append(compact)
            else:
                normalized = _preview_string(entry)
                if normalized:
                    items.append(normalized)
    elif isinstance(value, dict):
        pieces = [_preview_string(value.get(key), max_chars=72) for key in ("title", "name", "label", "summary", "detail", "impact", "recommendation", "owner", "priority", "status")]
        compact = " — ".join(piece for piece in pieces if piece)
        if compact:
            items.append(compact)
    else:
        normalized = _preview_string(value)
        if normalized:
            items.append(normalized)
    deduped: list[str] = []
    for item in items:
        if item not in deduped:
            deduped.append(item)
        if len(deduped) >= max_items:
            break
    return deduped


def _preview_items_from_keys(preview_payload: dict[str, Any] | None, *keys: str, max_items: int = 6) -> list[str]:
    if not isinstance(preview_payload, dict):
        return []
    collected: list[str] = []
    for key in keys:
        collected.extend(_preview_items_from_value(preview_payload.get(key), max_items=max_items))
        if len(collected) >= max_items:
            break
    deduped: list[str] = []
    for item in collected:
        if item not in deduped:
            deduped.append(item)
        if len(deduped) >= max_items:
            break
    return deduped


def _preview_documents(preview_payload: dict[str, Any] | None, result: ProductWorkflowResult) -> list[str]:
    documents = _preview_items_from_keys(preview_payload, "documents", "primary_documents", max_items=5)
    if documents:
        return documents
    return _extract_result_document_labels(result)[:5]


def _build_product_notion_preview_sections(
    result: ProductWorkflowResult,
    *,
    template_id: str | None = None,
    preview_payload: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    template = _resolve_product_notion_template(result.workflow_id, template_id)
    summary = _preview_string((preview_payload or {}).get("summary")) or _derive_publish_summary(result)
    recommendation = _preview_string((preview_payload or {}).get("recommendation")) or _derive_publish_recommendation(result)
    highlights = _preview_items_from_keys(preview_payload, "highlights", "strengths") or _derive_publish_highlights(result)
    next_steps = _preview_items_from_keys(preview_payload, "next_steps")
    findings = _preview_items_from_keys(preview_payload, "findings", "differences")
    actions = _preview_items_from_keys(preview_payload, "actions")
    evidence_gaps = _preview_items_from_keys(preview_payload, "evidence_gaps")
    must_fix_items = _preview_items_from_keys(preview_payload, "must_fix_items")
    negotiation_priorities = _preview_items_from_keys(preview_payload, "negotiation_priorities")
    watchouts = _preview_items_from_keys(preview_payload, "watchouts") or _derive_publish_warnings(result)
    interview_focus = _preview_items_from_keys(preview_payload, "interview_focus", "interview_questions")
    documents = _preview_documents(preview_payload, result)
    candidate_bits = _preview_items_from_keys(preview_payload, "candidate_name", "candidate_headline", "candidate_location", max_items=4)

    sections: list[dict[str, Any]] = []

    def add_section(heading: str, items: list[str] | None = None) -> None:
        normalized_items = [item for item in (items or []) if str(item).strip()]
        if normalized_items:
            sections.append({"heading": heading, "items": normalized_items[:6]})

    template_key = template.get("id") or "executive_summary"
    if template_key == "action_register":
        add_section("Executive summary", [summary] if summary else [])
        add_section("Actions", actions)
        add_section("Evidence gaps", evidence_gaps)
        add_section("Next steps", next_steps)
        add_section("Evidence used", documents)
    elif template_key == "evidence_gaps":
        add_section("Executive summary", [summary] if summary else [])
        add_section("Evidence gaps", evidence_gaps)
        add_section("Recommendation", [recommendation] if recommendation else [])
        add_section("Evidence used", documents)
    elif template_key == "candidate_brief":
        add_section("Candidate profile", candidate_bits)
        add_section("Executive summary", [summary] if summary else [])
        add_section("Strengths", highlights)
        add_section("Watchouts", watchouts)
        add_section("Interview focus", interview_focus)
        add_section("Next steps", next_steps)
        add_section("Evidence used", documents)
    elif template_key == "interview_plan":
        add_section("Candidate profile", candidate_bits)
        add_section("Recommendation", [recommendation] if recommendation else [])
        add_section("Interview focus", interview_focus)
        add_section("Next steps", next_steps)
        add_section("Evidence used", documents)
    elif template_key == "review_summary":
        add_section("Executive summary", [summary] if summary else [])
        add_section("Findings", findings or highlights)
        add_section("Recommendation", [recommendation] if recommendation else [])
        add_section("Next steps", next_steps)
        add_section("Evidence used", documents)
    elif template_key == "findings_register":
        add_section("Executive summary", [summary] if summary else [])
        add_section("Findings", findings or highlights)
        add_section("Remediation", next_steps or ([recommendation] if recommendation else []))
        add_section("Evidence used", documents)
    elif template_key == "comparison_memo":
        add_section("Executive summary", [summary] if summary else [])
        add_section("Must-fix items", must_fix_items or findings)
        add_section("Negotiation priorities", negotiation_priorities)
        add_section("Evidence used", documents)
    elif template_key == "remediation_register":
        add_section("Executive summary", [summary] if summary else [])
        add_section("Must-fix items", must_fix_items or findings)
        add_section("Negotiation priorities", negotiation_priorities)
        add_section("Evidence used", documents)
    else:
        add_section("Executive summary", [summary] if summary else [])
        add_section("Key highlights", highlights)
        add_section("Recommendation", [recommendation] if recommendation else [])
        add_section("Next steps", next_steps)
        add_section("Evidence used", documents)

    if not sections:
        add_section("Executive summary", [_derive_publish_summary(result)])
        add_section("Evidence used", _extract_result_document_labels(result)[:5])
    return sections


def _build_notion_children_from_preview_sections(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any] | None] = []
    for section in sections:
        heading = _preview_string(section.get("heading"), max_chars=80) if isinstance(section, dict) else None
        items = section.get("items") if isinstance(section, dict) else None
        normalized_items = [
            _preview_string(item, max_chars=220)
            for item in (items if isinstance(items, list) else [])
        ]
        normalized_items = [item for item in normalized_items if item]
        if not heading or not normalized_items:
            continue
        blocks.append(_build_notion_heading_block(heading, level=2))
        if len(normalized_items) == 1 and heading.lower() in {"executive summary", "recommendation"}:
            blocks.append(_build_notion_paragraph_block(normalized_items[0]))
        else:
            blocks.extend(_build_notion_bulleted_list_item(item) for item in normalized_items)
    return [item for item in blocks if item is not None]


def _product_result_notion_title(
    result: ProductWorkflowResult,
    *,
    template_id: str | None = None,
    preview_payload: dict[str, Any] | None = None,
) -> str:
    template = _resolve_product_notion_template(result.workflow_id, template_id)
    title_hint = _preview_string((preview_payload or {}).get("title"), max_chars=96)
    if title_hint:
        return _trim_text(f"{template.get('label', 'Executive summary')} — {title_hint}", max_chars=120)
    return _derive_publish_title(result)


def create_notion_page_from_product_result(
    result: ProductWorkflowResult,
    *,
    settings: EvidenceOpsExternalSettings | None = None,
    dry_run: bool = True,
    template_id: str | None = None,
    preview_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(result, ProductWorkflowResult):
        raise ValueError("A valid ProductWorkflowResult is required to create a Notion page.")

    resolved_settings = settings or get_evidenceops_external_settings()
    _require_notion_settings(resolved_settings)

    template = _resolve_product_notion_template(result.workflow_id, template_id)
    title = _product_result_notion_title(result, template_id=template.get("id"), preview_payload=preview_payload)
    preview_sections = _build_product_notion_preview_sections(
        result,
        template_id=template.get("id"),
        preview_payload=preview_payload,
    )
    children = _build_notion_children_from_preview_sections(preview_sections)
    if not children:
        children = _build_notion_children_for_result(result)

    properties: dict[str, Any] = {}
    if not dry_run:
        notion = NotionClient(resolved_settings.notion)
        database = notion.retrieve_database()
        database_properties = database.get("properties") if isinstance(database.get("properties"), dict) else {}
        properties = _build_notion_properties_for_result(result=result, database_properties=database_properties)
    else:
        # Keep dry-run preview independent from remote Notion calls when possible.
        properties = {}

    plan = {
        "status": "planned" if dry_run else "success",
        "dry_run": bool(dry_run),
        "workflow_id": result.workflow_id,
        "workflow_label": result.workflow_label,
        "database_id": resolved_settings.notion.database_id,
        "title": title,
        "children_count": len(children),
        "property_count": len(properties),
        "filled_properties": sorted(properties.keys()),
        "template_id": template.get("id"),
        "template_label": template.get("label"),
        "template_description": template.get("description"),
        "available_templates": _product_notion_template_options(result.workflow_id),
        "preview_sections": preview_sections,
    }
    if dry_run:
        return plan

    notion = NotionClient(resolved_settings.notion)
    page = notion.create_page(title=title, properties=properties, children=children)
    return {
        **plan,
        "status": "success",
        "dry_run": False,
        "page_id": page.get("id"),
        "page_title": title,
        "page_url": page.get("url"),
    }

def sync_phase95_corpus_to_nextcloud(
    *,
    settings: EvidenceOpsExternalSettings | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    resolved_settings = settings or get_evidenceops_external_settings()
    mapping = build_phase95_corpus_mapping(settings=resolved_settings)
    uploads: list[dict[str, Any]] = []

    for directory in mapping.nextcloud_directories:
        local_path = Path(directory["local_path"])
        remote_path = str(directory["remote_path"])
        if not local_path.exists():
            continue
        for file_path in sorted(item for item in local_path.iterdir() if item.is_file()):
            uploads.append(
                {
                    "local_path": str(file_path),
                    "remote_path": f"{remote_path.rstrip('/')}/{file_path.name}",
                }
            )

    result = {
        "dry_run": bool(dry_run),
        "official_demo_corpus": mapping.official_demo_corpus_name,
        "remote_root_path": resolved_settings.nextcloud.root_path,
        "planned_uploads": uploads,
        "planned_upload_count": len(uploads),
    }
    if dry_run:
        return result

    webdav = WebDavClient(resolved_settings.nextcloud)
    synced: list[dict[str, Any]] = []
    webdav.ensure_collection(str(resolved_settings.nextcloud.root_path))
    for directory in mapping.nextcloud_directories:
        webdav.ensure_collection(str(directory["remote_path"]))
    for upload in uploads:
        synced.append(webdav.upload_file(Path(upload["local_path"]), str(upload["remote_path"])))
    return {**result, "synced": synced}


def list_nextcloud_repository_documents(
    *,
    settings: EvidenceOpsExternalSettings | None = None,
    query: str | None = None,
    category: str | None = None,
    suffix: str | None = None,
    document_id: str | None = None,
    limit: int | None = None,
    allowed_suffixes: set[str] | None = None,
    include_fingerprint: bool = False,
) -> list[dict[str, Any]]:
    resolved_settings = settings or get_evidenceops_external_settings()
    webdav = WebDavClient(resolved_settings.nextcloud)
    query_tokens = _tokenize_query(query)
    normalized_category = _normalize_optional_str(category).lower()
    normalized_document_id = _normalize_optional_str(document_id).lower()
    normalized_suffix = _normalize_suffix(suffix)
    suffixes = {item.lower() for item in (allowed_suffixes or DEFAULT_EVIDENCEOPS_REPOSITORY_SUFFIXES)}
    documents: list[dict[str, Any]] = []

    for remote_entry in webdav.list_tree(""):
        relative_path = str(remote_entry.get("relative_path") or "").strip("/")
        if not relative_path:
            continue
        suffix_value = Path(relative_path).suffix.lower()
        if suffix_value not in suffixes:
            continue
        document_category = _resolve_category_from_relative_path(relative_path)
        if normalized_category and document_category.lower() != normalized_category:
            continue
        if normalized_suffix and suffix_value != normalized_suffix:
            continue
        document_id_value = _extract_document_id_from_name(Path(relative_path).name)
        if normalized_document_id and _normalize_optional_str(document_id_value).lower() != normalized_document_id:
            continue
        entry = {
            "document_id": document_id_value,
            "title": _build_title_from_name(Path(relative_path).name),
            "category": document_category,
            "relative_path": relative_path,
            "path": webdav._build_url(relative_path),
            "suffix": suffix_value,
            "size_bytes": int(remote_entry.get("size_bytes") or 0),
            "modified_at": _http_date_to_timestamp(remote_entry.get("modified_at")),
            "etag": _normalize_optional_str(remote_entry.get("etag")) or None,
            "source": "remote",
            "repository_backend": "nextcloud_webdav",
        }
        if include_fingerprint:
            entry["fingerprint"] = _compute_nextcloud_fingerprint(entry)
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


def get_nextcloud_repository_document(
    *,
    settings: EvidenceOpsExternalSettings | None = None,
    relative_path: str | None = None,
    document_id: str | None = None,
) -> dict[str, Any] | None:
    normalized_relative_path = _normalize_optional_str(relative_path)
    normalized_document_id = _normalize_optional_str(document_id)
    for document in list_nextcloud_repository_documents(settings=settings):
        if normalized_relative_path and str(document.get("relative_path") or "") == normalized_relative_path:
            return document
        if normalized_document_id and str(document.get("document_id") or "") == normalized_document_id:
            return document
    return None


def _find_nextcloud_repository_document(
    *,
    settings: EvidenceOpsExternalSettings,
    relative_path: str | None = None,
    document_id: str | None = None,
    filename: str | None = None,
    title: str | None = None,
    category: str | None = None,
    webdav_url: str | None = None,
) -> dict[str, Any] | None:
    normalized_relative_path = _normalize_optional_str(relative_path)
    normalized_document_id = _normalize_optional_str(document_id)
    normalized_filename = _normalize_optional_str(filename).lower()
    normalized_title = _normalize_optional_str(title).lower()
    normalized_category = _normalize_optional_str(category).lower()
    normalized_webdav_url = _normalize_optional_str(webdav_url)

    webdav = WebDavClient(settings.nextcloud)
    if normalized_webdav_url and not normalized_relative_path:
        derived_relative_path = webdav._normalize_remote_relative_path(normalized_webdav_url)
        if derived_relative_path:
            normalized_relative_path = derived_relative_path

    direct_match = get_nextcloud_repository_document(
        settings=settings,
        relative_path=normalized_relative_path or None,
        document_id=normalized_document_id or None,
    )
    if direct_match is not None:
        return direct_match

    documents = list_nextcloud_repository_documents(settings=settings)
    exact_matches: list[dict[str, Any]] = []
    fuzzy_matches: list[dict[str, Any]] = []
    for document in documents:
        document_relative_path = str(document.get("relative_path") or "").strip()
        document_filename = Path(document_relative_path).name.lower()
        document_title = str(document.get("title") or "").strip().lower()
        document_category = str(document.get("category") or "").strip().lower()
        document_webdav_url = str(document.get("path") or document.get("webdav_url") or "").strip()

        if normalized_category and document_category != normalized_category:
            continue
        if normalized_webdav_url and document_webdav_url and document_webdav_url == normalized_webdav_url:
            return document

        score = 0
        exact = False
        if normalized_filename:
            if document_filename == normalized_filename:
                score += 6
                exact = True
            elif normalized_filename in document_filename:
                score += 3
        if normalized_title:
            if document_title == normalized_title:
                score += 5
                exact = True
            elif normalized_title in document_title:
                score += 2
        if normalized_relative_path:
            if document_relative_path == normalized_relative_path:
                score += 10
                exact = True
            elif normalized_relative_path in document_relative_path:
                score += 4
        if normalized_document_id and str(document.get("document_id") or "").strip().lower() == normalized_document_id.lower():
            score += 8
            exact = True
        if score <= 0:
            continue
        if exact:
            exact_matches.append((score, document))
        else:
            fuzzy_matches.append((score, document))

    if exact_matches:
        exact_matches.sort(key=lambda item: (-item[0], str(item[1].get("relative_path") or "")))
        return exact_matches[0][1]
    if fuzzy_matches:
        fuzzy_matches.sort(key=lambda item: (-item[0], str(item[1].get("relative_path") or "")))
        return fuzzy_matches[0][1]
    return None


def download_nextcloud_repository_document(
    *,
    settings: EvidenceOpsExternalSettings | None = None,
    relative_path: str | None = None,
    document_id: str | None = None,
    filename: str | None = None,
    title: str | None = None,
    category: str | None = None,
    webdav_url: str | None = None,
) -> dict[str, Any]:
    resolved_settings = settings or get_evidenceops_external_settings()
    document = _find_nextcloud_repository_document(
        settings=resolved_settings,
        relative_path=relative_path,
        document_id=document_id,
        filename=filename,
        title=title,
        category=category,
        webdav_url=webdav_url,
    )
    if document is None:
        identifier = (
            _normalize_optional_str(relative_path)
            or _normalize_optional_str(document_id)
            or _normalize_optional_str(filename)
            or _normalize_optional_str(title)
            or _normalize_optional_str(webdav_url)
            or "requested document"
        )
        raise FileNotFoundError(f"Nextcloud repository document not found: {identifier}")

    resolved_relative_path = str(document.get("relative_path") or "").strip()
    if not resolved_relative_path:
        raise FileNotFoundError("Nextcloud repository document is missing a relative_path.")

    webdav = WebDavClient(resolved_settings.nextcloud)
    _, content = webdav._request("GET", resolved_relative_path, expected_statuses=(200,))
    resolved_filename = Path(resolved_relative_path).name or _normalize_optional_str(filename) or "remote-document"
    content_type = mimetypes.guess_type(resolved_filename)[0] or "application/octet-stream"
    return {
        **document,
        "filename": resolved_filename,
        "content": content,
        "content_type": content_type,
        "webdav_url": document.get("path") or document.get("webdav_url") or webdav._build_url(resolved_relative_path),
    }


def build_nextcloud_repository_snapshot(
    *,
    settings: EvidenceOpsExternalSettings | None = None,
    allowed_suffixes: set[str] | None = None,
) -> dict[str, Any]:
    resolved_settings = settings or get_evidenceops_external_settings()
    documents = list_nextcloud_repository_documents(
        settings=resolved_settings,
        allowed_suffixes=allowed_suffixes,
        include_fingerprint=True,
    )
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "repository_root": resolved_settings.nextcloud.root_path,
        "repository_backend": "nextcloud_webdav",
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


def compare_nextcloud_repository_state(
    previous_snapshot: dict[str, Any] | None,
    *,
    settings: EvidenceOpsExternalSettings | None = None,
    allowed_suffixes: set[str] | None = None,
) -> dict[str, Any]:
    current_snapshot = build_nextcloud_repository_snapshot(settings=settings, allowed_suffixes=allowed_suffixes)
    return {
        **diff_evidenceops_repository_snapshots(previous_snapshot, current_snapshot),
        "current_snapshot": current_snapshot,
    }


def build_trello_storyline_cards(
    *,
    settings: EvidenceOpsExternalSettings | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    resolved_settings = settings or get_evidenceops_external_settings()
    mapping = build_phase95_corpus_mapping(settings=resolved_settings)
    cards = []
    for storyline in mapping.trello_storylines:
        description_lines = [
            f"Goal: {storyline.get('goal')}",
            f"Primary documents: {', '.join(storyline.get('primary_documents') or [])}",
            f"Supporting documents: {', '.join(storyline.get('supporting_documents') or [])}",
            f"Expected action items: {', '.join(storyline.get('expected_action_items') or [])}",
            f"Expected review flags: {', '.join(storyline.get('expected_review_flags') or [])}",
            "Corpus: option_b_synthetic_premium",
        ]
        cards.append(
            {
                "storyline_id": storyline.get("storyline_id"),
                "name": storyline.get("card_title"),
                "description": "\n".join(line for line in description_lines if line and not line.endswith(": ")),
                "list_id": resolved_settings.trello.list_open_id or None,
            }
        )

    if dry_run:
        return {
            "dry_run": True,
            "official_demo_corpus": mapping.official_demo_corpus_name,
            "planned_cards": cards,
            "planned_card_count": len(cards),
        }

    trello = TrelloClient(resolved_settings.trello)
    created_cards = [
        trello.create_card(
            list_id=str(card.get("list_id") or resolved_settings.trello.list_open_id),
            name=str(card.get("name") or "EvidenceOps storyline"),
            description=str(card.get("description") or ""),
        )
        for card in cards
    ]
    return {
        "dry_run": False,
        "official_demo_corpus": mapping.official_demo_corpus_name,
        "created_cards": created_cards,
        "created_card_count": len(created_cards),
    }


def build_notion_storyline_register_entries(
    *,
    settings: EvidenceOpsExternalSettings | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    resolved_settings = settings or get_evidenceops_external_settings()
    mapping = build_phase95_corpus_mapping(settings=resolved_settings)
    entries = []
    for storyline in mapping.trello_storylines:
        entries.append(
            {
                "title": str(storyline.get("name") or "EvidenceOps Storyline"),
                "properties": {
                    "Storyline ID": {"rich_text": [{"type": "text", "text": {"content": str(storyline.get("storyline_id") or "")}}]},
                    "Corpus": {"select": {"name": mapping.official_demo_corpus_name}},
                    "Primary Documents": {"rich_text": [{"type": "text", "text": {"content": ", ".join(storyline.get("primary_documents") or [])}}]},
                    "Supporting Documents": {"rich_text": [{"type": "text", "text": {"content": ", ".join(storyline.get("supporting_documents") or [])}}]},
                },
            }
        )

    if dry_run:
        return {
            "dry_run": True,
            "official_demo_corpus": mapping.official_demo_corpus_name,
            "planned_pages": entries,
            "planned_page_count": len(entries),
        }

    notion = NotionClient(resolved_settings.notion)
    created_pages = [
        notion.create_page(title=str(entry.get("title") or "EvidenceOps Storyline"), properties=dict(entry.get("properties") or {}))
        for entry in entries
    ]
    return {
        "dry_run": False,
        "official_demo_corpus": mapping.official_demo_corpus_name,
        "created_pages": created_pages,
        "created_page_count": len(created_pages),
    }