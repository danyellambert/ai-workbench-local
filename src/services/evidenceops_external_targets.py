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


def _resolve_trello_target_list_id(
    *,
    result: ProductWorkflowResult,
    settings: EvidenceOpsExternalSettings,
) -> str:
    if _result_requires_review(result) and str(settings.trello.list_review_id or "").strip():
        return str(settings.trello.list_review_id)
    fallback_candidates = [
        settings.trello.list_open_id,
        settings.trello.list_review_id,
        settings.trello.list_approved_id,
        settings.trello.list_done_id,
    ]
    for candidate in fallback_candidates:
        if str(candidate or "").strip():
            return str(candidate)
    raise ValueError("No Trello target list is configured for card creation.")


def _candidate_card_name(result: ProductWorkflowResult, payload: CVAnalysisPayload) -> str:
    personal_info = payload.personal_info
    full_name = _trim_text(getattr(personal_info, "full_name", "") if personal_info is not None else "", max_chars=64)
    if full_name:
        return _trim_text(f"[{result.workflow_label}] {full_name}", max_chars=120)
    return _trim_text(f"[{result.workflow_label}] {result.recommendation or result.summary or result.workflow_id}", max_chars=120)


def _build_product_result_card_description(
    *,
    result: ProductWorkflowResult,
    document_ids: list[str],
    action_item: dict[str, Any] | None = None,
) -> str:
    description_lines = [
        f"Workflow: {result.workflow_label}",
        f"Workflow ID: {result.workflow_id}",
        f"Run status: {result.status}",
        f"Summary: {_trim_text(result.summary, max_chars=900)}",
    ]
    if result.recommendation:
        description_lines.append(f"Recommendation: {_trim_text(result.recommendation, max_chars=400)}")
    if isinstance(action_item, dict):
        if str(action_item.get("owner") or "").strip():
            description_lines.append(f"Owner: {_trim_text(action_item.get('owner'), max_chars=120)}")
        if str(action_item.get("due_date") or "").strip():
            description_lines.append(f"Due date: {_trim_text(action_item.get('due_date'), max_chars=120)}")
        if str(action_item.get("status") or "").strip():
            description_lines.append(f"Action status: {_trim_text(action_item.get('status'), max_chars=120)}")
        if str(action_item.get("evidence") or "").strip():
            description_lines.append(f"Evidence: {_trim_text(action_item.get('evidence'), max_chars=600)}")
    if result.highlights:
        description_lines.append(
            "Highlights: " + "; ".join(_trim_text(item, max_chars=120) for item in result.highlights[:5] if str(item).strip())
        )
    if result.warnings:
        description_lines.append(
            "Warnings: " + "; ".join(_trim_text(item, max_chars=120) for item in result.warnings[:4] if str(item).strip())
        )
    if document_ids:
        description_lines.append("Documents: " + ", ".join(document_ids[:8]))
    description_lines.append("Source surface: Gradio UI")
    return "\n".join(line for line in description_lines if str(line).strip())


def _build_product_result_trello_cards(
    *,
    result: ProductWorkflowResult,
    settings: EvidenceOpsExternalSettings,
    max_cards: int = 8,
) -> tuple[list[dict[str, Any]], str]:
    target_list_id = _resolve_trello_target_list_id(result=result, settings=settings)
    document_ids = _result_document_ids(result)
    payload = result.structured_result.validated_output if result.structured_result is not None else None
    cards: list[dict[str, Any]] = []

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
        card_name = _trim_text(
            f"[{result.workflow_label}] {result.recommendation or result.summary or result.workflow_id}",
            max_chars=120,
        )
    cards.append(
        {
            "name": card_name,
            "description": _build_product_result_card_description(result=result, document_ids=document_ids),
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
    )
    plan = {
        "status": "planned" if dry_run else "success",
        "dry_run": bool(dry_run),
        "workflow_id": result.workflow_id,
        "workflow_label": result.workflow_label,
        "card_mode": card_mode,
        "target_board_id": resolved_settings.trello.board_id or None,
        "planned_card_count": len(cards),
        "planned_cards": cards,
    }
    if dry_run:
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


def _product_result_notion_title(result: ProductWorkflowResult) -> str:
    payload = result.structured_result.validated_output if result.structured_result is not None else None
    if isinstance(payload, CVAnalysisPayload) and payload.personal_info is not None:
        full_name = _trim_text(getattr(payload.personal_info, "full_name", ""), max_chars=64)
        if full_name:
            return _trim_text(f"[{result.workflow_label}] {full_name}", max_chars=120)
    return _trim_text(
        f"[{result.workflow_label}] {result.recommendation or result.summary or result.workflow_id}",
        max_chars=120,
    )


def create_notion_page_from_product_result(
    result: ProductWorkflowResult,
    *,
    settings: EvidenceOpsExternalSettings | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    if not isinstance(result, ProductWorkflowResult):
        raise ValueError("A valid ProductWorkflowResult is required to create a Notion page.")

    resolved_settings = settings or get_evidenceops_external_settings()
    _require_notion_settings(resolved_settings)

    document_ids = _result_document_ids(result)
    children = [
        _build_notion_paragraph_block(f"Workflow: {result.workflow_label}"),
        _build_notion_paragraph_block(f"Workflow ID: {result.workflow_id}"),
        _build_notion_paragraph_block(f"Run status: {result.status}"),
        _build_notion_paragraph_block(f"Summary: {result.summary}"),
    ]
    if result.recommendation:
        children.append(_build_notion_paragraph_block(f"Recommendation: {result.recommendation}"))
    if result.highlights:
        children.append(_build_notion_paragraph_block("Highlights: " + "; ".join(_trim_text(item, max_chars=120) for item in result.highlights[:5])))
    if result.warnings:
        children.append(_build_notion_paragraph_block("Warnings: " + "; ".join(_trim_text(item, max_chars=120) for item in result.warnings[:5])))
    if document_ids:
        children.append(_build_notion_paragraph_block("Documents: " + ", ".join(document_ids[:8])))
    children.append(_build_notion_paragraph_block("Source surface: Gradio UI"))
    children = [item for item in children if item is not None]

    title = _product_result_notion_title(result)
    plan = {
        "status": "planned" if dry_run else "success",
        "dry_run": bool(dry_run),
        "workflow_id": result.workflow_id,
        "workflow_label": result.workflow_label,
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