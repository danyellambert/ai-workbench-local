from __future__ import annotations

import os
from dataclasses import is_dataclass, replace

from src.config import get_product_api_settings
from src.product.api import build_product_api_server


def _product_api_bind_config() -> tuple[str, int]:
    host = (
        os.environ.get("AI_DECISION_STUDIO_PRODUCT_API_HOST")
        or os.environ.get("PRODUCT_API_HOST")
        or "127.0.0.1"
    )
    port_raw = (
        os.environ.get("AI_DECISION_STUDIO_PRODUCT_API_PORT")
        or os.environ.get("PRODUCT_API_PORT")
        or "8011"
    )

    try:
        port = int(port_raw)
    except ValueError:
        port = 8011

    return host, port


def _settings_with_product_api_bind(settings, host: str, port: int):
    if is_dataclass(settings):
        return replace(settings, server_name=host, server_port=port)

    if hasattr(settings, "model_copy"):
        return settings.model_copy(update={"server_name": host, "server_port": port})

    try:
        settings.server_name = host
        settings.server_port = port
        return settings
    except Exception:
        values = dict(getattr(settings, "__dict__", {}))
        values["server_name"] = host
        values["server_port"] = port
        return settings.__class__(**values)


def main() -> None:
    settings = get_product_api_settings()
    bind_host, bind_port = _product_api_bind_config()
    settings = _settings_with_product_api_bind(settings, bind_host, bind_port)

    server = build_product_api_server(settings=settings)
    print(f"Axiovance Product API listening on http://{settings.server_name}:{settings.server_port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
