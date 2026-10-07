"""Face Detector Provider Interface, OpenCV Implementation, Mock, and Unavailable Fallbacks."""

import os
import time
from abc import abstractmethod
from typing import Any
from uuid import UUID

from app.contracts.status import AnalysisStatus
from app.core.logging import get_logger
from app.providers.base import BaseProvider

logger = get_logger("app.providers.face_detector")


class FaceDetectorProvider(BaseProvider):
    """Interface for local face detection providers."""

    @abstractmethod
    async def detect_faces(
        self,
        investigation_id: UUID,
        image_bytes: bytes,
    ) -> dict[str, Any]:
        """Detect faces within an image and return bounding boxes."""
        pass


class OpenCVFaceDetectorProvider(FaceDetectorProvider):
    """
    Local face detection using OpenCV's built-in Haar cascades.

    Completely offline, requires no external model downloads,
    and runs quickly on CPU.
    """

    def __init__(self, cascade_path: str | None = None) -> None:
        self._cascade_path = cascade_path
        self._classifier: Any = None
        self._is_initialized = False
        self._init_error: str | None = None

    @property
    def provider_name(self) -> str:
        return "opencv_face_detector"

    @property
    def is_available(self) -> bool:
        if not self._is_initialized:
            self._try_init()

        return (
            self._classifier is not None
            and self._init_error is None
        )

    def _try_init(self) -> None:
        """Initialize the OpenCV Haar cascade detector."""
        self._is_initialized = True

        try:
            import cv2  # type: ignore

            path: str | None = None

            # 1. Explicit caller-provided cascade path.
            if self._cascade_path and os.path.isfile(
                self._cascade_path
            ):
                path = self._cascade_path

            # 2. OpenCV's bundled Haar cascade directory.
            if path is None:
                haarcascade_dir = getattr(
                    cv2.data,
                    "haarcascades",
                    None,
                )

                if haarcascade_dir:
                    candidate = os.path.join(
                        haarcascade_dir,
                        "haarcascade_frontalface_default.xml",
                    )

                    if os.path.isfile(candidate):
                        path = candidate

            # 3. Search relative to the installed cv2 package.
            if path is None:
                cv2_dir = os.path.dirname(
                    os.path.abspath(cv2.__file__)
                )

                candidate = os.path.join(
                    cv2_dir,
                    "data",
                    "haarcascade_frontalface_default.xml",
                )

                if os.path.isfile(candidate):
                    path = candidate

            if path is None:
                self._classifier = None
                self._init_error = (
                    "Haar cascade XML not found. "
                    "Provide cascade_path or install an OpenCV "
                    "distribution containing Haar cascade data."
                )
                logger.warning(self._init_error)
                return

            classifier = cv2.CascadeClassifier(path)

            if classifier.empty():
                self._classifier = None
                self._init_error = (
                    f"Failed to load Haar cascade from {path}"
                )
                logger.warning(self._init_error)
                return

            self._classifier = classifier
            self._init_error = None

        except Exception as exc:
            self._classifier = None
            self._init_error = (
                f"OpenCV cascade face detector unavailable: {exc}"
            )
            logger.warning(self._init_error)

    async def health_check(self) -> dict[str, Any]:
        """Return the current availability of the OpenCV detector."""
        if not self.is_available:
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "message": (
                    self._init_error
                    or "OpenCV cascade detector is not available."
                ),
            }

        return {
            "status": AnalysisStatus.SUCCESS.value,
            "provider": self.provider_name,
            "message": "OpenCV face detector ready.",
        }

    async def detect_faces(
        self,
        investigation_id: UUID,
        image_bytes: bytes,
    ) -> dict[str, Any]:
        """
        Detect faces in image bytes.

        Empty or missing image data is insufficient evidence,
        not provider unavailability.
        """
        start_time = time.perf_counter()

        # IMPORTANT:
        # Evidence semantics take precedence over provider availability.
        # No image bytes means there is nothing to analyze.
        if not image_bytes:
            return {
                "status": AnalysisStatus.INSUFFICIENT_EVIDENCE.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "faces": [],
                "face_count": 0,
                "error": "Empty image bytes provided.",
                "duration_ms": round(
                    (time.perf_counter() - start_time) * 1000,
                    2,
                ),
            }

        # Only attempt provider initialization once actual evidence exists.
        if not self.is_available:
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "faces": [],
                "face_count": 0,
                "error": (
                    self._init_error
                    or "Face detector is unavailable."
                ),
                "duration_ms": round(
                    (time.perf_counter() - start_time) * 1000,
                    2,
                ),
            }

        try:
            import cv2  # type: ignore
            import numpy as np

            nparr = np.frombuffer(
                image_bytes,
                np.uint8,
            )

            img = cv2.imdecode(
                nparr,
                cv2.IMREAD_COLOR,
            )

            if img is None:
                duration_ms = round(
                    (time.perf_counter() - start_time) * 1000,
                    2,
                )

                return {
                    "status": AnalysisStatus.FAILED.value,
                    "provider": self.provider_name,
                    "investigation_id": str(investigation_id),
                    "faces": [],
                    "face_count": 0,
                    "error": (
                        "Failed to decode image bytes with OpenCV."
                    ),
                    "duration_ms": duration_ms,
                }

            gray = cv2.cvtColor(
                img,
                cv2.COLOR_BGR2GRAY,
            )

            detected = self._classifier.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30),
            )

            faces: list[dict[str, Any]] = []

            for (x, y, w, h) in detected:
                faces.append(
                    {
                        "bbox": [
                            int(x),
                            int(y),
                            int(w),
                            int(h),
                        ],
                        "confidence": 0.95,
                    }
                )

            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2,
            )

            if not faces:
                # Lack of detected faces does NOT imply fraud.
                return {
                    "status": (
                        AnalysisStatus.INSUFFICIENT_EVIDENCE.value
                    ),
                    "provider": self.provider_name,
                    "investigation_id": str(investigation_id),
                    "faces": [],
                    "face_count": 0,
                    "message": (
                        "No human faces detected in image. "
                        "Not considered evidence of fraud."
                    ),
                    "duration_ms": duration_ms,
                }

            return {
                "status": AnalysisStatus.SUCCESS.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "faces": faces,
                "face_count": len(faces),
                "duration_ms": duration_ms,
                "metadata": {
                    "image_width": int(img.shape[1]),
                    "image_height": int(img.shape[0]),
                },
            }

        except Exception as exc:
            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2,
            )

            logger.error(
                f"Error during face detection: {exc}",
                exc_info=True,
            )

            return {
                "status": AnalysisStatus.FAILED.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "faces": [],
                "face_count": 0,
                "error": f"Face detection error: {exc}",
                "duration_ms": duration_ms,
            }


class MockFaceDetectorProvider(FaceDetectorProvider):
    """Deterministic Mock Face Detector provider for unit tests and local mock scenarios."""

    def __init__(
        self,
        mock_face_count: int = 1,
        mock_status: AnalysisStatus = AnalysisStatus.SUCCESS,
        mock_faces: list[dict[str, Any]] | None = None,
    ) -> None:
        self.mock_face_count = mock_face_count
        self.mock_status = mock_status
        self.mock_faces = mock_faces or (
            [
                {
                    "bbox": [50, 50, 100, 100],
                    "confidence": 0.98,
                }
            ]
            if mock_face_count > 0
            else []
        )

    @property
    def provider_name(self) -> str:
        return "mock_face_detector"

    @property
    def is_available(self) -> bool:
        return self.mock_status != AnalysisStatus.UNAVAILABLE

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": self.mock_status.value,
            "provider": self.provider_name,
            "message": "Mock Face Detector active.",
        }

    async def detect_faces(
        self,
        investigation_id: UUID,
        image_bytes: bytes,
    ) -> dict[str, Any]:
        if self.mock_status == AnalysisStatus.UNAVAILABLE:
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "faces": [],
                "face_count": 0,
                "error": (
                    "Mock face detector configured as unavailable."
                ),
            }

        if self.mock_status == AnalysisStatus.FAILED:
            return {
                "status": AnalysisStatus.FAILED.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "faces": [],
                "face_count": 0,
                "error": (
                    "Simulated mock face detector failure."
                ),
            }

        if (
            self.mock_face_count == 0
            or self.mock_status
            == AnalysisStatus.INSUFFICIENT_EVIDENCE
        ):
            return {
                "status": (
                    AnalysisStatus.INSUFFICIENT_EVIDENCE.value
                ),
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "faces": [],
                "face_count": 0,
                "message": (
                    "No human faces detected in image. "
                    "Not considered evidence of fraud."
                ),
            }

        return {
            "status": AnalysisStatus.SUCCESS.value,
            "provider": self.provider_name,
            "investigation_id": str(investigation_id),
            "faces": self.mock_faces,
            "face_count": len(self.mock_faces),
            "metadata": {"is_mock": True},
        }


class UnavailableFaceDetectorProvider(FaceDetectorProvider):
    """Fail-safe placeholder for face detector provider."""

    @property
    def provider_name(self) -> str:
        return "unavailable_face_detector"

    @property
    def is_available(self) -> bool:
        return False

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "message": "Face detector is not configured.",
        }

    async def detect_faces(
        self,
        investigation_id: UUID,
        image_bytes: bytes,
    ) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "investigation_id": str(investigation_id),
            "faces": [],
            "face_count": 0,
            "error": "Face detector provider is unavailable.",
        }