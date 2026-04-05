from __future__ import annotations

import json
from typing import Any, BinaryIO


MCP_PROTOCOL_VERSION = "2024-11-05"

JSONRPC_PARSE_ERROR = -32700
JSONRPC_INVALID_REQUEST = -32600
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_PARAMS = -32602
JSONRPC_INTERNAL_ERROR = -32603


def _ensure_binary_stream(stream: Any) -> BinaryIO:
    return stream.buffer if hasattr(stream, "buffer") else stream


def sanitize_json_like(value: object) -> object:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [sanitize_json_like(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): sanitize_json_like(item)
            for key, item in value.items()
        }
    return str(value)


def read_message(stream: Any) -> dict[str, Any] | None:
    binary_stream = _ensure_binary_stream(stream)
    headers: dict[str, str] = {}

    while True:
        line = binary_stream.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        decoded_line = line.decode("utf-8").strip()
        if not decoded_line:
            break
        name, _, value = decoded_line.partition(":")
        headers[name.lower().strip()] = value.strip()

    content_length = int(headers.get("content-length", "0") or 0)
    if content_length <= 0:
        return None
    payload = binary_stream.read(content_length)
    if not payload:
        return None
    return json.loads(payload.decode("utf-8"))


def write_message(stream: Any, payload: dict[str, Any]) -> None:
    binary_stream = _ensure_binary_stream(stream)
    body = json.dumps(sanitize_json_like(payload), ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\nContent-Type: application/json\r\n\r\n".encode("ascii")
    binary_stream.write(header)
    binary_stream.write(body)
    binary_stream.flush()


def build_success_response(message_id: object, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "result": sanitize_json_like(result),
    }


def build_error_response(
    message_id: object,
    *,
    code: int,
    message: str,
    data: object | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "code": int(code),
        "message": str(message),
    }
    if data is not None:
        error["data"] = sanitize_json_like(data)
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": error,
    }