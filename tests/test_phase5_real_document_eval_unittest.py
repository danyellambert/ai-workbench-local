import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.structured.base import CodeAnalysisPayload, CodeIssue, CVAnalysisPayload, ContactInfo, EducationEntry, ExperienceEntry, ExtractionPayload, ExtractedField, Entity
from src.structured.envelope import StructuredResult
from src.structured.tasks import CVAnalysisTaskHandler, ExtractionTaskHandler, CodeAnalysisTaskHandler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_phase5_structured_eval.py"
GOLD_CODE_PATH = PROJECT_ROOT / "phase5_eval" / "fixtures" / "07_code_analysis_demo_gold.json"
GOLD_SUMMARY_ASAP_PATH = PROJECT_ROOT / "phase5_eval" / "fixtures" / "12_summary_asap_2025_annual_report_gold.json"
GOLD_EXTRACTION_EX10_PATH = PROJECT_ROOT / "phase5_eval" / "fixtures" / "13_extraction_exhibit10_3_gold.json"
GOLD_CV_SAMPLE_RESUME_PATH = PROJECT_ROOT / "phase5_eval" / "fixtures" / "14_cv_sample_resume_1_gold.json"
GOLD_CV_SAMPLE_RESUME_2_PATH = PROJECT_ROOT / "phase5_eval" / "fixtures" / "15_cv_sample_resume_2_gold.json"
GOLD_CV_SAMPLE_RESUME_3_PATH = PROJECT_ROOT / "phase5_eval" / "fixtures" / "16_cv_sample_resume_3_gold.json"
GOLD_MANIFEST_PATH = PROJECT_ROOT / "phase5_eval" / "fixtures" / "11_real_document_gold_sets_manifest.json"


def _load_eval_module():
    spec = importlib.util.spec_from_file_location("phase5_real_document_eval", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


eval_module = _load_eval_module()


class Phase5RealDocumentEvalTests(unittest.TestCase):
    def test_prepare_eval_request_builds_indexed_document_request_from_gold_fixture(self) -> None:
        fake_rag_store = {
            "documents": [
                {
                    "document_id": "doc-code-1",
                    "name": "demo_code_analysis.py",
                    "file_type": "py",
                    "chunk_count": 1,
                }
            ]
        }

        with patch.object(eval_module, "_load_rag_store", return_value=fake_rag_store):
            prepared = eval_module._prepare_eval_request(
                task="code_analysis",
                provider="ollama",
                model=None,
                cv_pdf=None,
                use_indexed_document=True,
                document_name=None,
                document_id=None,
                context_strategy="document_scan",
                gold_fixture_path=str(GOLD_CODE_PATH),
                gold_manifest_path=str(GOLD_MANIFEST_PATH),
            )

        request = prepared["request"]
        self.assertEqual(prepared["mode"], "indexed_document")
        self.assertEqual(prepared["suite_name"], "structured_real_document_eval")
        self.assertEqual(prepared["resolved_document"]["document_id"], "doc-code-1")
        self.assertTrue(request.use_document_context)
        self.assertEqual(request.source_document_ids, ["doc-code-1"])
        self.assertEqual(request.context_strategy, "document_scan")
        self.assertIn("Analyze the selected code file", request.input_text)

    def test_evaluate_payload_against_gold_returns_pass_for_code_analysis_payload(self) -> None:
        gold_fixture = json.loads(GOLD_CODE_PATH.read_text(encoding="utf-8"))
        payload = {
            "task_type": "code_analysis",
            "snippet_summary": "Functions that normalize item scores and compute an aggregate average.",
            "main_purpose": "Normalize score values and compute an average.",
            "detected_issues": [
                {
                    "severity": "high",
                    "category": "runtime_failure",
                    "title": "Division by zero on empty input",
                    "description": "average computation fails when items is empty.",
                    "evidence": "average = total / len(values)",
                    "recommendation": "Guard against division by zero and return average 0.0 for empty input.",
                },
                {
                    "severity": "medium",
                    "category": "input_mutation",
                    "title": "Mutates caller-provided items in place",
                    "description": "normalize_scores changes the input dictionaries.",
                    "evidence": "item[\"score\"] = 100",
                    "recommendation": "Copy the item before clamping score.",
                },
                {
                    "severity": "medium",
                    "category": "api_contract",
                    "title": "Output structure is inconsistent",
                    "description": "items without score pass through unchanged.",
                    "evidence": "else: result.append(item)",
                    "recommendation": "Always return objects with the same shape.",
                },
            ],
            "readability_improvements": [
                "Document the expected input/output schema.",
            ],
            "maintainability_improvements": [
                "Separate normalization from aggregation.",
            ],
            "refactor_plan": [
                "Handle empty input before dividing.",
                "Avoid mutating input items.",
                "Normalize the output schema consistently.",
            ],
            "test_suggestions": [
                "Test empty input.",
                "Test score clamping above 100 and below 0.",
                "Test that the original input is not mutated.",
            ],
            "risk_notes": [
                "Runtime crash on empty input.",
                "Mixed output shape can break consumers expecting consistent schema.",
            ],
        }

        evaluation = eval_module._evaluate_payload_against_gold("code_analysis", payload, gold_fixture)

        self.assertEqual(evaluation["status"], "PASS")
        self.assertGreaterEqual(evaluation["metrics"]["issue_hits"], 3)
        self.assertGreaterEqual(evaluation["metrics"]["refactor_hits"], 3)
        self.assertGreaterEqual(evaluation["metrics"]["test_hits"], 3)

    def test_run_tasks_records_gold_metadata_for_indexed_document_eval(self) -> None:
        fake_rag_store = {
            "documents": [
                {
                    "document_id": "doc-code-1",
                    "name": "demo_code_analysis.py",
                    "file_type": "py",
                    "chunk_count": 1,
                }
            ]
        }
        fake_result = StructuredResult(
            success=True,
            task_type="code_analysis",
            raw_output_text="{}",
            parsed_json={},
            validated_output=CodeAnalysisPayload(
                task_type="code_analysis",
                snippet_summary="Functions that normalize item scores and compute an aggregate average.",
                main_purpose="Normalize score values and compute an average.",
                detected_issues=[
                    CodeIssue(
                        severity="high",
                        category="runtime_failure",
                        title="Division by zero on empty input",
                        description="average computation fails when items is empty.",
                        evidence="average = total / len(values)",
                        recommendation="Guard against division by zero and return average 0.0 for empty input.",
                    ),
                    CodeIssue(
                        severity="medium",
                        category="input_mutation",
                        title="Mutates caller-provided items in place",
                        description="normalize_scores changes the input dictionaries.",
                        evidence="item[\"score\"] = 100",
                        recommendation="Copy the item before clamping score.",
                    ),
                    CodeIssue(
                        severity="medium",
                        category="api_contract",
                        title="Output structure is inconsistent",
                        description="items without score pass through unchanged.",
                        evidence="else: result.append(item)",
                        recommendation="Always return objects with the same shape.",
                    ),
                ],
                readability_improvements=["Document the expected input/output schema."],
                maintainability_improvements=["Separate normalization from aggregation."],
                refactor_plan=[
                    "Handle empty input before dividing.",
                    "Avoid mutating input items.",
                    "Normalize the output schema consistently.",
                ],
                test_suggestions=[
                    "Test empty input.",
                    "Test score clamping above 100 and below 0.",
                    "Test that the original input is not mutated.",
                ],
                risk_notes=["Runtime crash on empty input."],
            ),
            execution_metadata={},
            quality_score=0.91,
            overall_confidence=0.9,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_report = Path(tmp_dir) / "report.json"
            with patch.object(eval_module, "_load_rag_store", return_value=fake_rag_store), patch.object(
                eval_module.structured_service,
                "execute_task",
                return_value=fake_result,
            ), patch.object(eval_module, "append_eval_run") as append_mock, patch.object(
                eval_module,
                "_save_report",
                return_value=tmp_report,
            ):
                exit_code = eval_module.run_tasks(
                    ["code_analysis"],
                    provider="ollama",
                    model=None,
                    cv_pdf=None,
                    use_indexed_document=True,
                    document_name="demo_code_analysis.py",
                    context_strategy="document_scan",
                    gold_fixture=str(GOLD_CODE_PATH),
                    gold_manifest=str(GOLD_MANIFEST_PATH),
                )

        self.assertEqual(exit_code, 0)
        append_payload = append_mock.call_args.args[1]
        self.assertEqual(append_payload["suite_name"], "structured_real_document_eval")
        self.assertEqual(append_payload["case_name"], "demo_code_analysis.py")
        self.assertEqual(append_payload["metrics"]["mode"], "indexed_document")
        self.assertEqual(append_payload["metrics"]["gold_status"], "PASS")

    def test_evaluate_payload_against_gold_accepts_semantic_code_analysis_matches(self) -> None:
        gold_fixture = json.loads(GOLD_CODE_PATH.read_text(encoding="utf-8"))
        payload = {
            "task_type": "code_analysis",
            "snippet_summary": "Função que normaliza pontuações e calcula média.",
            "main_purpose": "Normalizar score e computar média final.",
            "detected_issues": [
                {
                    "severity": "high",
                    "category": "runtime_failure",
                    "title": "Divisão por zero quando a lista está vazia",
                    "description": "A média quebra com lista vazia.",
                    "evidence": "average = total / len(values)",
                    "recommendation": "Retornar 0.0 com lista vazia.",
                }
            ],
            "refactor_plan": [
                "Evitar mutação in place dos itens.",
                "Retornar 0.0 para entrada vazia.",
                "Manter formato de saída consistente.",
            ],
            "test_suggestions": [
                "Teste de lista vazia.",
                "Teste de clamping acima de 100 e abaixo de 0.",
                "Teste que garanta que a entrada original não foi mutada.",
            ],
            "maintainability_improvements": ["Separar normalização da agregação."],
            "risk_notes": ["Saída inconsistente pode quebrar consumidores."],
        }

        evaluation = eval_module._evaluate_payload_against_gold("code_analysis", payload, gold_fixture)

        self.assertNotEqual(evaluation["metrics"]["main_purpose_hit"], 0)
        self.assertNotEqual(evaluation["metrics"]["test_hits"], 0)

    def test_prepare_eval_request_uses_manifest_for_new_summary_gold_set(self) -> None:
        fake_rag_store = {
            "documents": [
                {
                    "document_id": "doc-summary-1",
                    "name": "asap-2025-annual-report-tagged.pdf",
                    "file_type": "pdf",
                    "chunk_count": 11,
                }
            ]
        }

        with patch.object(eval_module, "_load_rag_store", return_value=fake_rag_store):
            prepared = eval_module._prepare_eval_request(
                task="summary",
                provider="ollama",
                model=None,
                cv_pdf=None,
                use_indexed_document=True,
                document_name="asap-2025-annual-report-tagged.pdf",
                document_id=None,
                context_strategy="retrieval",
                gold_fixture_path=None,
                gold_manifest_path=str(GOLD_MANIFEST_PATH),
            )

        self.assertEqual(prepared["suite_name"], "structured_real_document_eval")
        self.assertEqual(prepared["gold_fixture_path"], str(GOLD_SUMMARY_ASAP_PATH))
        self.assertEqual(prepared["resolved_document"]["document_id"], "doc-summary-1")
        self.assertIn("human-spaceflight risk view", prepared["request"].input_text)

    def test_prepare_eval_request_uses_manifest_for_new_cv_gold_set(self) -> None:
        fake_rag_store = {
            "documents": [
                {
                    "document_id": "doc-cv-2",
                    "name": "Sample-Resume-1-07262023.pdf",
                    "file_type": "pdf",
                    "chunk_count": 4,
                }
            ]
        }

        with patch.object(eval_module, "_load_rag_store", return_value=fake_rag_store):
            prepared = eval_module._prepare_eval_request(
                task="cv_analysis",
                provider="ollama",
                model=None,
                cv_pdf=None,
                use_indexed_document=True,
                document_name="Sample-Resume-1-07262023.pdf",
                document_id=None,
                context_strategy="document_scan",
                gold_fixture_path=None,
                gold_manifest_path=str(GOLD_MANIFEST_PATH),
            )

        self.assertEqual(prepared["gold_fixture_path"], str(GOLD_CV_SAMPLE_RESUME_PATH))
        self.assertEqual(prepared["resolved_document"]["document_id"], "doc-cv-2")

    def test_prepare_eval_request_uses_manifest_for_additional_cv_gold_sets(self) -> None:
        fake_rag_store = {
            "documents": [
                {
                    "document_id": "doc-cv-3",
                    "name": "Sample-Resume-2-1.pdf",
                    "file_type": "pdf",
                    "chunk_count": 4,
                },
                {
                    "document_id": "doc-cv-4",
                    "name": "Sample-Resume-3-.pdf",
                    "file_type": "pdf",
                    "chunk_count": 5,
                },
            ]
        }

        with patch.object(eval_module, "_load_rag_store", return_value=fake_rag_store):
            prepared_2 = eval_module._prepare_eval_request(
                task="cv_analysis",
                provider="ollama",
                model=None,
                cv_pdf=None,
                use_indexed_document=True,
                document_name="Sample-Resume-2-1.pdf",
                document_id=None,
                context_strategy="document_scan",
                gold_fixture_path=None,
                gold_manifest_path=str(GOLD_MANIFEST_PATH),
            )
            prepared_3 = eval_module._prepare_eval_request(
                task="cv_analysis",
                provider="ollama",
                model=None,
                cv_pdf=None,
                use_indexed_document=True,
                document_name="Sample-Resume-3-.pdf",
                document_id=None,
                context_strategy="document_scan",
                gold_fixture_path=None,
                gold_manifest_path=str(GOLD_MANIFEST_PATH),
            )

        self.assertEqual(prepared_2["gold_fixture_path"], str(GOLD_CV_SAMPLE_RESUME_2_PATH))
        self.assertEqual(prepared_2["resolved_document"]["document_id"], "doc-cv-3")
        self.assertEqual(prepared_3["gold_fixture_path"], str(GOLD_CV_SAMPLE_RESUME_3_PATH))
        self.assertEqual(prepared_3["resolved_document"]["document_id"], "doc-cv-4")

    def test_new_real_document_gold_sets_expose_threshold_overrides(self) -> None:
        summary_gold = json.loads(GOLD_SUMMARY_ASAP_PATH.read_text(encoding="utf-8"))
        extraction_gold = json.loads(GOLD_EXTRACTION_EX10_PATH.read_text(encoding="utf-8"))

        summary_payload = {
            "topics": ["Artemis", "ISS", "contracts"],
            "executive_summary": "The report says Artemis III carries too many first-time risks and that the ISS is entering its riskiest period.",
            "key_insights": ["Artemis III risk posture is too aggressive."],
        }
        extraction_payload = {
            "main_subject": "Seller’s Purchase, Warranties and Interim Servicing Agreement between DLJ Mortgage Capital, Inc. and E-LOAN, Inc.",
            "categories": ["Agreement", "Contract"],
            "entities": [{"value": "DLJ Mortgage Capital, Inc.", "type": "organization"}],
            "extracted_fields": [],
            "relationships": [],
            "important_dates": ["April 1, 2003"],
            "important_numbers": ["$7"],
            "action_items": [],
            "risks": [],
        }

        summary_eval = eval_module._evaluate_payload_against_gold("summary", summary_payload, summary_gold)
        extraction_eval = eval_module._evaluate_payload_against_gold("extraction", extraction_payload, extraction_gold)

        self.assertEqual(summary_eval["thresholds"]["pass_ratio"], 0.6)
        self.assertEqual(extraction_eval["thresholds"]["pass_ratio"], 0.64)

    def test_cv_post_processing_recovers_languages_sections_and_organization(self) -> None:
        handler = CVAnalysisTaskHandler()
        result = StructuredResult(
            success=True,
            task_type="cv_analysis",
            raw_output_text="{}",
            parsed_json={},
            validated_output=CVAnalysisPayload(
                task_type="cv_analysis",
                personal_info=ContactInfo(
                    full_name="Lucas de Souza Ferreira",
                    email="lucas.souza-ferreira@student-cs.fr",
                    location="Rio de Janeiro, Brésil",
                    links=[],
                ),
                sections=[],
                skills=["Python", "MATLAB"],
                languages=["Portugais", "Français", "Anglais"],
                education_entries=[
                    EducationEntry(
                        degree="Ingénieur spécialisé en Énergie",
                        institution="CentraleSupélec",
                        date_range="2021-2023",
                        description="Ingénieur spécialisé en Énergie | CentraleSupélec | 2021-2023",
                    ),
                    EducationEntry(
                        degree="Formation d'Ingénieur : Université Fédérale du Rio de Janeiro Musique (Guitare et Flûte depuis 2014)",
                        institution=None,
                        description="Formation d'Ingénieur : Université Fédérale du Rio de Janeiro Musique (Guitare et Flûte depuis 2014)",
                    ),
                ],
                experience_entries=[
                    ExperienceEntry(
                        title="Optimisation de l’emplacement des générateurs distribués dans un réseau électrique",
                        organization="Projet",
                        date_range="02/2022 - 04/2022",
                        bullets=["Développement des méthodes d’optimisation sur MATLAB."],
                        description="Optimisation de l’emplacement des générateurs distribués dans un réseau électrique | CentraleSupélec | 02/2022 - 04/2022",
                    )
                ],
                experience_years=3.0,
                strengths=["Travail en équipe"],
            ),
        )
        source_text = """
        Lucas de Souza Ferreira
        /in/lucas-de-souza-ferreira/
        Portugais Natif
        Français Bilingue
        Anglais Bilingue
        Formation d'Ingénieur : Université Fédérale du Rio de Janeiro
        Ingénieur spécialisé en Électrotechnique 2018-2024 | Rio de Janeiro
        Optimisation de l’emplacement des générateurs distribués dans un réseau électrique | CentraleSupélec | 02/2022 - 04/2022
        """

        normalized = handler._post_process_cv_result(result, source_text=source_text).validated_output

        self.assertIn("Français — Bilingue", normalized.languages)
        self.assertIn("Anglais — Bilingue", normalized.languages)
        self.assertTrue(normalized.sections)
        section_types = [section.section_type for section in normalized.sections]
        self.assertIn("education", section_types)
        self.assertIn("experience", section_types)
        self.assertIn("/in/lucas-de-souza-ferreira/", normalized.personal_info.links)
        self.assertTrue(any((entry.get("institution") or "") == "Université Fédérale du Rio de Janeiro" for entry in normalized.model_dump(mode="python")["education_entries"]))
        self.assertEqual(normalized.experience_entries[0].organization, "CentraleSupélec")

    def test_extraction_prompt_mentions_legal_clause_requirements(self) -> None:
        handler = ExtractionTaskHandler()
        prompt = handler._build_extraction_prompt("Analyze legal agreement", "Separation Agreement text")

        self.assertIn("governing law", prompt)
        self.assertIn("jurisdiction/forum", prompt)
        self.assertIn("notice periods", prompt)
        self.assertIn("clause-level duties", prompt)

    def test_code_analysis_post_processing_recovers_grounded_missing_issues(self) -> None:
        handler = CodeAnalysisTaskHandler()
        result = StructuredResult(
            success=True,
            task_type="code_analysis",
            raw_output_text="{}",
            parsed_json={},
            validated_output=CodeAnalysisPayload(
                task_type="code_analysis",
                snippet_summary="Código que normaliza pontuações e calcula uma média.",
                main_purpose="Normalizar score e computar média.",
                detected_issues=[],
                readability_improvements=[],
                maintainability_improvements=[],
                refactor_plan=[],
                test_suggestions=[],
                risk_notes=[],
            ),
        )
        source_text = PROJECT_ROOT.joinpath("phase5_eval", "fixtures", "05_code_sample.py").read_text(encoding="utf-8")

        normalized = handler._post_process_code_analysis_result(result, source_text=source_text).validated_output
        issue_titles = [issue.title for issue in normalized.detected_issues]

        self.assertIn("Division by zero on empty input", issue_titles)
        self.assertIn("Mutates caller-provided items in place", issue_titles)
        self.assertIn("Output structure is inconsistent", issue_titles)
        self.assertGreaterEqual(len(normalized.refactor_plan), 3)
        self.assertGreaterEqual(len(normalized.test_suggestions), 3)

    def test_match_object_entries_accepts_partial_semantic_cv_match(self) -> None:
        hits = eval_module._match_object_entries(
            [
                {
                    "degree": "Master en Réseaux et Renouvelables",
                    "institution": "Université Paris-Saclay",
                    "location": "Paris-Saclay",
                    "date_range": "2022-2023",
                }
            ],
            [
                {
                    "institution_aliases": ["Université Paris-Saclay"],
                    "degree_aliases": ["Master en Réseaux et Renouvelables", "Master Spécialisé"],
                    "date_aliases": ["2022-2023"],
                    "location_aliases": ["Paris-Saclay"],
                    "description_terms": ["production d'énergie décentralisée"],
                }
            ],
        )

        self.assertEqual(hits, 1)

    def test_cv_post_processing_recovers_paris_saclay_and_drops_date_only_experience(self) -> None:
        handler = CVAnalysisTaskHandler()
        result = StructuredResult(
            success=True,
            task_type="cv_analysis",
            raw_output_text="{}",
            parsed_json={},
            validated_output=CVAnalysisPayload(
                task_type="cv_analysis",
                personal_info=ContactInfo(full_name="Lucas de Souza Ferreira"),
                sections=[],
                skills=[],
                languages=[],
                education_entries=[
                    EducationEntry(
                        degree="Master Spécialisé : Université Paris-Saclay Master en Réseaux et Renouvelables 2022-2023",
                        institution=None,
                        description="Master Spécialisé : Université Paris-Saclay Master en Réseaux et Renouvelables 2022-2023",
                    )
                ],
                experience_entries=[
                    ExperienceEntry(
                        title="07/2024 - 12/2024",
                        organization=None,
                        date_range="07/2024 - 12/2024",
                        bullets=[],
                        description="07/2024 - 12/2024",
                    ),
                    ExperienceEntry(
                        title="Développement d’interface pour l'analyse de la courbe de charge du sistema elétrico",
                        organization="ONS",
                        date_range="07/2024 - 12/2024",
                        bullets=["Visualisation en temps réel"],
                        description="Développement d’interface pour l'analyse de la courbe de charge du sistema elétrico | ONS | 07/2024 - 12/2024",
                    ),
                ],
                experience_years=2.0,
                strengths=[],
            ),
        )
        source_text = """
        Master Spécialisé : Université Paris-Saclay
        Master en Réseaux et Renouvelables | Paris-Saclay | 2022-2023
        Développement d’interface pour l'analyse de la courbe de charge du sistema elétrico | ONS | 07/2024 - 12/2024
        Visualisation en temps réel
        """

        normalized = handler._post_process_cv_result(result, source_text=source_text).validated_output
        education_dump = normalized.model_dump(mode="python")["education_entries"]

        self.assertTrue(any((entry.get("institution") or "") == "Université Paris-Saclay" for entry in education_dump))
        self.assertEqual(len(normalized.experience_entries), 1)
        self.assertEqual(normalized.experience_entries[0].organization, "ONS")


if __name__ == "__main__":
    unittest.main()