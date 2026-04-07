from src.evidence_cv.reconcile import reconcile_pages
from src.evidence_cv.schemas import PageExtraction


def test_reconcile_extracts_email_and_phone_without_guessing():
    pages = [
        PageExtraction(page=1, ocr_text="Maria Silva\nmaria@test.com\n+55 11 99999-9999"),
    ]
    result = reconcile_pages(pages, document_id="doc-1")
    assert len(result.resume.emails) == 1
    assert result.resume.emails[0].status == "confirmed"
    assert len(result.resume.phones) == 1


def test_reconcile_returns_warnings_when_evidence_missing():
    result = reconcile_pages([PageExtraction(page=1, ocr_text="no contact")], document_id="doc-2")
    assert "No confirmed email found" in result.warnings


def test_reconcile_recovers_name_and_location_around_contact_header_window():
    pages = [
        PageExtraction(
            page=1,
            ocr_text=(
                "Noise line\n"
                "/in/lucas-de-souza-ferreira/\n"
                "lucas.souza-ferreira@student-cs.fr\n"
                "Lucas de Souza Ferreira\n"
                "Rua Sao Bras, 370. Rio de Janeiro, Brazil\n"
            ),
        ),
    ]
    result = reconcile_pages(pages, document_id="doc-3")
    assert result.resume.name.value == "Lucas de Souza Ferreira"
    assert result.resume.name.status == "confirmed"
    assert result.resume.location.value == "Rua Sao Bras, 370. Rio de Janeiro, Brazil"
    assert result.resume.location.status == "confirmed"


def test_reconcile_accepts_lowercase_name_particles():
    pages = [
        PageExtraction(
            page=1,
            ocr_text="lucas.souza-ferreira@student-cs.fr\nLucas de Souza Ferreira\nRua Sao Bras, 370. Rio de Janeiro, Brazil\n",
        ),
    ]
    result = reconcile_pages(pages, document_id="doc-5")
    assert result.resume.name.value == "Lucas de Souza Ferreira"


def test_reconcile_rejects_education_line_as_location_candidate():
    pages = [
        PageExtraction(
            page=1,
            ocr_text=(
                "Nathaly Ortiz\n"
                "(562) 449-0312 • nathalyortiz15@gmail.com\n"
                "EDUCATION\n"
                "B.A., Scripps College, Expected 2024 Claremont, CA\n"
                "WORK EXPERIENCE\n"
                "Hamlin, Hamlin & McGill Albuquerque, NM\n"
            ),
        ),
    ]
    result = reconcile_pages(pages, document_id="doc-6")
    assert result.resume.name.value == "Nathaly Ortiz"
    assert result.resume.location.value is None


def test_reconcile_recovers_location_from_address_line_with_contact_suffixes():
    pages = [
        PageExtraction(
            page=1,
            ocr_text=(
                "Darrell Wiremu Rogers\n"
                "43 Kiwi Lane, Auckland, NZ • dwr5@apple.com • +64 22 427 8081\n"
            ),
        ),
    ]
    result = reconcile_pages(pages, document_id="doc-4")
    assert result.resume.name.value == "Darrell Wiremu Rogers"
    assert result.resume.location.value == "43 Kiwi Lane, Auckland, NZ"