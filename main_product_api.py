from __future__ import annotations

from src.config import get_product_api_settings
from src.product.api import build_product_api_server


def main() -> None:
    settings = get_product_api_settings()
    server = build_product_api_server(settings=settings)
    print(f"AI Workbench Product API listening on http://{settings.server_name}:{settings.server_port}")
    server.serve_forever()


if __name__ == "__main__":
    main()