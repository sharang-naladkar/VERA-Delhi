"""Deepfake & Facial Manipulation Provider Interface, MesoNet, Mock, and Unavailable Fallbacks."""

import os
import time
from abc import abstractmethod
from typing import Any
from uuid import UUID

from app.contracts.status import AnalysisStatus
from app.core.logging import get_logger
from app.providers.base import BaseProvider

logger = get_logger("app.providers.deepfake")


class DeepfakeProvider(BaseProvider):
    """Interface for Deepfake (MesoNet / FaceForensics / CV) detection."""

    @abstractmethod
    async def analyze_media(
        self,
        investigation_id: UUID,
        media_bytes: bytes,
        media_type: str,  # image / video
    ) -> dict[str, Any]:
        """Analyze image or video stream for synthetic manipulation or deepfake signs."""
        pass


class MesoNetDeepfakeProvider(DeepfakeProvider):
    """
    MesoNet (Meso4) facial manipulation detector provider.
    Enforces that missing weights cause UNAVAILABLE rather than false authentic conclusions.
    Lazy loads weights only when requested and configured.
    """

    DISCLAIMER = "MODEL SCORE != PROBABILITY OF FRAUD; MODEL SCORE != LEGAL DETERMINATION"

    def __init__(self, weights_path: str | None = None) -> None:
        self.weights_path = weights_path
        self._model: Any = None
        self._is_initialized = False
        self._init_error: str | None = None

    @property
    def provider_name(self) -> str:
        return "mesonet_meso4"

    @property
    def model_version(self) -> str:
        return "1.0.0"

    @property
    def is_available(self) -> bool:
        if not self._is_initialized:
            self._try_init()
        return self._model is not None and self._init_error is None

    def _try_init(self) -> None:
        """Lazy load weights and model."""
        self._is_initialized = True
        if not self.weights_path or not os.path.exists(self.weights_path):
            self._model = None
            self._init_error = "Deepfake model weights unavailable."
            return

        try:
            # Build and load Meso4 architecture
            self._model = self._build_meso4_model(self.weights_path)
            self._init_error = None
        except Exception as exc:
            self._model = None
            self._init_error = f"Failed to load MesoNet weights: {exc}"
            logger.warning(self._init_error)

    def _build_meso4_model(self, weights_path: str) -> Any:
        """Constructs Meso4 architecture in Keras/TensorFlow and loads weights."""
        from tensorflow.keras import layers, models  # type: ignore

        model = models.Sequential([
            layers.Input(shape=(256, 256, 3)),
            layers.Conv2D(8, (3, 3), padding="same", activation="relu"),
            layers.BatchNormalization(),
            layers.MaxPooling2D(pool_size=(2, 2), padding="same"),
            layers.Conv2D(8, (5, 5), padding="same", activation="relu"),
            layers.BatchNormalization(),
            layers.MaxPooling2D(pool_size=(2, 2), padding="same"),
            layers.Conv2D(16, (5, 5), padding="same", activation="relu"),
            layers.BatchNormalization(),
            layers.MaxPooling2D(pool_size=(2, 2), padding="same"),
            layers.Conv2D(16, (5, 5), padding="same", activation="relu"),
            layers.BatchNormalization(),
            layers.MaxPooling2D(pool_size=(4, 4), padding="same"),
            layers.Flatten(),
            layers.Dropout(0.5),
            layers.Dense(16),
            layers.LeakyReLU(negative_slope=0.1),
            layers.Dropout(0.5),
            layers.Dense(1, activation="sigmoid"),
        ])
        model.load_weights(weights_path)
        return model

    async def health_check(self) -> dict[str, Any]:
        if not self.is_available:
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "message": self._init_error or "Deepfake model weights unavailable.",
            }
        return {
            "status": AnalysisStatus.SUCCESS.value,
            "provider": self.provider_name,
            "message": "MesoNet detector ready with loaded weights.",
        }

    async def analyze_media(
        self,
        investigation_id: UUID,
        media_bytes: bytes,
        media_type: str,
    ) -> dict[str, Any]:
        start_time = time.perf_counter()

        if not self.is_available:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "manipulation_score": None,
                "confidence": None,
                "frames_analyzed": 0,
                "faces_analyzed": 0,
                "model": "Meso4",
                "model_version": self.model_version,
                "error": "Deepfake model weights unavailable.",
                "message": "Deepfake model weights unavailable. Cannot evaluate synthetic manipulation.",
                "duration_ms": duration_ms,
            }

        if not media_bytes:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "status": AnalysisStatus.INSUFFICIENT_EVIDENCE.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "manipulation_score": None,
                "confidence": None,
                "frames_analyzed": 0,
                "faces_analyzed": 0,
                "model": "Meso4",
                "model_version": self.model_version,
                "error": "Empty media bytes provided.",
                "duration_ms": duration_ms,
            }

        try:
            import cv2  # type: ignore
            import numpy as np

            nparr = np.frombuffer(media_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return {
                    "status": AnalysisStatus.FAILED.value,
                    "provider": self.provider_name,
                    "investigation_id": str(investigation_id),
                    "manipulation_score": None,
                    "error": "Failed to decode media image bytes.",
                    "duration_ms": duration_ms,
                }

            # Resize to 256x256 and normalize to [0, 1]
            resized = cv2.resize(img, (256, 256))
            input_tensor = np.expand_dims(resized.astype(np.float32) / 255.0, axis=0)

            # MesoNet forward pass
            pred = self._model.predict(input_tensor, verbose=0)
            score = float(pred[0][0])
            confidence = round(abs(score - 0.5) * 2, 4)

            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "status": AnalysisStatus.SUCCESS.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "manipulation_score": round(score, 4),
                "confidence": confidence,
                "frames_analyzed": 1,
                "faces_analyzed": 1,
                "model": "Meso4",
                "model_version": self.model_version,
                "disclaimer": self.DISCLAIMER,
                "duration_ms": duration_ms,
            }
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Error during MesoNet analysis: {exc}", exc_info=True)
            return {
                "status": AnalysisStatus.FAILED.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "manipulation_score": None,
                "error": f"MesoNet execution error: {exc}",
                "duration_ms": duration_ms,
            }


class MockDeepfakeProvider(DeepfakeProvider):
    """Deterministic Mock Deepfake provider for unit tests and local mock scenarios."""

    DISCLAIMER = "MODEL SCORE != PROBABILITY OF FRAUD; MODEL SCORE != LEGAL DETERMINATION"

    def __init__(
        self,
        mock_score: float | None = 0.85,
        mock_confidence: float = 0.90,
        mock_status: AnalysisStatus = AnalysisStatus.SUCCESS,
        mock_frames: int = 5,
        mock_faces: int = 2,
    ) -> None:
        self.mock_score = mock_score
        self.mock_confidence = mock_confidence
        self.mock_status = mock_status
        self.mock_frames = mock_frames
        self.mock_faces = mock_faces

    @property
    def provider_name(self) -> str:
        return "mock_deepfake"

    @property
    def is_available(self) -> bool:
        return self.mock_status != AnalysisStatus.UNAVAILABLE

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": self.mock_status.value,
            "provider": self.provider_name,
            "message": "Mock deepfake detector active.",
        }

    async def analyze_media(
        self,
        investigation_id: UUID,
        media_bytes: bytes,
        media_type: str,
    ) -> dict[str, Any]:
        if self.mock_status == AnalysisStatus.UNAVAILABLE:
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "manipulation_score": None,
                "confidence": None,
                "frames_analyzed": 0,
                "faces_analyzed": 0,
                "model": "MockMeso4",
                "error": "Deepfake model weights unavailable.",
                "message": "Deepfake model weights unavailable.",
            }

        if self.mock_status == AnalysisStatus.FAILED:
            return {
                "status": AnalysisStatus.FAILED.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "manipulation_score": None,
                "error": "Simulated deepfake detection failure.",
            }

        if self.mock_status == AnalysisStatus.INSUFFICIENT_EVIDENCE:
            return {
                "status": AnalysisStatus.INSUFFICIENT_EVIDENCE.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "manipulation_score": None,
                "confidence": None,
                "frames_analyzed": self.mock_frames,
                "faces_analyzed": 0,
                "message": "No face regions detected for deepfake manipulation analysis.",
            }

        return {
            "status": AnalysisStatus.SUCCESS.value,
            "provider": self.provider_name,
            "investigation_id": str(investigation_id),
            "manipulation_score": self.mock_score,
            "confidence": self.mock_confidence,
            "frames_analyzed": self.mock_frames,
            "faces_analyzed": self.mock_faces,
            "model": "MockMeso4",
            "model_version": "1.0.0",
            "disclaimer": self.DISCLAIMER,
            "metadata": {"is_mock": True},
        }


class UnavailableDeepfakeProvider(DeepfakeProvider):
    """Fail-safe placeholder for Deepfake provider."""

    @property
    def provider_name(self) -> str:
        return "unavailable_deepfake"

    @property
    def is_available(self) -> bool:
        return False

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "message": "Deepfake analysis engine is not configured in Phase 01.",
        }

    async def analyze_media(
        self,
        investigation_id: UUID,
        media_bytes: bytes,
        media_type: str,
    ) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "investigation_id": str(investigation_id),
            "manipulation_score": None,
            "error": "Deepfake analysis engine is unavailable.",
        }
