import unittest
from unittest.mock import patch

from src.rag.pdf_extraction import _prepare_pdf_bytes_for_processing


class _FakePdfReader:
    def __init__(self, is_encrypted: bool):
        self.is_encrypted = is_encrypted


class PdfExtractionFallbackTests(unittest.TestCase):
    def test_prepare_pdf_bytes_returns_original_for_non_encrypted_pdf(self) -> None:
        with patch("src.rag.pdf_extraction.PdfReader", return_value=_FakePdfReader(False)):
            prepared, metadata = _prepare_pdf_bytes_for_processing(b"plain-pdf")

        self.assertEqual(prepared, b"plain-pdf")
        self.assertFalse(metadata["pdf_encrypted"])
        self.assertFalse(metadata["pdf_decryption_attempted"])
        self.assertIsNone(metadata["pdf_decryption_method"])

    def test_prepare_pdf_bytes_uses_qpdf_fallback_for_encrypted_pdf(self) -> None:
        with patch("src.rag.pdf_extraction.PdfReader", return_value=_FakePdfReader(True)):
            with patch("src.rag.pdf_extraction._decrypt_pdf_with_qpdf", return_value=(b"decrypted-pdf", None)):
                prepared, metadata = _prepare_pdf_bytes_for_processing(b"encrypted-pdf")

        self.assertEqual(prepared, b"decrypted-pdf")
        self.assertTrue(metadata["pdf_encrypted"])
        self.assertTrue(metadata["pdf_decryption_attempted"])
        self.assertEqual(metadata["pdf_decryption_method"], "qpdf_blank_user_password")
        self.assertIsNone(metadata["pdf_decryption_error"])


if __name__ == "__main__":
    unittest.main()