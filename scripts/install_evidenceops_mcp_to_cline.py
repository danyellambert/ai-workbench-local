#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.evidenceops_mcp_client import (  # noqa: E402
    DEFAULT_CLINE_MCP_SETTINGS_PATH,
    DEFAULT_EVIDENCEOPS_MCP_SERVER_KEY,
    install_evidenceops_mcp_server_in_cline_settings,
)


def main() -> None:
    payload = install_evidenceops_mcp_server_in_cline_settings()
    server_entry = payload.get("mcpServers", {}).get(DEFAULT_EVIDENCEOPS_MCP_SERVER_KEY, {})
    print(f"Installed MCP server '{DEFAULT_EVIDENCEOPS_MCP_SERVER_KEY}' into {DEFAULT_CLINE_MCP_SETTINGS_PATH}")
    print(json.dumps(server_entry, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()