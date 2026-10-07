"""Ollama / Qwen3 LLM Provider Implementation for VERA."""

import json
from typing import Any, TypeVar
from uuid import UUID

import httpx
from pydantic import BaseModel, ValidationError

from app.contracts.status import AnalysisStatus
from app.core.errors import LLMGenerationError, ProviderUnavailableError
from app.core.logging import get_logger
from app.providers.llm import LLMProvider

logger = get_logger("app.providers.ollama")

T = TypeVar("T", bound=BaseModel)


class OllamaLLMProvider(LLMProvider):
    """LLM Provider interfacing with local or networked Ollama instance."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen3:8b",
        timeout_seconds: float = 60.0,
        temperature: float = 0.1,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self._provider_name = f"ollama:{self.model}"

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def is_available(self) -> bool:
        """Lightweight synchronous check property."""
        return True

    async def health_check(self) -> dict[str, Any]:
        """Probes the Ollama endpoint and verifies that the model is present."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")

                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    model_found = any(self.model in m for m in models)

                    return {
                        "status": (
                            AnalysisStatus.SUCCESS.value
                            if model_found
                            else AnalysisStatus.PARTIAL.value
                        ),
                        "provider": self.provider_name,
                        "base_url": self.base_url,
                        "model": self.model,
                        "model_loaded": model_found,
                        "available_models": models,
                        "message": (
                            "Ollama service connected successfully."
                            if model_found
                            else (
                                f"Ollama reachable, but model "
                                f"'{self.model}' not yet pulled."
                            )
                        ),
                    }

                return {
                    "status": AnalysisStatus.UNAVAILABLE.value,
                    "provider": self.provider_name,
                    "message": f"Ollama returned status {resp.status_code}",
                }

        except (
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.NetworkError,
            httpx.ReadError,
            httpx.RemoteProtocolError,
            OSError,
        ) as exc:
            logger.warning(
                f"Ollama server unreachable at {self.base_url}: {exc}"
            )
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "message": f"Cannot connect to Ollama at {self.base_url}",
            }

        except Exception as exc:
            error_text = str(exc)

            if (
                "TaskGroup" in error_text
                or "ConnectError" in error_text
                or "Connection refused" in error_text
                or "All connection attempts failed" in error_text
                or "port must be 0-65535" in error_text
            ):
                logger.warning(
                    f"Ollama server unreachable at {self.base_url}: {exc}"
                )
                return {
                    "status": AnalysisStatus.UNAVAILABLE.value,
                    "provider": self.provider_name,
                    "message": f"Cannot connect to Ollama at {self.base_url}",
                }

            logger.warning(f"Ollama health check error: {exc}")
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "message": error_text,
            }

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Sends chat request to Ollama /api/chat."""
        temp = self.temperature if temperature is None else temperature

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temp},
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds
            ) as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )

                if resp.status_code != 200:
                    logger.error(
                        f"Ollama chat error HTTP "
                        f"{resp.status_code}: {resp.text}"
                    )
                    return {
                        "status": AnalysisStatus.FAILED.value,
                        "provider": self.provider_name,
                        "error": (
                            f"Ollama returned HTTP {resp.status_code}"
                        ),
                        "response": None,
                    }

                data = resp.json()
                content = data.get("message", {}).get("content", "")

                return {
                    "status": AnalysisStatus.SUCCESS.value,
                    "provider": self.provider_name,
                    "response": content,
                    "total_duration": data.get("total_duration"),
                }

        except (
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.NetworkError,
            httpx.ReadError,
            httpx.RemoteProtocolError,
            OSError,
        ) as exc:
            logger.warning(
                f"Ollama unavailable during chat: {exc}"
            )
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "error": f"Ollama unavailable at {self.base_url}",
                "response": None,
            }

        except httpx.TimeoutException as exc:
            logger.warning(f"Ollama chat timeout: {exc}")
            return {
                "status": AnalysisStatus.FAILED.value,
                "provider": self.provider_name,
                "error": (
                    f"Ollama request timed out after "
                    f"{self.timeout_seconds}s"
                ),
                "response": None,
            }

        except Exception as exc:
            error_text = str(exc)

            if (
                "TaskGroup" in error_text
                or "ConnectError" in error_text
                or "Connection refused" in error_text
                or "All connection attempts failed" in error_text
                or "port must be 0-65535" in error_text
            ):
                logger.warning(
                    f"Ollama unavailable during chat: {exc}"
                )
                return {
                    "status": AnalysisStatus.UNAVAILABLE.value,
                    "provider": self.provider_name,
                    "error": f"Ollama unavailable at {self.base_url}",
                    "response": None,
                }

            logger.error(
                f"Ollama chat unexpected error: {exc}"
            )
            return {
                "status": AnalysisStatus.FAILED.value,
                "provider": self.provider_name,
                "error": error_text,
                "response": None,
            }

    async def generate_structured(
        self,
        schema: type[T],
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> T:
        """Generates Pydantic structured output from Ollama using JSON schema enforcement."""
        temp = self.temperature if temperature is None else temperature

        messages: list[dict[str, str]] = []

        if system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": system_prompt,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        json_schema = schema.model_json_schema()

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": json_schema,
            "options": {"temperature": temp},
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds
            ) as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )

                if resp.status_code != 200:
                    raise LLMGenerationError(
                        (
                            f"Ollama returned HTTP "
                            f"{resp.status_code} during structured "
                            f"generation"
                        ),
                        details={"response": resp.text},
                    )

                data = resp.json()
                raw_content = data.get(
                    "message",
                    {},
                ).get(
                    "content",
                    "",
                )

                if not raw_content:
                    raise LLMGenerationError(
                        "Ollama returned empty message content."
                    )

        except (
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.NetworkError,
            httpx.ReadError,
            httpx.RemoteProtocolError,
            OSError,
        ) as exc:
            raise ProviderUnavailableError(
                self.provider_name,
                details={
                    "reason": (
                        f"Ollama unavailable at "
                        f"{self.base_url}: {exc}"
                    )
                },
            ) from exc

        except httpx.TimeoutException as exc:
            raise LLMGenerationError(
                (
                    f"Ollama structured generation timed out "
                    f"after {self.timeout_seconds}s"
                )
            ) from exc

        except Exception as exc:
            error_text = str(exc)

            if (
                "TaskGroup" in error_text
                or "ConnectError" in error_text
                or "Connection refused" in error_text
                or "All connection attempts failed" in error_text
                or "port must be 0-65535" in error_text
            ):
                raise ProviderUnavailableError(
                    self.provider_name,
                    details={
                        "reason": (
                            f"Ollama unavailable at "
                            f"{self.base_url}"
                        )
                    },
                ) from exc

            raise

        try:
            # Parse and validate with Pydantic.
            return schema.model_validate_json(raw_content)

        except (ValidationError, json.JSONDecodeError) as err:
            logger.warning(
                "Raw Ollama output failed Pydantic validation: "
                f"{err}. Raw: {raw_content[:200]}"
            )

            # Attempt to extract JSON substring if extra markdown
            # or reasoning tokens wrapped it.
            cleaned = self._clean_json_substring(raw_content)

            try:
                return schema.model_validate_json(cleaned)

            except Exception as final_err:
                raise LLMGenerationError(
                    (
                        f"Model output did not match required schema "
                        f"'{schema.__name__}': {final_err}"
                    ),
                    details={
                        "raw_output": raw_content[:500]
                    },
                ) from final_err

    @staticmethod
    def _clean_json_substring(text: str) -> str:
        """Extracts JSON substring if enclosed in markdown code fences or surrounded by text."""
        text = text.strip()

        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1 and end > start:
            return text[start : end + 1]

        return text

    async def analyze_fraud_claim(
        self,
        investigation_id: UUID,
        claim_text: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Analyzes a specific claim for fraud indicators."""
        prompt = (
            "Analyze this financial or investment claim for fraud "
            "indicators:\n"
            f"Claim: {claim_text}\n"
            f"Context: {json.dumps(context or {})}\n"
            "Provide an objective analysis stating whether known "
            "indicators appear."
        )

        chat_res = await self.chat(
            [{"role": "user", "content": prompt}]
        )

        if chat_res.get("status") != AnalysisStatus.SUCCESS.value:
            return {
                "status": chat_res.get(
                    "status",
                    AnalysisStatus.FAILED.value,
                ),
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "error": chat_res.get(
                    "error",
                    "Failed claim analysis",
                ),
                "evidence": None,
            }

        return {
            "status": AnalysisStatus.SUCCESS.value,
            "provider": self.provider_name,
            "investigation_id": str(investigation_id),
            "claim": claim_text,
            "analysis": chat_res.get("response"),
        }