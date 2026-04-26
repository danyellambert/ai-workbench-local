#!/usr/bin/env python3
"""
Static runtime/provider diagnostic for AI Decision Studio.
Run from the repository root after activating the same virtualenv used by the backend.
It does not print raw API keys; only sha256 fingerprints.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
from typing import Any

SECRET_ENV_NAMES = [
    "OLLAMA_BASE_URL",
    "OLLAMA_HOSTED_BASE_URL",
    "OLLAMA_HOSTED_API_KEY",
    "OLLAMA_API_KEY",
    "HUGGINGFACEHUB_API_TOKEN",
    "HUGGINGFACE_INFERENCE_API_KEY",
    "HF_TOKEN",
    "HF_LOCAL_LLM_SERVICE_BASE_URL",
    "OPENAI_API_KEY",
]
SECRET_STORE_KEYS = [
    "ollama_hosted_api_key",
    "huggingface_inference_api_key",
    "openai_api_key",
]


def fp(value: object) -> str | None:
    text = str(value or "")
    if not text:
        return None
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()[:12]


def jdump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def safe_import(name: str):
    try:
        return importlib.import_module(name)
    except Exception as exc:
        print(f"[import-error] {name}: {exc!r}")
        return None


def maybe_call(obj: object, name: str, *args):
    try:
        fn = getattr(obj, name)
    except Exception:
        return None
    try:
        return fn(*args)
    except Exception as exc:
        return f"<error {type(exc).__name__}: {exc}>"


def redact_json(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            lower = str(k).lower()
            if any(token in lower for token in ["api_key", "apikey", "secret", "token", "authorization", "credential", "password"]):
                out[k] = None if not v else f"<redacted sha256:{fp(v)}>"
            else:
                out[k] = redact_json(v)
        return out
    if isinstance(value, list):
        return [redact_json(v) for v in value]
    return value


def summarize_profile(profile: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(profile, dict):
        return {"profile": None}
    generation = profile.get("generation") if isinstance(profile.get("generation"), dict) else {}
    return {
        "id": profile.get("id"),
        "name": profile.get("name"),
        "isActive": profile.get("isActive"),
        "primaryConnectionId": profile.get("primaryConnectionId"),
        "primaryModel": profile.get("primaryModel"),
        "embeddingConnectionId": profile.get("embeddingConnectionId"),
        "embeddingModel": profile.get("embeddingModel"),
        "executionPolicy": profile.get("executionPolicy"),
        "fallbackEnabled": profile.get("fallbackEnabled"),
        "fallbackChain": profile.get("fallbackChain"),
        "generation": {
            "maxOutputTokens": generation.get("maxOutputTokens"),
            "temperature": generation.get("temperature"),
            "topP": generation.get("topP"),
            "contextWindow": generation.get("contextWindow"),
            "promptProfile": generation.get("promptProfile"),
        },
        "retrievalStrategy": profile.get("retrievalStrategy"),
        "qualityPosture": profile.get("qualityPosture"),
        "docProcessingPreset": profile.get("docProcessingPreset"),
    }


def summarize_registry(registry: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, entry in sorted(registry.items()):
        if not isinstance(entry, dict):
            continue
        instance = entry.get("instance")
        settings = getattr(instance, "settings", None) or getattr(instance, "_settings", None)
        item = {
            "label": entry.get("label"),
            "supports_chat": entry.get("supports_chat"),
            "supports_embeddings": entry.get("supports_embeddings"),
            "default_model": entry.get("default_model"),
            "default_context_window": entry.get("default_context_window"),
            "instance_class": instance.__class__.__name__ if instance is not None else None,
        }
        if settings is not None:
            for attr in ["base_url", "model", "default_model", "embedding_model", "default_context_window"]:
                if hasattr(settings, attr):
                    item[f"settings.{attr}"] = getattr(settings, attr)
            for attr in ["api_key", "token"]:
                if hasattr(settings, attr):
                    item[f"settings.{attr}_fingerprint"] = fp(getattr(settings, attr))
        output[key] = item
    return output


def find_state_files(root: Path) -> list[Path]:
    candidates: list[Path] = []
    names = {
        "preferences-state.json",
        "preferences_state.json",
        "runtime-controls-state.json",
        "runtime_controls_state.json",
        ".preferences-state.json",
        ".runtime-controls-state.json",
    }
    for base in [root, root / ".ai-decision-studio", root / ".ai_decision_studio", root / "data", root / "storage", root / ".runtime", root / "runtime"]:
        if not base.exists():
            continue
        for path in base.rglob("*.json"):
            if path.name in names:
                candidates.append(path)
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")[:4000]
            except Exception:
                continue
            if any(marker in text for marker in ["active_profile_id", "runtime_profiles", "primaryConnectionId", "fallbackChain"]):
                candidates.append(path)
    unique: list[Path] = []
    seen = set()
    for path in candidates:
        resolved = str(path.resolve())
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique[:30]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Repository/workspace root. Default: current directory.")
    parser.add_argument("--show-state-files", action="store_true", help="Print redacted state JSON files that look relevant.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    section("Python/runtime")
    print(jdump({"cwd": str(Path.cwd()), "python": sys.executable, "sys_path_head": sys.path[:5]}))

    section("Environment fingerprints")
    print(jdump({name: (None if not os.getenv(name) else f"set sha256:{fp(os.getenv(name))}") for name in SECRET_ENV_NAMES}))

    section("Keychain/secret-store fingerprints")
    secret_store = safe_import("src.storage.secret_store")
    if secret_store is not None:
        secret_info = {}
        for key in SECRET_STORE_KEYS:
            value = maybe_call(secret_store, "get_secret", key)
            if isinstance(value, str) and value:
                secret_info[key] = f"set sha256:{fp(value)}"
            elif value is None or value == "":
                secret_info[key] = None
            else:
                secret_info[key] = value
        print(jdump(secret_info))

    section("Active runtime profile from backend code")
    runtime_controls = safe_import("src.services.runtime_controls")
    active_profile = None
    if runtime_controls is not None:
        loaded = maybe_call(runtime_controls, "load_active_runtime_profile", root)
        if isinstance(loaded, dict):
            active_profile = loaded
            print(jdump(summarize_profile(loaded)))
        else:
            print(jdump({"load_active_runtime_profile": loaded}))

    section("Provider registry built by backend code")
    registry_mod = safe_import("src.providers.registry")
    registry = None
    if registry_mod is not None:
        built = maybe_call(registry_mod, "build_provider_registry")
        if isinstance(built, dict):
            registry = built
            print(jdump(summarize_registry(built)))
        else:
            print(jdump({"build_provider_registry": built}))

    section("Resolution check for active profile")
    if registry_mod is not None and isinstance(registry, dict) and isinstance(active_profile, dict):
        for capability, provider_field, model_field in [
            ("chat", "primaryConnectionId", "primaryModel"),
            ("embeddings", "embeddingConnectionId", "embeddingModel"),
        ]:
            provider = str(active_profile.get(provider_field) or "").strip()
            model = str(active_profile.get(model_field) or "").strip()
            fallback_provider = None
            try:
                fallback_enabled = bool(active_profile.get("fallbackEnabled"))
                chain = active_profile.get("fallbackChain") if isinstance(active_profile.get("fallbackChain"), list) else []
                if fallback_enabled and chain:
                    fallback_provider = str(chain[0].get("connectionId") or "").strip()
            except Exception:
                fallback_provider = None
            resolved = maybe_call(registry_mod, "resolve_provider_runtime_profile", registry, provider, capability, fallback_provider)
            if isinstance(resolved, dict):
                printable = {k: v for k, v in resolved.items() if k not in {"provider_entry", "provider_instance"}}
            else:
                printable = resolved
            print(jdump({"capability": capability, "requested_provider": provider, "requested_model": model, "fallback_provider_arg": fallback_provider, "resolved": printable}))

    section("Relevant state files")
    files = find_state_files(root)
    print(jdump([str(path.relative_to(root)) if path.is_relative_to(root) else str(path) for path in files]))
    if args.show_state_files:
        for path in files:
            print("\n---", str(path), "---")
            try:
                parsed = json.loads(path.read_text(encoding="utf-8"))
                print(jdump(redact_json(parsed)))
            except Exception as exc:
                print(f"<could not read JSON: {exc}>")

    section("Static source references to Hugging Face fallback")
    hits = []
    for path in [root / "src", root / "frontend" if (root / "frontend").exists() else root / "frontend_missing"]:
        if not path.exists():
            continue
        for file_path in path.rglob("*"):
            if file_path.suffix.lower() not in {".py", ".ts", ".tsx", ".js", ".jsx", ".json"}:
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if "huggingface_inference" in text or "Hugging Face Inference" in text or "resolve_runtime_fallback" in text:
                rel = str(file_path.relative_to(root)) if file_path.is_relative_to(root) else str(file_path)
                for idx, line in enumerate(text.splitlines(), start=1):
                    if "huggingface_inference" in line or "Hugging Face Inference" in line or "resolve_runtime_fallback" in line:
                        hits.append(f"{rel}:{idx}: {line.strip()[:220]}")
                        if len(hits) >= 120:
                            break
            if len(hits) >= 120:
                break
        if len(hits) >= 120:
            break
    print("\n".join(hits) if hits else "<no references found>")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
