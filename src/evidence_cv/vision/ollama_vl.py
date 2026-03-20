from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from urllib import request as urllib_request

from ..config import EvidencePipelineConfig


class OllamaVLBackend:
    def __init__(self, config: EvidencePipelineConfig) -> None:
        self.config = config

    def inspect_image(self, image_path: Path, prompt: str) -> dict:
        image_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        payload = {
            "model": self.config.vl_model,
            "messages": [{"role": "user", "content": prompt, "images": [image_b64]}],
            "stream": False,
        }
        req = urllib_request.Request(
            url=f"{self.config.ollama_base_url.rstrip('/')}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib_request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def extract_contact_candidates(self, image_path: Path) -> dict[str, object]:
        prompt = (
            "You are an evidence extraction assistant for CVs. "
            "Read only what is visually present in this resume region. "
            "Do not guess. Return JSON only with keys: name, emails, phones, location, notes. "
            "For each field, only include values explicitly visible. If not visible, return null or empty list."
        )
        response = self.inspect_image(image_path, prompt)
        content = ((response.get("message") or {}).get("content") or "").strip()
        try:
            return json.loads(content)
        except Exception:
            match = re.search(r"\{.*\}", content, re.S)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
        return {"name": None, "emails": [], "phones": [], "location": None, "notes": content[:500] if content else None}

    def extract_contact_candidates_from_region(self, image_path: Path, region_label: str) -> dict[str, object]:
        prompt = (
            "You are an evidence extraction assistant for CVs. "
            f"This image is a cropped region from a resume: {region_label}. "
            "Extract only explicitly visible contact/header information. "
            "Return JSON only with keys: name, emails, phones, location, notes. "
            "Do not infer missing values."
        )
        response = self.inspect_image(image_path, prompt)
        content = ((response.get("message") or {}).get("content") or "").strip()
        try:
            return json.loads(content)
        except Exception:
            match = re.search(r"\{.*\}", content, re.S)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
        return {"name": None, "emails": [], "phones": [], "location": None, "notes": content[:500] if content else None}