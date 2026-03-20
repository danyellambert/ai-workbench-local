from src.evidence_cv.reconcile import reconcile_pages
from src.evidence_cv.schemas import PageExtraction


def test_reconcile_extracts_email_and_phone_without_guessing():
    pages = [
        PageExtraction(page=1, ocr_text="Maria Silva\nmaria@teste.com\n+55 11 99999-9999"),
    ]
    result = reconcile_pages(pages, document_id="doc-1")
    assert len(result.resume.emails) == 1
    assert result.resume.emails[0].status == "confirmed"
    assert len(result.resume.phones) == 1


def test_reconcile_returns_warnings_when_evidence_missing():
    result = reconcile_pages([PageExtraction(page=1, ocr_text="sem contato")], document_id="doc-2")
    assert "No confirmed email found" in result.warnings