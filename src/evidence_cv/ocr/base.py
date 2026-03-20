from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..schemas import PageExtraction


class OCRBackend(Protocol):
    def extract(self, pdf_path: Path) -> list[PageExtraction]: ...