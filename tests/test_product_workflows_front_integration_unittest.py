import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from src.config import PresentationExportSettings, get_rag_settings
from src.gradio_ui.components import build_result_panels_html, build_result_summary_html
from src.product.models import ProductWorkflowRequest
from src.product.presenters import build_product_result_sections
from src.product.service import generate_product_workflow_deck, index_loaded_documents, run_product_workflow
from src.rag.loaders import load_document
from src.rag.service import normalize_rag_index
from src.storage.rag_store import load_rag_store


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_REVIEW_PATH = PROJECT_ROOT / "data" / "materials_demo" / "summary" / "asap-2025-annual-report-tagged.pdf"
POLICY_DOC_A_PATH = PROJECT_ROOT / "data" / "materials_demo" / "extraction" / "exhib101.pdf"
POLICY_DOC_B_PATH = PROJECT_ROOT / "data" / "materials_demo" / "extraction" / "exhibit10-3.pdf"
ACTION_PLAN_PATH = PROJECT_ROOT / "data" / "materials_demo" / "extraction" / "exhib101.pdf"


class _UploadAdapter:
    def __init__(self, path: Path) -> None:
        self.name = path.name
        self._content = path.read_bytes()

    def getvalue(self) -> bytes:
        return self._content


class _FakeHttpResponse:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class _RuleBasedWorkflowProvider:
    def list_available_models(self):
        return ["workflow-front-fake"]

    def create_embeddings(self, texts, model=None, context_window=None, truncate=None):
        embeddings = []
        for text in texts:
            bucket = [0.0] * 8
            for index, value in enumerate((text or "").encode("utf-8", errors="ignore")):
                bucket[index % 8] += float(value)
            total = sum(abs(item) for item in bucket) or 1.0
            embeddings.append([round(item / total, 6) for item in bucket])
        return embeddings

    def stream_chat_completion(self, messages, model, temperature, context_window=None, top_p=None, max_tokens=None, think=None):
        prompt = "\n".join(str(message.get("content") or "") for message in messages)
        return [self._response_for_prompt(prompt)]

    @staticmethod
    def iter_stream_text(stream):
        for item in stream:
            yield item

    def _response_for_prompt(self, prompt: str) -> str:
        if '"task_type": "summary"' in prompt and (
            "SEPARATION AGREEMENT" in prompt
            or "Preservation of Records; Cooperation" in prompt
            or "Tax Indemnification" in prompt
            or "Corporate separation covenants" in prompt
        ):
            return json.dumps(
                {
                    "task_type": "summary",
                    "topics": [
                        {
                            "title": "Corporate separation covenants",
                            "key_points": [
                                "The agreement requires preservation of records, cooperation and confidentiality obligations between Enron and PGE.",
                                "Use-of-name and further-assurance clauses frame post-separation operating discipline.",
                            ],
                            "relevance_score": 0.94,
                            "supporting_evidence": ["Preservation of Records; Cooperation", "Confidentiality", "Use of Name"],
                        },
                        {
                            "title": "Indemnification and legal protections",
                            "key_points": [
                                "Tax and employee-benefits indemnification obligations are explicit.",
                                "The agreement includes submission to jurisdiction, waiver of jury trial and governing law clauses.",
                            ],
                            "relevance_score": 0.91,
                            "supporting_evidence": ["Tax Indemnification", "Waiver of Jury Trial", "Governing Law"],
                        },
                    ],
                    "executive_summary": "The separation agreement allocates post-spin obligations across records retention, confidentiality, stock issuance, indemnification and dispute-governance terms between Enron and PGE.",
                    "key_insights": [
                        "The agreement is covenant-heavy and allocates operational duties that need coordinated execution by both parties.",
                        "Indemnification and dispute-resolution clauses create material legal exposure if obligations are missed.",
                    ],
                    "reading_time_minutes": 2,
                    "completeness_score": 0.9,
                },
                ensure_ascii=False,
            )

        if '"task_type": "summary"' in prompt and (
            "DLJ MORTGAGE CAPITAL" in prompt
            or "Servicing of Mortgage Loans" in prompt
            or "Custodial Accounts" in prompt
            or "Mortgage loan servicing operations" in prompt
            or "Repurchase and servicer obligations" in prompt
        ):
            return json.dumps(
                {
                    "task_type": "summary",
                    "topics": [
                        {
                            "title": "Mortgage loan servicing operations",
                            "key_points": [
                                "The agreement governs purchase, servicing, mortgage files, books and records, and transfer of mortgage loans.",
                                "Custodial accounts, escrow accounts and servicing-period procedures are operationally central.",
                            ],
                            "relevance_score": 0.95,
                            "supporting_evidence": ["Servicing of Mortgage Loans", "Custodial Accounts", "Escrow Accounts"],
                        },
                        {
                            "title": "Repurchase and servicer obligations",
                            "key_points": [
                                "Representations, warranties and repurchase mechanics create quality and compliance exposure.",
                                "The servicer must support reporting, compliance and record examination by the purchaser.",
                            ],
                            "relevance_score": 0.9,
                            "supporting_evidence": ["Repurchase; Substitution", "Annual Statement as to Compliance", "Purchaser’s Right to Examine Servicer Records"],
                        },
                    ],
                    "executive_summary": "The mortgage purchase and interim servicing agreement is operationally focused on loan servicing, custody, account management, compliance reporting and repurchase protections between DLJ Mortgage Capital and E-Loan.",
                    "key_insights": [
                        "The document is process- and servicing-heavy, with explicit obligations on records, custody, compliance and repurchase exposure.",
                        "Operational breakdowns in servicing controls would likely create direct contractual risk.",
                    ],
                    "reading_time_minutes": 2,
                    "completeness_score": 0.9,
                },
                ensure_ascii=False,
            )

        if '"task_type": "extraction"' in prompt and "Aerospace Safety Advisory Panel" in prompt:
            return json.dumps(
                {
                    "task_type": "extraction",
                    "main_subject": "ASAP Annual Report 2025 on NASA safety, organizational and programmatic risks.",
                    "entities": [
                        {"type": "organization", "value": "NASA", "confidence": 0.98, "source_text": "National Aeronautics and Space Administration", "position_start": 0, "position_end": 0},
                        {"type": "organization", "value": "Aerospace Safety Advisory Panel", "confidence": 0.97, "source_text": "Aerospace Safety Advisory Panel", "position_start": 0, "position_end": 0},
                        {"type": "program", "value": "Artemis III", "confidence": 0.95, "source_text": "Artemis III", "position_start": 0, "position_end": 0},
                        {"type": "program", "value": "International Space Station", "confidence": 0.94, "source_text": "ISS", "position_start": 0, "position_end": 0},
                    ],
                    "categories": ["Annual Report", "Safety Oversight Report"],
                    "relationships": [
                        {"from_entity": "Aerospace Safety Advisory Panel", "to_entity": "NASA", "relationship": "advises", "confidence": 0.9, "evidence": "The ASAP Annual Report for 2025 to the U.S. Congress and to the Administrator of NASA."}
                    ],
                    "extracted_fields": [
                        {"name": "report_date", "value": "February 15, 2026", "evidence": "February 15, 2026"},
                        {"name": "iss_deorbit_target", "value": "2030", "evidence": "its safe deorbit in 2030"},
                    ],
                    "important_dates": ["February 15, 2026", "2030"],
                    "important_numbers": ["2025", "2030"],
                    "risks": [
                        {"description": "Artemis III and subsequent mission risk posture remains a major safety concern.", "evidence": "has repeatedly raised concern regarding Artemis III and subsequent Artemis mission risk postures", "impact": "Human spaceflight risk may increase if readiness pressure overrides safety discipline.", "owner": "NASA leadership", "due_date": None},
                        {"description": "The ISS is entering the riskiest period of its operational life.", "evidence": "The Panel continues to characterize the International Space Station (ISS) as now entering the riskiest period of its operational life", "impact": "Transition and deorbit decisions carry elevated operational and safety risk.", "owner": "NASA ISS leadership", "due_date": "2030"},
                        {"description": "Workforce attrition and organizational pressure may erode independent technical authority.", "evidence": "workforce attrition, proposed budget reductions, and organizational pressures could erode their effectiveness", "impact": "Reduced technical authority could weaken safety oversight and acquisition decisions.", "owner": "NASA technical authority leadership", "due_date": None},
                    ],
                    "action_items": [
                        {"description": "Reassess Artemis III readiness and mission risk posture before proceeding to later mission commitments.", "evidence": "raised concern regarding Artemis III and subsequent Artemis mission risk postures", "owner": "NASA leadership", "due_date": "before Artemis III readiness decisions", "status": "recommended"},
                        {"description": "Strengthen acquisition, procurement and contracting discipline as a safety determinant.", "evidence": "acquisition strategy as an emerging determinant of safety outcomes", "owner": "NASA acquisition leadership", "due_date": None, "status": "recommended"},
                        {"description": "Protect independent technical authorities against attrition, budget pressure and organizational stress.", "evidence": "The Panel reaffirmed the necessity of independent technical authorities", "owner": "NASA technical authority leadership", "due_date": None, "status": "recommended"},
                        {"description": "Advance ISS transition and deorbit planning early enough to manage the 2030 transition safely.", "evidence": "decisions that must be made well in advance of deorbit execution", "owner": "NASA ISS program leadership", "due_date": "2030", "status": "recommended"},
                    ],
                    "missing_information": ["The report excerpt does not provide a detailed mitigation roadmap with owners and milestones for each risk area."],
                },
                ensure_ascii=False,
            )

        if '"task_type": "extraction"' in prompt and "SEPARATION AGREEMENT" in prompt:
            return json.dumps(
                {
                    "task_type": "extraction",
                    "main_subject": "Separation Agreement between Enron Corp. and Portland General Electric Company.",
                    "entities": [
                        {"type": "organization", "value": "Enron Corp.", "confidence": 0.98, "source_text": "ENRON CORP.", "position_start": 0, "position_end": 0},
                        {"type": "organization", "value": "Portland General Electric Company", "confidence": 0.98, "source_text": "PORTLAND GENERAL ELECTRIC COMPANY", "position_start": 0, "position_end": 0},
                        {"type": "organization", "value": "Bankruptcy Court", "confidence": 0.85, "source_text": "Submission to Jurisdiction; Consent to Service of Process", "position_start": 0, "position_end": 0},
                    ],
                    "categories": ["Separation Agreement", "Contract"],
                    "relationships": [
                        {"from_entity": "Enron Corp.", "to_entity": "Portland General Electric Company", "relationship": "agreement_between", "confidence": 0.93, "evidence": "SEPARATION AGREEMENT, dated as of April 3, 2006"}
                    ],
                    "extracted_fields": [
                        {"name": "effective_date", "value": "April 3, 2006", "evidence": "Dated as of April 3, 2006"},
                        {"name": "counterparties", "value": "Enron Corp.; Portland General Electric Company", "evidence": "between Enron Corp. ... and Portland General Electric Company"},
                        {"name": "covered_clauses", "value": "Preservation of Records; Cooperation; Confidentiality; Use of Name; Tax Indemnification; Employee Benefits Indemnification; Submission to Jurisdiction; Waiver of Jury Trial; Governing Law", "evidence": "TABLE OF CONTENTS"},
                    ],
                    "important_dates": ["April 3, 2006"],
                    "important_numbers": [],
                    "risks": [
                        {"description": "Confidentiality and name-use breaches may create contractual and reputational exposure.", "evidence": "Confidentiality" , "impact": "Breach could trigger dispute and reputational damage.", "owner": None, "due_date": None},
                        {"description": "Indemnification clauses may shift tax and employee-benefit liabilities between the parties.", "evidence": "Tax Indemnification; Employee Benefits Indemnification", "impact": "Potential financial liability transfer if obligations are not managed correctly.", "owner": None, "due_date": None},
                        {"description": "Jurisdiction and waiver clauses constrain litigation options and dispute handling.", "evidence": "Submission to Jurisdiction; Waiver of Jury Trial; Governing Law", "impact": "Disputes must follow the agreement’s chosen forum and legal framework.", "owner": None, "due_date": None},
                    ],
                    "action_items": [
                        {"description": "Preserve records and cooperate on claims, actions, investigations and proceedings related to the business.", "evidence": "Preservation of Records; Cooperation", "owner": "Enron Corp. and Portland General Electric Company", "due_date": "on and after the date hereof", "status": "required"},
                        {"description": "Maintain confidentiality obligations over shared information after the separation.", "evidence": "Confidentiality", "owner": "Enron Corp. and Portland General Electric Company", "due_date": None, "status": "required"},
                        {"description": "Complete concurrent deliveries, transactions and stock issuance tied to execution of the agreement.", "evidence": "concurrently with the execution and delivery of this Agreement", "owner": "Enron Group and PGE", "due_date": "concurrently with the execution and delivery of this Agreement", "status": "required"},
                    ],
                    "missing_information": ["The excerpt does not provide a detailed operational checklist with internal owners below the party level."],
                },
                ensure_ascii=False,
            )

        if '"task_type": "extraction"' in prompt and "DLJ MORTGAGE CAPITAL" in prompt:
            return json.dumps(
                {
                    "task_type": "extraction",
                    "main_subject": "Seller’s Purchase, Warranties and Interim Servicing Agreement between DLJ Mortgage Capital, Inc. and E-LOAN, Inc.",
                    "entities": [
                        {"type": "organization", "value": "DLJ Mortgage Capital, Inc.", "confidence": 0.98, "source_text": "DLJ MORTGAGE CAPITAL, INC.", "position_start": 0, "position_end": 0},
                        {"type": "organization", "value": "E-LOAN, INC.", "confidence": 0.98, "source_text": "E-LOAN, INC.", "position_start": 0, "position_end": 0},
                    ],
                    "categories": ["Agreement", "Mortgage Servicing Agreement"],
                    "relationships": [
                        {"from_entity": "DLJ Mortgage Capital, Inc.", "to_entity": "E-LOAN, INC.", "relationship": "agreement_between", "confidence": 0.93, "evidence": "Purchaser / Seller and Servicer"}
                    ],
                    "extracted_fields": [
                        {"name": "effective_date", "value": "April 1, 2003", "evidence": "Dated as of April 1, 2003"},
                        {"name": "counterparties", "value": "DLJ Mortgage Capital, Inc.; E-LOAN, INC.", "evidence": "Purchaser, Seller and Servicer"},
                    ],
                    "important_dates": ["April 1, 2003"],
                    "important_numbers": [],
                    "risks": [
                        {"description": "Servicing-control failures may create repurchase and compliance exposure.", "evidence": "Repurchase; Review of Mortgage Loans", "impact": "Poor servicing quality can trigger contractual remedies and repurchase obligations.", "owner": "Servicer", "due_date": None},
                        {"description": "Weak custody, escrow or insurance maintenance controls could create operational loss exposure.", "evidence": "Custodial Accounts; Escrow Accounts; Maintenance of Hazard Insurance", "impact": "Operational and financial controls may fail if account obligations are not followed.", "owner": "Servicer", "due_date": None},
                    ],
                    "action_items": [
                        {"description": "Maintain mortgage files, books and records in accordance with the servicing agreement.", "evidence": "Record Title and Possession of Mortgage Files; Books and Records", "owner": "Servicer", "due_date": None, "status": "required"},
                        {"description": "Operate custodial and escrow accounts and process permitted withdrawals according to the agreement.", "evidence": "Establishment of Custodial Accounts; Permitted Withdrawals", "owner": "Servicer", "due_date": None, "status": "required"},
                        {"description": "Support compliance reporting and provide records for purchaser examination as reasonably required.", "evidence": "Annual Statement as to Compliance; Purchaser’s Right to Examine Servicer Records", "owner": "Servicer", "due_date": "annual", "status": "required"},
                    ],
                    "missing_information": ["The excerpt does not show internal operational owners below the servicer/purchaser role level."],
                },
                ensure_ascii=False,
            )

        if "Compare os documentos" in prompt or "Resumos dos documentos:" in prompt:
            return (
                "Both agreements require grounded legal review, but they serve very different operating models. "
                "The Enron/PGE separation agreement is focused on corporate separation covenants, indemnification and dispute governance, "
                "while the DLJ/E-LOAN agreement is focused on mortgage servicing operations, custody, compliance and repurchase protections.\n"
                "- The separation agreement concentrates on confidentiality, records cooperation, stock issuance and legal protections.\n"
                "- The mortgage servicing agreement concentrates on servicing controls, custodial accounts, escrow operations and repurchase mechanics.\n"
                "- Business impact differs: the first is corporate/legal separation risk, the second is servicing and operational compliance risk.\n"
                "- Both documents still require final human validation before contractual decisions or operational execution."
            )

        return (
            "Grounded response unavailable for the current prompt. "
            "Please refine the document set or run a manual review."
        )


class ProductWorkflowsFrontIntegrationTests(unittest.TestCase):
    def _provider_registry(self):
        provider = _RuleBasedWorkflowProvider()
        return {
            "ollama": {
                "label": "Ollama (fake)",
                "instance": provider,
                "supports_chat": True,
                "supports_embeddings": True,
                "default_model": "workflow-front-fake",
                "default_context_window": 8192,
            }
        }

    def _rag_settings(self, temp_dir: str):
        base = get_rag_settings()
        return replace(
            base,
            store_path=Path(temp_dir) / ".rag_store.json",
            chroma_path=Path(temp_dir) / ".chroma_rag",
            loader_strategy="manual",
            chunking_strategy="manual",
            retrieval_strategy="manual_hybrid",
            embedding_provider="ollama",
            embedding_model="workflow-front-fake-embed",
            pdf_extraction_mode="basic",
            pdf_docling_enabled=False,
            pdf_docling_ocr_enabled=False,
            pdf_ocr_fallback_enabled=False,
            pdf_scan_image_ocr_enabled=False,
            pdf_evidence_pipeline_enabled=False,
        )

    def _service_settings(self, temp_dir: str) -> PresentationExportSettings:
        return PresentationExportSettings(
            enabled=True,
            base_url="http://deck.local",
            timeout_seconds=15,
            remote_output_dir="outputs/ai_workbench_exports",
            remote_preview_dir="outputs/ai_workbench_export_previews",
            local_artifact_dir=Path(temp_dir) / "artifacts",
            include_review=True,
            preview_backend="auto",
            require_real_previews=False,
            fail_on_regression=False,
        )

    def _fake_urlopen(self, request, timeout=0):
        url = request.full_url if hasattr(request, "full_url") else str(request)
        parsed = urlparse(url)
        if parsed.path == "/health":
            return _FakeHttpResponse(json.dumps({"status": "ok"}).encode("utf-8"))
        if parsed.path == "/render":
            body = {
                "result": {
                    "output_path": "outputs/ai_workbench_exports/export/deck.pptx",
                    "quality_review": {"score": 0.92},
                    "preview_result": {
                        "preview_manifest": "outputs/ai_workbench_export_previews/export/preview-manifest.json",
                        "thumbnail_sheet": "outputs/ai_workbench_export_previews/export/thumbnails.png",
                    },
                }
            }
            return _FakeHttpResponse(json.dumps(body).encode("utf-8"))
        if parsed.path == "/artifact":
            remote_path = parse_qs(parsed.query).get("path", [""])[0]
            if remote_path.endswith("deck.pptx"):
                return _FakeHttpResponse(b"pptx-binary")
            if remote_path.endswith("preview-manifest.json"):
                return _FakeHttpResponse(b'{"preview_count": 1}')
            if remote_path.endswith("thumbnails.png"):
                return _FakeHttpResponse(b"png-binary")
        raise AssertionError(f"Unexpected request URL: {url}")

    def _run_front_flow(self, *, workflow_id: str, file_paths: list[Path], input_text: str = ""):
        with tempfile.TemporaryDirectory() as temp_dir:
            rag_settings = self._rag_settings(temp_dir)
            provider_registry = self._provider_registry()
            loaded_documents = [load_document(_UploadAdapter(path), rag_settings) for path in file_paths]
            indexed_documents, index_status = index_loaded_documents(
                loaded_documents,
                rag_settings=rag_settings,
                provider_registry=provider_registry,
            )
            rag_index = normalize_rag_index(load_rag_store(rag_settings.store_path), rag_settings)
            self.assertIsNotNone(rag_index)
            request = ProductWorkflowRequest(
                workflow_id=workflow_id,
                document_ids=[document.document_id for document in indexed_documents[: len(file_paths)]],
                input_text=input_text,
                provider="ollama",
                model="workflow-front-fake",
            )

            with (
                patch("src.providers.registry.build_provider_registry", return_value=provider_registry),
                patch("src.services.document_context._get_rag_index", return_value=rag_index),
                patch("src.services.document_context._get_effective_rag_settings", return_value=rag_settings),
                patch("src.services.document_context._get_embedding_provider", return_value=provider_registry["ollama"]["instance"]),
            ):
                result = run_product_workflow(request)
                sections = build_product_result_sections(result)
                summary_html = build_result_summary_html(result)
                panels_html = build_result_panels_html(result)
                with patch("src.services.presentation_export_service.urllib_request.urlopen", side_effect=self._fake_urlopen):
                    export_result, artifacts = generate_product_workflow_deck(
                        result,
                        settings=self._service_settings(temp_dir),
                        workspace_root=Path(temp_dir),
                    )

            return {
                "index_status": index_status,
                "result": result,
                "sections": sections,
                "summary_html": summary_html,
                "panels_html": panels_html,
                "export_result": export_result,
                "artifacts": artifacts,
            }

    def test_document_review_front_flow_produces_grounded_risk_review(self) -> None:
        run = self._run_front_flow(workflow_id="document_review", file_paths=[DOCUMENT_REVIEW_PATH])

        payload = run["result"].structured_result.validated_output

        self.assertEqual(run["index_status"]["ok"], True)
        self.assertEqual(run["result"].status, "warning")
        self.assertEqual(payload.tool_used, "review_document_risks")
        self.assertIn("Artemis III", run["result"].summary)
        self.assertTrue(run["sections"]["next_steps"])
        self.assertTrue(any(table.get("title") == "Risk review" for table in run["sections"]["tables"]))
        self.assertIn("Watchouts", run["panels_html"])
        self.assertEqual(run["export_result"]["status"], "completed")
        self.assertTrue(any(artifact.artifact_type == "pptx" for artifact in run["artifacts"]))

    def test_policy_comparison_front_flow_compares_two_real_documents(self) -> None:
        run = self._run_front_flow(
            workflow_id="policy_contract_comparison",
            file_paths=[POLICY_DOC_A_PATH, POLICY_DOC_B_PATH],
        )

        payload = run["result"].structured_result.validated_output

        self.assertEqual(run["index_status"]["ok"], True)
        self.assertEqual(run["result"].status, "completed")
        self.assertEqual(payload.tool_used, "compare_documents")
        self.assertEqual(len(payload.compared_documents), 2)
        self.assertTrue(payload.comparison_findings)
        self.assertTrue(any(table.get("title") == "Comparison findings" for table in run["sections"]["tables"]))
        self.assertIn("different operating models", run["result"].summary)
        self.assertIn("Next steps", run["panels_html"])
        self.assertEqual(run["export_result"]["status"], "completed")

    def test_action_plan_front_flow_extracts_owners_deadlines_and_actions(self) -> None:
        run = self._run_front_flow(
            workflow_id="action_plan_evidence_review",
            file_paths=[ACTION_PLAN_PATH],
        )

        payload = run["result"].structured_result.validated_output
        structured_response = payload.structured_response if isinstance(payload.structured_response, dict) else {}

        self.assertEqual(run["index_status"]["ok"], True)
        self.assertEqual(run["result"].status, "warning")
        self.assertEqual(payload.tool_used, "extract_operational_tasks")
        self.assertTrue(structured_response.get("actions"))
        self.assertTrue(any("Preserve records" in item for item in structured_response.get("actions", [])))
        self.assertTrue(any(table.get("title") == "Action plan" for table in run["sections"]["tables"]))
        self.assertTrue(run["sections"]["next_steps"])
        self.assertIn("Decision-ready summary", run["summary_html"])
        self.assertEqual(run["export_result"]["status"], "completed")


if __name__ == "__main__":
    unittest.main()