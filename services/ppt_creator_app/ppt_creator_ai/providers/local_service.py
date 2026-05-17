from __future__ import annotations

import json
import os
import time
from urllib import error, request

from ppt_creator_ai.briefing import (
    BriefingInput,
    generate_presentation_payload_from_briefing,
    review_presentation_density,
    suggest_image_queries_from_briefing,
    summarize_text_to_executive_bullets,
)
from ppt_creator_ai.providers.base import BriefingGenerationResult, DeckCritiqueResult
from ppt_creator_ai.structured_generation import DeckTextGenerationAdapter


class LocalServiceBriefingProvider:
    name = "local_service"
    description = "Delegates briefing-to-deck generation to the external persisted hf_local_llm_service over HTTP."
    RETRIABLE_HTTP_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
    DEFAULT_PROVIDER_NAME = "ollama"
    DEFAULT_MODEL_NAME = "nemotron-3-nano:30b-cloud"
    GENERATION_ENDPOINT_CANDIDATES = ("/v1/generate", "/api/generate")

    def __init__(
        self,
        *,
        base_url: str | None = None,
        provider_name: str | None = None,
        model_name: str | None = None,
        generation_attempts: int | None = None,
    ) -> None:
        self._adapter = DeckTextGenerationAdapter()
        self._base_url_override = (base_url or "").strip().rstrip("/") or None
        self._provider_name_override = (provider_name or "").strip().lower() or None
        self._model_name_override = (model_name or "").strip() or None
        self._generation_attempts_override = generation_attempts

    def with_runtime_overrides(self, **runtime_overrides: str | None) -> "LocalServiceBriefingProvider":
        generation_attempts = runtime_overrides.get("generation_attempts")
        return self.__class__(
            base_url=runtime_overrides.get("base_url") or self._base_url_override,
            provider_name=runtime_overrides.get("provider_name") or self._provider_name_override,
            model_name=runtime_overrides.get("model_name") or self._model_name_override,
            generation_attempts=(
                int(str(generation_attempts))
                if generation_attempts not in {None, ""}
                else self._generation_attempts_override
            ),
        )

    def resolve_base_url(self) -> str:
        return (self._base_url_override or os.environ.get("PPT_CREATOR_AI_SERVICE_URL") or "http://127.0.0.1:8788").strip().rstrip("/")

    def resolve_provider_name(self) -> str:
        return (self._provider_name_override or os.environ.get("PPT_CREATOR_AI_SERVICE_PROVIDER") or self.DEFAULT_PROVIDER_NAME).strip().lower()

    def resolve_model_name(self) -> str:
        return (self._model_name_override or os.environ.get("PPT_CREATOR_AI_SERVICE_MODEL") or self.DEFAULT_MODEL_NAME).strip()

    def resolve_provider_source(self) -> str:
        return "environment" if os.environ.get("PPT_CREATOR_AI_SERVICE_PROVIDER") else "app_default"

    def resolve_model_source(self) -> str:
        return "environment" if os.environ.get("PPT_CREATOR_AI_SERVICE_MODEL") else "app_default"

    def resolve_timeout_seconds(self) -> int:
        return int(os.environ.get("PPT_CREATOR_AI_SERVICE_TIMEOUT_SECONDS", "180"))

    def resolve_status_timeout_seconds(self) -> float:
        raw_value = (
            os.environ.get("PPT_CREATOR_AI_SERVICE_STATUS_TIMEOUT_SECONDS")
            or os.environ.get("PPT_CREATOR_AI_STATUS_TIMEOUT_SECONDS")
            or "2.0"
        )
        try:
            return max(0.2, float(raw_value))
        except ValueError:
            return 2.0

    def resolve_retry_attempts(self) -> int:
        return max(1, int(os.environ.get("PPT_CREATOR_AI_SERVICE_RETRY_ATTEMPTS", "2")))

    def resolve_retry_backoff_seconds(self) -> float:
        return max(0.0, float(os.environ.get("PPT_CREATOR_AI_SERVICE_RETRY_BACKOFF_SECONDS", "1.5")))

    def resolve_generation_attempts(self) -> int:
        if self._generation_attempts_override is not None:
            return max(1, int(self._generation_attempts_override))
        return max(1, int(os.environ.get("PPT_CREATOR_AI_GENERATION_ATTEMPTS", "3")))

    def status_payload(self) -> dict[str, object]:
        base_url = self.resolve_base_url()
        health_url = f"{base_url}/health"
        status_timeout_seconds = min(float(self.resolve_timeout_seconds()), self.resolve_status_timeout_seconds())
        health_status = "unknown"
        health_error: str | None = None
        health_payload: dict[str, object] | None = None
        try:
            req = request.Request(health_url, method="GET")
            with request.urlopen(req, timeout=status_timeout_seconds) as response:
                body = response.read().decode("utf-8", errors="replace")
            decoded = json.loads(body)
            health_payload = decoded if isinstance(decoded, dict) else {"raw": body}
            health_status = "ok"
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp is not None else ""
            health_status = "http_error"
            health_error = f"HTTP {exc.code}: {body or exc.reason or exc.msg}"
        except error.URLError as exc:
            health_status = "unreachable"
            health_error = str(exc.reason)
        except Exception as exc:  # noqa: BLE001
            health_status = "error"
            health_error = str(exc)

        return {
            "service_url": base_url,
            "health_url": health_url,
            "provider_name": self.resolve_provider_name(),
            "provider_source": self.resolve_provider_source(),
            "model_name": self.resolve_model_name(),
            "model_source": self.resolve_model_source(),
            "timeout_seconds": self.resolve_timeout_seconds(),
            "status_timeout_seconds": status_timeout_seconds,
            "retry_attempts": self.resolve_retry_attempts(),
            "retry_backoff_seconds": self.resolve_retry_backoff_seconds(),
            "generation_attempts": self.resolve_generation_attempts(),
            "health_status": health_status,
            "health_error": health_error,
            "health_payload": health_payload,
            "supports_model_listing": False,
        }

    def _merge_feedback_messages(self, base: list[str] | None, additions: list[str]) -> list[str]:
        merged: list[str] = list(base or [])
        for item in additions:
            normalized = str(item).strip()
            if normalized and normalized not in merged:
                merged.append(normalized)
        return merged

    def _retry_feedback_messages(self, error_message: str, *, critique_mode: bool = False) -> list[str]:
        messages = [
            f"Previous attempt failed: {error_message}",
            "Retry from scratch and return one complete valid JSON object only.",
            "Do not truncate the JSON and do not omit required slide structures implied by the briefing.",
        ]
        if critique_mode:
            messages.append("Return only a JSON object with the top-level key 'slide_critiques'.")
        else:
            messages.append("Return only a JSON object with top-level keys 'presentation' and 'slides'.")
        return messages

    def _repair_feedback_messages(
        self,
        error_message: str,
        *,
        raw_output: str | None = None,
        critique_mode: bool = False,
    ) -> list[str]:
        messages = self._retry_feedback_messages(error_message, critique_mode=critique_mode)
        messages.extend(
            [
                f"Repair the previous invalid response instead of simplifying the deck away. Validation/parsing failure: {error_message}",
                "Preserve any valid business-specific structure from the previous draft, but return clean schema-valid JSON from the first brace to the final closing brace.",
                "Keep requested evidence-bearing slides such as metrics, chart, comparison, timeline, table or FAQ when the briefing clearly asks for them.",
                "Do not collapse the answer into generic bullets if the briefing asks for richer executive structure.",
            ]
        )
        if raw_output:
            messages.append(
                "The last response contained a draft that may have partially worked. Use it only as a draft and rewrite it into one complete valid JSON object now."
            )
        return messages

    def _extract_error_details(self, payload: object) -> tuple[str | None, str | None, bool | None]:
        if not isinstance(payload, dict):
            return None, None, None

        error_payload = payload.get("error")
        if isinstance(error_payload, dict):
            message = (
                str(
                    error_payload.get("message")
                    or error_payload.get("detail")
                    or error_payload.get("error")
                    or ""
                ).strip()
                or None
            )
            code = str(error_payload.get("code")).strip() if error_payload.get("code") else None
            retriable = bool(error_payload["retriable"]) if "retriable" in error_payload else None
            return message, code, retriable

        if error_payload:
            return str(error_payload).strip() or None, None, None

        message = str(payload.get("message")).strip() if payload.get("message") else None
        code = str(payload.get("code")).strip() if payload.get("code") else None
        retriable = bool(payload["retriable"]) if "retriable" in payload else None
        return message, code, retriable

    def _format_service_error(
        self,
        *,
        base_url: str,
        path: str,
        status_code: int | None = None,
        code: str | None = None,
        message: str | None = None,
        retriable: bool | None = None,
        fallback_message: str,
    ) -> str:
        parts = [f"hf_local_llm_service request to {base_url}{path} failed"]
        if status_code is not None:
            parts.append(f"HTTP {status_code}")
        if code:
            parts.append(code)
        detail = message or fallback_message
        formatted = " • ".join(parts)
        if detail:
            formatted = f"{formatted}: {detail}"
        if retriable is not None:
            formatted = f"{formatted} (retriable={str(retriable).lower()})"
        return formatted

    def _sleep_before_retry(self, attempt: int) -> None:
        delay = self.resolve_retry_backoff_seconds() * attempt
        if delay > 0:
            time.sleep(delay)

    def _request_json(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        base_url = self.resolve_base_url()
        attempts = self.resolve_retry_attempts()

        for attempt in range(1, attempts + 1):
            req = request.Request(
                f"{base_url}{path}",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with request.urlopen(req, timeout=self.resolve_timeout_seconds()) as response:
                    body = response.read().decode("utf-8", errors="replace")
            except error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace") if exc.fp is not None else ""
                parsed_payload: dict[str, object] | None = None
                if body.strip():
                    try:
                        decoded = json.loads(body)
                    except json.JSONDecodeError:
                        decoded = None
                    if isinstance(decoded, dict):
                        parsed_payload = decoded
                message, code, retriable_hint = self._extract_error_details(parsed_payload or {})
                retriable = retriable_hint if retriable_hint is not None else exc.code in self.RETRIABLE_HTTP_STATUS_CODES
                runtime_error = RuntimeError(
                    self._format_service_error(
                        base_url=base_url,
                        path=path,
                        status_code=exc.code,
                        code=code,
                        message=message,
                        retriable=retriable,
                        fallback_message=exc.reason or exc.msg or "HTTP error",
                    )
                )
                if retriable and attempt < attempts:
                    self._sleep_before_retry(attempt)
                    continue
                raise runtime_error from exc
            except error.URLError as exc:
                runtime_error = RuntimeError(
                    f"Could not reach hf_local_llm_service at {base_url}{path} after {attempt} attempt(s). "
                    f"Start the local persisted service first. Details: {exc.reason}"
                )
                if attempt < attempts:
                    self._sleep_before_retry(attempt)
                    continue
                raise runtime_error from exc

            try:
                response_payload = json.loads(body)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"hf_local_llm_service returned invalid JSON: {exc.msg}") from exc

            if not isinstance(response_payload, dict):
                raise RuntimeError("hf_local_llm_service returned a non-object JSON response")
            if response_payload.get("error"):
                message, code, retriable = self._extract_error_details(response_payload)
                runtime_error = RuntimeError(
                    self._format_service_error(
                        base_url=base_url,
                        path=path,
                        status_code=None,
                        code=code,
                        message=message,
                        retriable=retriable,
                        fallback_message="service returned an application error payload",
                    )
                )
                if retriable and attempt < attempts:
                    self._sleep_before_retry(attempt)
                    continue
                raise runtime_error
            return response_payload

        raise RuntimeError(f"hf_local_llm_service request to {base_url}{path} failed after {attempts} attempt(s)")

    def _append_feedback_messages(self, prompt: str, feedback_messages: list[str] | None, *, label: str) -> str:
        if feedback_messages:
            return prompt + f"\n\n{label}:\n- " + "\n- ".join(feedback_messages)
        return prompt

    def _build_ai_exchange(
        self,
        *,
        request_path: str,
        request_payload: dict[str, object],
        response_payload: dict[str, object],
        raw_response: str | None,
    ) -> dict[str, object]:
        return {
            "kind": "external_ai_roundtrip",
            "transport": self.name,
            "target_url": f"{self.resolve_base_url()}{request_path}",
            "request_payload": request_payload,
            "prompt": str(request_payload.get("prompt") or ""),
            "response_payload": response_payload,
            "raw_response": raw_response,
        }

    def _request_json_with_fallback(
        self,
        paths: tuple[str, ...] | list[str],
        payload: dict[str, object],
    ) -> tuple[str, dict[str, object]]:
        last_error: RuntimeError | None = None
        for index, path in enumerate(paths):
            try:
                return path, self._request_json(path, payload)
            except RuntimeError as exc:
                last_error = exc
                is_not_found = "HTTP 404" in str(exc)
                has_more_candidates = index < len(paths) - 1
                if is_not_found and has_more_candidates:
                    continue
                raise
        if last_error is not None:
            raise last_error
        raise RuntimeError("hf_local_llm_service request failed before any endpoint candidate was attempted")

    def _request_generation_round(self, prompt: str) -> tuple[dict[str, object], dict[str, object], str | None]:
        request_payload = {
            "provider_name": self.resolve_provider_name(),
            "model_name": self.resolve_model_name(),
            "prompt": prompt,
        }
        request_path, payload = self._request_json_with_fallback(self.GENERATION_ENDPOINT_CANDIDATES, request_payload)
        raw_output = str(payload.get("response") or "") or None
        ai_exchange = self._build_ai_exchange(
            request_path=request_path,
            request_payload=request_payload,
            response_payload=payload,
            raw_response=raw_output,
        )
        return payload, ai_exchange, raw_output

    def _parse_generation_payload(
        self,
        payload: dict[str, object],
        *,
        raw_output: str | None,
        prompt: str,
        briefing: BriefingInput,
        theme_name: str | None = None,
        fallback_payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        if payload.get("payload"):
            provided_payload = dict(payload.get("payload") or {})
            spec, _, _ = self._adapter.validate_generated_payload(
                provided_payload,
                briefing,
                theme_name=theme_name,
                fallback_payload=fallback_payload,
            )
            return spec.model_dump(mode="json")

        extracted_payload = self._adapter.extract_json_payload(raw_output or "", prompt=prompt)
        normalized_payload = self._adapter.normalize_generated_payload(
            extracted_payload,
            briefing,
            theme_name=theme_name,
        )
        spec, _, _ = self._adapter.validate_generated_payload(
            normalized_payload,
            briefing,
            theme_name=theme_name,
            fallback_payload=fallback_payload,
        )
        return spec.model_dump(mode="json")

    def _parse_critique_payload(
        self,
        payload: dict[str, object],
        *,
        raw_output: str | None,
        prompt: str,
        slide_critiques: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        if payload.get("critiques"):
            critiques = [item for item in (payload.get("critiques") or []) if isinstance(item, dict)]
            if critiques:
                return critiques
            raise ValueError("Provider returned an empty critique list")

        return self._adapter.normalize_slide_critiques(
            self._adapter.extract_slide_critiques_payload(raw_output or "", prompt=prompt),
            fallback_slide_critiques=slide_critiques,
        )

    def _enrich_analysis_from_transport(
        self,
        analysis: dict[str, object],
        response_payload: dict[str, object],
    ) -> dict[str, object]:
        analysis.setdefault("transport_provider", self.name)
        analysis.setdefault("backend_provider", str(response_payload.get("provider_name") or self.resolve_provider_name()))
        analysis.setdefault("base_url", self.resolve_base_url())
        resolved_model = response_payload.get("resolved_model") or response_payload.get("model")
        if resolved_model:
            analysis.setdefault("resolved_model", resolved_model)
        if response_payload.get("matched_registry_entry"):
            analysis.setdefault("matched_registry_entry", response_payload.get("matched_registry_entry"))
        if response_payload.get("provider_config"):
            analysis.setdefault("provider_config", response_payload.get("provider_config"))
        if response_payload.get("request_metrics"):
            analysis.setdefault("request_metrics", response_payload.get("request_metrics"))
        return analysis

    def _build_generation_analysis(
        self,
        *,
        briefing: BriefingInput,
        spec_payload: dict[str, object],
        feedback_messages: list[str] | None,
        response_payload: dict[str, object],
        fallback_used: bool,
        fallback_reason: str | None,
    ) -> dict[str, object]:
        from ppt_creator.schema import PresentationInput

        spec = PresentationInput.model_validate(spec_payload)
        summary_source = " ".join(
            filter(
                None,
                [briefing.objective, briefing.context, *briefing.key_messages[:3], *briefing.recommendations[:3]],
            )
        )
        analysis = {
            "briefing_title": briefing.title,
            "provider": str(response_payload.get("provider_name") or self.resolve_provider_name()),
            "theme": spec.presentation.theme,
            "generated_slide_count": len(spec.slides),
            "feedback_messages": feedback_messages or [],
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "repair_loop_used": False,
            "repair_attempt_count": 0,
            "executive_summary_bullets": briefing.recommendations[:3]
            or summarize_text_to_executive_bullets(summary_source, max_bullets=3),
            "image_suggestions": suggest_image_queries_from_briefing(briefing),
            "density_review": review_presentation_density(spec),
        }
        return self._enrich_analysis_from_transport(analysis, response_payload)

    def _build_fallback_generation_result(
        self,
        *,
        briefing: BriefingInput,
        theme_name: str | None,
        feedback_messages: list[str] | None,
        response_payload: dict[str, object],
        ai_exchange: dict[str, object] | None,
        fallback_reason: str,
        generation_attempts: int,
    ) -> BriefingGenerationResult:
        fallback_payload = generate_presentation_payload_from_briefing(
            briefing,
            theme_name=theme_name,
            feedback_messages=feedback_messages,
        )
        analysis = self._build_generation_analysis(
            briefing=briefing,
            spec_payload=fallback_payload,
            feedback_messages=feedback_messages,
            response_payload=response_payload,
            fallback_used=True,
            fallback_reason=fallback_reason,
        )
        analysis["generation_attempts"] = generation_attempts
        analysis["retry_count"] = max(0, generation_attempts - 1)
        analysis["repair_loop_used"] = generation_attempts > 1
        analysis["repair_attempt_count"] = max(0, generation_attempts - 1)
        if ai_exchange is not None:
            analysis["ai_exchange"] = ai_exchange
        return BriefingGenerationResult(
            provider_name=str(response_payload.get("provider_name") or self.resolve_provider_name()),
            payload=fallback_payload,
            analysis=analysis,
        )

    def _build_revision_analysis(
        self,
        *,
        briefing: BriefingInput,
        spec_payload: dict[str, object],
        review: dict[str, object],
        slide_critiques: list[dict[str, object]],
        feedback_messages: list[str] | None,
        response_payload: dict[str, object],
        fallback_used: bool,
        fallback_reason: str | None,
    ) -> dict[str, object]:
        from ppt_creator.schema import PresentationInput

        spec = PresentationInput.model_validate(spec_payload)
        analysis = {
            "briefing_title": briefing.title,
            "provider": str(response_payload.get("provider_name") or self.resolve_provider_name()),
            "theme": spec.presentation.theme,
            "generated_slide_count": len(spec.slides),
            "feedback_messages": feedback_messages or [],
            "revision_mode": "llm_review",
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "repair_loop_used": False,
            "repair_attempt_count": 0,
            "source_issue_count": review.get("issue_count"),
            "slide_critique_count": len(slide_critiques),
            "density_review": review_presentation_density(spec),
        }
        return self._enrich_analysis_from_transport(analysis, response_payload)

    def _build_critique_analysis(
        self,
        *,
        feedback_messages: list[str] | None,
        response_payload: dict[str, object],
        fallback_used: bool,
        critiques: list[dict[str, object]],
    ) -> dict[str, object]:
        analysis = {
            "provider": str(response_payload.get("provider_name") or self.resolve_provider_name()),
            "critique_mode": "llm_slide_critique",
            "feedback_messages": feedback_messages or [],
            "fallback_used": fallback_used,
            "repair_loop_used": False,
            "repair_attempt_count": 0,
            "critique_count": len(critiques),
        }
        return self._enrich_analysis_from_transport(analysis, response_payload)

    def generate(
        self,
        briefing: BriefingInput,
        *,
        theme_name: str | None = None,
        feedback_messages: list[str] | None = None,
    ) -> BriefingGenerationResult:
        combined_feedback = list(feedback_messages or [])
        last_error: Exception | None = None
        last_payload: dict[str, object] = {}
        last_ai_exchange: dict[str, object] | None = None
        attempts = self.resolve_generation_attempts()
        for attempt in range(1, attempts + 1):
            prompt = self._append_feedback_messages(
                self._adapter.build_prompt(briefing, theme_name=theme_name),
                combined_feedback,
                label="Additional regeneration guidance",
            )
            payload, ai_exchange, raw_output = self._request_generation_round(prompt)
            last_payload = payload
            last_ai_exchange = ai_exchange
            try:
                normalized_spec_payload = self._parse_generation_payload(
                    payload,
                    raw_output=raw_output,
                    prompt=prompt,
                    briefing=briefing,
                    theme_name=theme_name,
                )
            except Exception as exc:
                last_error = exc
                if attempt >= attempts:
                    break
                combined_feedback = self._merge_feedback_messages(
                    combined_feedback,
                    self._repair_feedback_messages(str(exc), raw_output=raw_output),
                )
                continue

            analysis = self._build_generation_analysis(
                briefing=briefing,
                spec_payload=normalized_spec_payload,
                feedback_messages=combined_feedback,
                response_payload=payload,
                fallback_used=False,
                fallback_reason=None,
            )
            analysis["generation_attempts"] = attempt
            analysis["retry_count"] = attempt - 1
            analysis["repair_loop_used"] = attempt > 1
            analysis["repair_attempt_count"] = max(0, attempt - 1)
            analysis["ai_exchange"] = ai_exchange
            return BriefingGenerationResult(
                provider_name=str(payload.get("provider_name") or self.name),
                payload=normalized_spec_payload,
                analysis=analysis,
            )
        if last_error is None:
            raise RuntimeError("Model-backed generation failed without a recoverable fallback reason")
        return self._build_fallback_generation_result(
            briefing=briefing,
            theme_name=theme_name,
            feedback_messages=combined_feedback,
            response_payload=last_payload,
            ai_exchange=last_ai_exchange,
            fallback_reason=f"Model-backed generation failed after {attempts} attempt(s): {last_error}",
            generation_attempts=attempts,
        )

    def revise_generated_deck(
        self,
        briefing: BriefingInput,
        current_payload: dict[str, object],
        review: dict[str, object],
        slide_critiques: list[dict[str, object]],
        *,
        theme_name: str | None = None,
        feedback_messages: list[str] | None = None,
    ) -> BriefingGenerationResult:
        combined_feedback = list(feedback_messages or [])
        last_error: Exception | None = None
        attempts = self.resolve_generation_attempts()
        for attempt in range(1, attempts + 1):
            prompt = self._adapter.build_revision_prompt(
                briefing,
                current_payload,
                review,
                slide_critiques,
                theme_name=theme_name,
                feedback_messages=combined_feedback,
            )
            payload, ai_exchange, raw_output = self._request_generation_round(prompt)
            try:
                normalized_spec_payload = self._parse_generation_payload(
                    payload,
                    raw_output=raw_output,
                    prompt=prompt,
                    briefing=briefing,
                    theme_name=theme_name,
                    fallback_payload=current_payload,
                )
            except Exception as exc:
                last_error = exc
                if attempt >= attempts:
                    raise RuntimeError(
                        f"Model-backed revision failed after {attempts} attempt(s): {exc}"
                    ) from exc
                combined_feedback = self._merge_feedback_messages(
                    combined_feedback,
                    self._repair_feedback_messages(str(exc), raw_output=raw_output),
                )
                continue

            analysis = self._build_revision_analysis(
                briefing=briefing,
                spec_payload=normalized_spec_payload,
                review=review,
                slide_critiques=slide_critiques,
                feedback_messages=combined_feedback,
                response_payload=payload,
                fallback_used=False,
                fallback_reason=None,
            )
            analysis["generation_attempts"] = attempt
            analysis["retry_count"] = attempt - 1
            analysis["repair_loop_used"] = attempt > 1
            analysis["repair_attempt_count"] = max(0, attempt - 1)
            analysis["ai_exchange"] = ai_exchange
            return BriefingGenerationResult(
                provider_name=str(payload.get("provider_name") or self.name),
                payload=normalized_spec_payload,
                analysis=analysis,
            )

        raise RuntimeError(f"Model-backed revision failed: {last_error}")

    def critique_generated_deck(
        self,
        briefing: BriefingInput,
        current_payload: dict[str, object],
        review: dict[str, object],
        slide_critiques: list[dict[str, object]],
        *,
        theme_name: str | None = None,
        feedback_messages: list[str] | None = None,
    ) -> DeckCritiqueResult:
        combined_feedback = list(feedback_messages or [])
        last_error: Exception | None = None
        attempts = self.resolve_generation_attempts()
        for attempt in range(1, attempts + 1):
            prompt = self._adapter.build_critique_prompt(
                briefing,
                current_payload,
                review,
                slide_critiques,
                theme_name=theme_name,
                feedback_messages=combined_feedback,
            )
            payload, ai_exchange, raw_output = self._request_generation_round(prompt)
            try:
                critiques = self._parse_critique_payload(
                    payload,
                    raw_output=raw_output,
                    prompt=prompt,
                    slide_critiques=slide_critiques,
                )
            except Exception as exc:
                last_error = exc
                if attempt >= attempts:
                    raise RuntimeError(
                        f"Model-backed critique failed after {attempts} attempt(s): {exc}"
                    ) from exc
                combined_feedback = self._merge_feedback_messages(
                    combined_feedback,
                    self._repair_feedback_messages(str(exc), raw_output=raw_output, critique_mode=True),
                )
                continue

            analysis = self._build_critique_analysis(
                feedback_messages=combined_feedback,
                response_payload=payload,
                fallback_used=False,
                critiques=critiques,
            )
            analysis["generation_attempts"] = attempt
            analysis["retry_count"] = attempt - 1
            analysis["repair_loop_used"] = attempt > 1
            analysis["repair_attempt_count"] = max(0, attempt - 1)
            analysis["ai_exchange"] = ai_exchange
            return DeckCritiqueResult(
                provider_name=str(payload.get("provider_name") or self.name),
                critiques=critiques,
                analysis=analysis,
            )

        raise RuntimeError(f"Model-backed critique failed: {last_error}")