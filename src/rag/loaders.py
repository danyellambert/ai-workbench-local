import csv
import hashlib
import io
from dataclasses import dataclass


@dataclass(frozen=True)
class LoadedDocument:
    name: str
    file_type: str
    file_hash: str
    text: str


def _extract_pdf_text(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError("Instale `pypdf` para carregar arquivos PDF.") from error

    reader = PdfReader(io.BytesIO(file_bytes))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    return "\n\n".join(page for page in pages if page)


def _extract_csv_text(file_bytes: bytes) -> str:
    text = file_bytes.decode("utf-8", errors="ignore")
    rows = list(csv.reader(io.StringIO(text)))
    return "\n".join(" | ".join(cell.strip() for cell in row) for row in rows if row)


def _extract_txt_text(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="ignore")


def load_document(uploaded_file) -> LoadedDocument:
    file_bytes = uploaded_file.getvalue()
    suffix = uploaded_file.name.lower().rsplit(".", 1)[-1] if "." in uploaded_file.name else ""

    if suffix == "pdf":
        text = _extract_pdf_text(file_bytes)
        file_type = "pdf"
    elif suffix == "csv":
        text = _extract_csv_text(file_bytes)
        file_type = "csv"
    elif suffix in {"txt", "md", "py"}:
        text = _extract_txt_text(file_bytes)
        file_type = suffix
    else:
        raise RuntimeError("Formato não suportado. Use PDF, TXT, CSV, MD ou PY.")

    cleaned_text = text.strip()
    if not cleaned_text:
        raise RuntimeError("Não foi possível extrair conteúdo útil do arquivo enviado.")

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    return LoadedDocument(
        name=uploaded_file.name,
        file_type=file_type,
        file_hash=file_hash,
        text=cleaned_text,
    )