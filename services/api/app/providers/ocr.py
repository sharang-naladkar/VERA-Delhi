"""OCR Provider Interface, PaddleOCR, Mock, and Unavailable Fallbacks."""

import io
import time
from abc import abstractmethod
from typing import Any
from uuid import UUID

from app.contracts.status import AnalysisStatus
from app.core.logging import get_logger
from app.providers.base import BaseProvider

logger = get_logger("app.providers.ocr")


class OCRProvider(BaseProvider):
    """Interface for OCR document/screenshot text extraction."""

    @abstractmethod
    async def extract_text(
        self,
        investigation_id: UUID,
        image_bytes: bytes,
        filename: str | None = None,
    ) -> dict[str, Any]:
        """Extract text and bounding metadata from an image."""
        pass


class PaddleOCRProvider(OCRProvider):
    """
    PaddleOCR concrete provider for forensic text extraction.
    Loads lazily and handles missing dependencies gracefully without crashing.
    """

    def __init__(self, lang: str = "en", use_angle_cls: bool = True) -> None:
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self._ocr_engine: Any = None
        self._is_initialized = False
        self._init_error: str | None = None

    @property
    def provider_name(self) -> str:
        return "paddleocr"

    @property
    def is_available(self) -> bool:
        if not self._is_initialized:
            self._try_init()
        return self._ocr_engine is not None and self._init_error is None

    def _try_init(self) -> None:
        """Lazy initialization of PaddleOCR."""
        self._is_initialized = True
        try:
            from paddleocr import PaddleOCR  # type: ignore

            self._ocr_engine = PaddleOCR(
                use_angle_cls=self.use_angle_cls,
                lang=self.lang,
                show_log=False,
            )
            self._init_error = None
        except Exception as exc:
            self._ocr_engine = None
            self._init_error = f"PaddleOCR unavailable: {exc}"
            logger.warning(f"Failed to initialize PaddleOCR engine: {exc}")

    async def health_check(self) -> dict[str, Any]:
        if not self.is_available:
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "message": self._init_error or "PaddleOCR engine is not installed or available.",
            }
        return {
            "status": AnalysisStatus.SUCCESS.value,
            "provider": self.provider_name,
            "message": "PaddleOCR is ready.",
        }

    async def extract_text(
        self,
        investigation_id: UUID,
        image_bytes: bytes,
        filename: str | None = None,
    ) -> dict[str, Any]:
        start_time = time.perf_counter()
        if not self.is_available:
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "text": "",
                "blocks": [],
                "error": self._init_error or "PaddleOCR dependency is not installed.",
                "duration_ms": round((time.perf_counter() - start_time) * 1000, 2),
            }

        if not image_bytes:
            return {
                "status": AnalysisStatus.INSUFFICIENT_EVIDENCE.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "text": "",
                "blocks": [],
                "error": "Empty image bytes provided.",
                "duration_ms": round((time.perf_counter() - start_time) * 1000, 2),
            }

        try:
            import numpy as np
            from PIL import Image

            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_np = np.array(image)

            result = self._ocr_engine.ocr(img_np, cls=self.use_angle_cls)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            blocks: list[dict[str, Any]] = []
            extracted_lines: list[str] = []
            total_confidence = 0.0

            if result and result[0]:
                for line in result[0]:
                    box = line[0]  # [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                    text, conf = line[1]
                    extracted_lines.append(text)
                    total_confidence += float(conf)
                    blocks.append({
                        "box": box,
                        "text": text,
                        "confidence": round(float(conf), 4),
                    })

            full_text = "\n".join(extracted_lines).strip()
            avg_confidence = round(total_confidence / len(blocks), 4) if blocks else 0.0

            if not full_text:
                return {
                    "status": AnalysisStatus.INSUFFICIENT_EVIDENCE.value,
                    "provider": self.provider_name,
                    "investigation_id": str(investigation_id),
                    "text": "",
                    "blocks": [],
                    "language": self.lang,
                    "duration_ms": duration_ms,
                    "metadata": {"line_count": 0, "avg_confidence": 0.0},
                }

            return {
                "status": AnalysisStatus.SUCCESS.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "text": full_text,
                "blocks": blocks,
                "language": self.lang,
                "confidence": avg_confidence,
                "duration_ms": duration_ms,
                "metadata": {
                    "line_count": len(blocks),
                    "filename": filename,
                    "avg_confidence": avg_confidence,
                },
            }
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Error during PaddleOCR text extraction: {exc}", exc_info=True)
            return {
                "status": AnalysisStatus.FAILED.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "text": "",
                "blocks": [],
                "error": f"OCR extraction error: {exc}",
                "duration_ms": duration_ms,
            }


class MockOCRProvider(OCRProvider):
    """Deterministic Mock OCR provider for unit tests and local mock scenarios."""

    def __init__(
        self,
        mock_text: str = "Guaranteed 100% daily returns on SEBI registered VIP trading group",
        mock_status: AnalysisStatus = AnalysisStatus.SUCCESS,
        mock_confidence: float = 0.95,
        mock_blocks: list[dict[str, Any]] | None = None,
    ) -> None:
        self.mock_text = mock_text
        self.mock_status = mock_status
        self.mock_confidence = mock_confidence
        self.mock_blocks = mock_blocks or [
            {
                "box": [[10, 10], [200, 10], [200, 30], [10, 30]],
                "text": mock_text,
                "confidence": mock_confidence,
            }
        ]

    @property
    def provider_name(self) -> str:
        return "mock_ocr"

    @property
    def is_available(self) -> bool:
        return self.mock_status != AnalysisStatus.UNAVAILABLE

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": self.mock_status.value,
            "provider": self.provider_name,
            "message": "Mock OCR provider active.",
        }

    async def extract_text(
        self,
        investigation_id: UUID,
        image_bytes: bytes,
        filename: str | None = None,
    ) -> dict[str, Any]:
        if self.mock_status == AnalysisStatus.UNAVAILABLE:
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "text": "",
                "blocks": [],
                "error": "Mock OCR provider configured as unavailable.",
            }

        if self.mock_status == AnalysisStatus.FAILED:
            return {
                "status": AnalysisStatus.FAILED.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "text": "",
                "blocks": [],
                "error": "Simulated mock OCR failure.",
            }

        if not self.mock_text.strip() or self.mock_status == AnalysisStatus.INSUFFICIENT_EVIDENCE:
            return {
                "status": AnalysisStatus.INSUFFICIENT_EVIDENCE.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "text": "",
                "blocks": [],
                "confidence": 0.0,
                "metadata": {"line_count": 0},
            }

        return {
            "status": AnalysisStatus.SUCCESS.value,
            "provider": self.provider_name,
            "investigation_id": str(investigation_id),
            "text": self.mock_text,
            "blocks": self.mock_blocks,
            "confidence": self.mock_confidence,
            "language": "en",
            "metadata": {
                "line_count": len(self.mock_blocks),
                "filename": filename,
                "is_mock": True,
            },
        }


class UnavailableOCRProvider(OCRProvider):
    """Fail-safe placeholder for OCR provider."""

    @property
    def provider_name(self) -> str:
        return "unavailable_ocr"

    @property
    def is_available(self) -> bool:
        return False

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "message": "OCR engine is not configured in Phase 01.",
        }

    async def extract_text(
        self,
        investigation_id: UUID,
        image_bytes: bytes,
        filename: str | None = None,
    ) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "investigation_id": str(investigation_id),
            "text": "",
            "blocks": [],
            "error": "OCR provider is unavailable.",
        }
