from __future__ import annotations

try:
    import gradio as gr  # noqa: F401
except Exception as error:  # pragma: no cover - CLI guard
    raise SystemExit(
        "Gradio is not installed in the current environment. Add `gradio` to the environment before running `main_gradio.py`."
    ) from error

from src.app.product_bootstrap import build_product_bootstrap
from src.gradio_ui.app import build_gradio_product_app


def main() -> None:
    bootstrap = build_product_bootstrap()
    app = build_gradio_product_app(bootstrap)
    app.launch(
        server_name=bootstrap.product_settings.server_name,
        server_port=bootstrap.product_settings.server_port,
    )


if __name__ == "__main__":
    main()