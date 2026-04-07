import importlib.util
import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from src.config import PresentationExportSettings, get_rag_settings
from src.gradio_ui.components import build_result_summary_html
from src.product.models import ProductWorkflowRequest
from src.product.presenters import build_product_result_sections
from src.product.service import generate_product_workflow_deck, index_loaded_documents, run_product_workflow
from src.rag.loaders import load_document
from src.rag.service import normalize_rag_index
from src.storage.rag_store import load_rag_store


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REAL_RESUME_1_PATH = PROJECT_ROOT / "data" / "materials_demo" / "cv_analysis" / "Sample-Resume-1-07262023.pdf"
SYNTHETIC_TXT_PATH = PROJECT_ROOT / "phase5_eval" / "fixtures" / "04_cv_sample.txt"
GOLD_RESUME_1_PATH = PROJECT_ROOT / "phase5_eval" / "fixtures" / "14_cv_sample_resume_1_gold.json"
EVAL_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_phase5_structured_eval.py"


def _load_eval_module():
    spec = importlib.util.spec_from_file_location("phase5_real_document_eval_front", EVAL_SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


eval_module = _load_eval_module()


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


class _RuleBasedCandidateProvider:
    def list_available_models(self):
        return ["candidate-review-fake"]

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
        if "Francis B. Taylor" in prompt:
            return json.dumps(
                {
                    "task_type": "cv_analysis",
                    "personal_info": {
                        "full_name": "Francis B. Taylor",
                        "email": "francisjtaylor@gmail.com",
                        "phone": "617-343-0338",
                        "location": "Cincinnati, OH 45201",
                        "links": [],
                    },
                    "sections": [
                        {
                            "section_type": "summary",
                            "title": "Professional Summary",
                            "content": [
                                {
                                    "text": "Science-oriented candidate with biochemistry training and medical-device research experience.",
                                    "details": {},
                                }
                            ],
                            "confidence": 0.95,
                        },
                        {
                            "section_type": "interests",
                            "title": "Interests",
                            "content": [
                                {"text": "Bollywood movies", "details": {}},
                                {"text": "nature documentaries", "details": {}},
                                {"text": "hiking", "details": {}},
                                {"text": "boxing", "details": {}},
                                {"text": "gardening", "details": {}},
                            ],
                            "confidence": 0.9,
                        },
                    ],
                    "skills": [
                        "Biochemistry",
                        "scientific support",
                        "surgical support",
                        "medical devices",
                        "laboratory manuals",
                        "community building",
                    ],
                    "languages": [],
                    "education_entries": [
                        {
                            "degree": "Bachelor of Science, Biochemistry",
                            "institution": "Creighton University",
                            "location": "Omaha, NE",
                            "date_range": "May 2019",
                            "description": "Bachelor of Science, Biochemistry • Phi Beta Kappa • Magna Cum Laude",
                        }
                    ],
                    "experience_entries": [
                        {
                            "title": "Scientist",
                            "organization": "Johnson & Johnson",
                            "location": "Cincinnati, OH",
                            "date_range": "July 2019—Present",
                            "bullets": [
                                "Provide scientific support to project leaders during preclinical studies.",
                                "Offer surgical support during research and development of animate and inanimate models.",
                                "Perform testing to aid in the development of new medical devices.",
                            ],
                        },
                        {
                            "title": "Teaching Assistant",
                            "organization": "Creighton University Department of Chemistry",
                            "location": "Omaha, NE",
                            "date_range": "August 2016—May 2019",
                            "bullets": [
                                "Assisted in the design of lectures, assignments, quizzes, and laboratory manuals.",
                                "Served as grader and primary point of contact for over 150 students.",
                            ],
                        },
                        {
                            "title": "Admissions Fellow",
                            "organization": "Creighton University Admissions Office",
                            "location": "Omaha, NE",
                            "date_range": "Summer 2016, 2017, 2018",
                            "bullets": [
                                "Conducted interviews with prospective applicants and produced written evaluations.",
                                "Led tours and information sessions to prospective students and families.",
                            ],
                        },
                    ],
                    "experience_years": 4.5,
                    "strengths": [
                        "Strong applied scientific execution in research and medical-device environments.",
                        "Evidence of communication and leadership through teaching and admissions support.",
                    ],
                    "improvement_areas": [
                        "Validate long-term leadership scope in industry settings.",
                    ],
                    "projects": [],
                },
                ensure_ascii=False,
            )

        if "Ana Ribeiro" in prompt:
            return json.dumps(
                {
                    "task_type": "cv_analysis",
                    "personal_info": {
                        "full_name": "Ana Ribeiro",
                        "email": "ana.ribeiro@example.com",
                        "phone": "+55 11 98888-7777",
                        "location": "São Paulo, Brazil",
                        "links": ["https://www.linkedin.com/in/anaribeiro"],
                    },
                    "sections": [
                        {
                            "section_type": "summary",
                            "title": "Professional Summary",
                            "content": [
                                {
                                    "text": "AI engineer focused on retrieval-augmented generation, document intelligence, and local LLM applications.",
                                    "details": {},
                                }
                            ],
                            "confidence": 0.95,
                        }
                    ],
                    "skills": ["Python", "RAG", "Streamlit", "Ollama", "Chroma", "Pydantic", "SQL", "Git"],
                    "languages": [
                        {"language": "Portuguese", "level": "native"},
                        {"language": "English", "level": "advanced"},
                        {"language": "French", "level": "intermediate"},
                    ],
                    "education_entries": [
                        {
                            "degree": "B.Sc. in Computer Engineering",
                            "institution": "Federal University of Minas Gerais",
                            "date_range": "2020 to 2024",
                            "location": "Brazil",
                        }
                    ],
                    "experience_entries": [
                        {
                            "title": "AI Engineer",
                            "organization": "Orion Labs",
                            "date_range": "Jan 2024 to Present",
                            "bullets": [
                                "Built a local RAG assistant for internal technical documentation using Python, Ollama, Chroma, and Streamlit.",
                                "Designed structured output pipelines for extraction, summary, and checklist generation.",
                            ],
                        },
                        {
                            "title": "Data Science Intern",
                            "organization": "Vento Analytics",
                            "date_range": "Jul 2023 to Dec 2023",
                            "bullets": [
                                "Created dashboards and evaluated classification models.",
                                "Automated reporting workflows.",
                            ],
                        },
                    ],
                    "experience_years": 1.8,
                    "strengths": [
                        "Hands-on RAG and local LLM delivery with strong document intelligence focus.",
                        "Strong structured outputs foundation for extraction, summary, and checklist tasks.",
                    ],
                    "improvement_areas": [
                        "Validate stakeholder management and production-scale ownership in larger environments.",
                    ],
                    "projects": [],
                },
                ensure_ascii=False,
            )

        return json.dumps(
            {
                "task_type": "cv_analysis",
                "personal_info": {"full_name": None, "email": None, "phone": None, "location": None, "links": []},
                "sections": [],
                "skills": [],
                "languages": [],
                "education_entries": [],
                "experience_entries": [],
                "experience_years": 0.0,
                "strengths": [],
                "improvement_areas": ["Validate missing core candidate signals manually."],
                "projects": [],
            },
            ensure_ascii=False,
        )


class CandidateReviewFrontIntegrationTests(unittest.TestCase):
    def _provider_registry(self):
        provider = _RuleBasedCandidateProvider()
        return {
            "ollama": {
                "label": "Ollama (fake)",
                "instance": provider,
                "supports_chat": True,
                "supports_embeddings": True,
                "default_model": "candidate-review-fake",
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
            embedding_model="candidate-review-fake-embed",
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
                    "quality_review": {"score": 0.93},
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

    def _run_front_flow(self, *, file_path: Path, input_text: str | None = None):
        with tempfile.TemporaryDirectory() as temp_dir:
            rag_settings = self._rag_settings(temp_dir)
            provider_registry = self._provider_registry()
            uploaded = _UploadAdapter(file_path)
            loaded_document = load_document(uploaded, rag_settings)
            indexed_documents, index_status = index_loaded_documents(
                [loaded_document],
                rag_settings=rag_settings,
                provider_registry=provider_registry,
            )
            rag_index = normalize_rag_index(load_rag_store(rag_settings.store_path), rag_settings)
            self.assertIsNotNone(rag_index)
            document_id = indexed_documents[0].document_id
            request = ProductWorkflowRequest(
                workflow_id="candidate_review",
                document_ids=[document_id],
                input_text=input_text or "Review this candidate for hiring fit.",
                provider="ollama",
                model="candidate-review-fake",
                context_strategy="document_scan",
            )

            with (
                patch("src.providers.registry.build_provider_registry", return_value=provider_registry),
                patch("src.services.document_context._get_rag_index", return_value=rag_index),
                patch("src.services.document_context._get_effective_rag_settings", return_value=rag_settings),
                patch("src.services.document_context._get_embedding_provider", return_value=provider_registry["ollama"]["instance"]),
            ):
                result = run_product_workflow(request)
                sections = build_product_result_sections(result)
                html = build_result_summary_html(result)

                with patch("src.services.presentation_export_service.urllib_request.urlopen", side_effect=self._fake_urlopen):
                    export_result, artifacts = generate_product_workflow_deck(
                        result,
                        settings=self._service_settings(temp_dir),
                        workspace_root=Path(temp_dir),
                    )

            return {
                "loaded_document": loaded_document,
                "index_status": index_status,
                "result": result,
                "sections": sections,
                "html": html,
                "export_result": export_result,
                "artifacts": artifacts,
            }

    def test_front_flow_real_pdf_sample_resume_matches_gold_and_exports(self) -> None:
        gold = json.loads(GOLD_RESUME_1_PATH.read_text(encoding="utf-8"))

        run = self._run_front_flow(file_path=REAL_RESUME_1_PATH, input_text=gold["input_text"])
        payload = run["result"].structured_result.validated_output.model_dump(mode="json")
        evaluation = eval_module._evaluate_payload_against_gold("cv_analysis", payload, gold)

        self.assertEqual(run["index_status"]["ok"], True)
        self.assertEqual(run["result"].status, "completed")
        self.assertEqual(evaluation["status"], "PASS")
        self.assertEqual(run["sections"]["candidate_profile"]["name"], "Francis B. Taylor")
        self.assertIn("Candidate: Francis B. Taylor", run["html"])
        self.assertEqual(run["export_result"]["status"], "completed")
        self.assertTrue(any(artifact.artifact_type == "pptx" for artifact in run["artifacts"]))

    def test_front_flow_synthetic_txt_resume_behaves_like_user_upload(self) -> None:
        run = self._run_front_flow(
            file_path=SYNTHETIC_TXT_PATH,
            input_text="Review this candidate profile and prepare a hiring recommendation with strengths, gaps and next steps.",
        )

        payload = run["result"].structured_result.validated_output.model_dump(mode="json")

        self.assertEqual(run["index_status"]["ok"], True)
        self.assertEqual(run["loaded_document"].file_type, "txt")
        self.assertIn("Ana Ribeiro", run["loaded_document"].text)
        self.assertEqual(run["result"].status, "completed")
        self.assertEqual(payload["personal_info"]["full_name"], "Ana Ribeiro")
        self.assertIn("RAG", " ".join(payload["skills"]))
        self.assertIn("Candidate: Ana Ribeiro", run["html"])
        self.assertTrue(run["sections"]["next_steps"])
        self.assertEqual(run["export_result"]["status"], "completed")
        self.assertGreaterEqual(len(run["artifacts"]), 3)


if __name__ == "__main__":
    unittest.main()