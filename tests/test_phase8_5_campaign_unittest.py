import json
import tempfile
import unittest
from pathlib import Path

from src.services.phase8_5_benchmark import load_benchmark_manifest
from src.services.phase8_5_campaign import (
    DEFAULT_PHASE8_5_STAGE_ORDER,
    build_phase8_5_campaign_id,
    build_phase8_5_campaign_plan,
)
from src.services.phase8_5_decision_gate import find_latest_phase8_5_run_dir


class _FakeProvider:
    def _discover_local_models(self):
        return [
            "qwen2.5:7b",
            "embeddinggemma:300m",
            "qwen3-embedding:0.6b",
        ]

    @staticmethod
    def _looks_like_embedding_model(model: str) -> bool:
        normalized = str(model).lower()
        return "embed" in normalized or "embedding" in normalized or "bge" in normalized

    def list_available_models(self):
        return ["qwen2.5:7b-ollama"]

    def list_available_embedding_models(self):
        return ["embeddinggemma:300m"]


class Phase85CampaignTests(unittest.TestCase):
    def test_build_campaign_id_is_stable(self) -> None:
        manifest = load_benchmark_manifest()
        campaign_id_a = build_phase8_5_campaign_id(
            manifest,
            selected_groups=["generation", "embeddings", "rerankers", "ocr_vlm"],
            provider_filter=None,
            model_filter=None,
            smoke=False,
        )
        campaign_id_b = build_phase8_5_campaign_id(
            manifest,
            selected_groups=["generation", "embeddings", "rerankers", "ocr_vlm"],
            provider_filter=None,
            model_filter=None,
            smoke=False,
        )

        self.assertEqual(campaign_id_a, campaign_id_b)

    def test_build_campaign_plan_creates_ordered_group_runs(self) -> None:
        manifest = load_benchmark_manifest()
        registry = {
            "ollama": {
                "label": "Ollama (local)",
                "instance": _FakeProvider(),
                "supports_chat": True,
                "supports_embeddings": True,
                "default_model": "qwen2.5:7b",
            },
            "huggingface_server": {
                "label": "HF server local",
                "instance": _FakeProvider(),
                "supports_chat": True,
                "supports_embeddings": True,
                "default_model": "qwen2.5:7b-ollama",
            },
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            campaign_dir = Path(tmp_dir) / "campaign"
            plan = build_phase8_5_campaign_plan(
                manifest,
                registry=registry,
                campaign_id="campaign-1",
                campaign_dir=campaign_dir,
                selected_groups=list(DEFAULT_PHASE8_5_STAGE_ORDER),
                smoke=True,
                provider_filter=None,
                model_filter=None,
                resume=False,
            )

        self.assertEqual(plan["selected_groups"], list(DEFAULT_PHASE8_5_STAGE_ORDER))
        self.assertEqual([item["group"] for item in plan["stages"]], list(DEFAULT_PHASE8_5_STAGE_ORDER))
        self.assertTrue(str(plan["stages"][0]["run_dir"]).endswith("01_generation_" + plan["stages"][0]["run_id"]))
        self.assertEqual(plan["preflight"]["campaign_mode"], "staged_full_matrix")

    def test_find_latest_phase8_5_run_dir_sees_campaign_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            campaign_run_dir = root / "benchmark_runs" / "phase8_5_matrix_campaigns" / "campaign-1"
            (campaign_run_dir / "aggregated").mkdir(parents=True, exist_ok=True)
            (campaign_run_dir / "aggregated" / "summary.json").write_text(
                json.dumps({"total_cases": 4, "successful_cases": 4, "failed_cases": 0}),
                encoding="utf-8",
            )
            (campaign_run_dir / "aggregated" / "latest_case_results.json").write_text(
                json.dumps(
                    [
                        {"group": "generation", "status": "success", "run_id": "g"},
                        {"group": "embeddings", "status": "success", "run_id": "e"},
                        {"group": "rerankers", "status": "success", "run_id": "r"},
                        {"group": "ocr_vlm", "status": "success", "run_id": "o"},
                    ]
                ),
                encoding="utf-8",
            )
            (campaign_run_dir / "manifest.resolved.json").write_text(
                json.dumps({"groups": {"generation": {}, "embeddings": {}, "rerankers": {}, "ocr_vlm": {}}}),
                encoding="utf-8",
            )
            (campaign_run_dir / "preflight.json").write_text(
                json.dumps({"run_id": "campaign-1", "selected_groups": ["generation", "embeddings", "rerankers", "ocr_vlm"]}),
                encoding="utf-8",
            )

            discovered = find_latest_phase8_5_run_dir(root)

        self.assertEqual(discovered, campaign_run_dir)


if __name__ == "__main__":
    unittest.main()