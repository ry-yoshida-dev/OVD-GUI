import gc
from dataclasses import replace
from time import perf_counter

from open_vocabulary_detector import DetectionResult, DetectorSettings, OpenVocabularyDetector

from .detection_outcome import DetectionOutcome
from .detection_request import DetectionRequest


class DetectorSession:
    """
    Keeps one loaded detector and switches it when the requested model changes.

    Settings differing only in thresholds or batch size reuse the loaded model,
    since those values are read at inference time; any other change reloads it.
    """

    def __init__(self) -> None:
        self._detector: OpenVocabularyDetector | None = None

    @property
    def loaded_settings(self) -> DetectorSettings | None:
        """
        Settings of the loaded detector.

        Returns
        -------
        DetectorSettings | None
            ``None`` while no detector is loaded.
        """
        return None if self._detector is None else self._detector.settings

    def is_loaded_for(self, settings: DetectorSettings) -> bool:
        """
        Whether ``settings`` can run on the loaded model without reloading.

        Parameters
        ----------
        settings : DetectorSettings
            Requested settings.

        Returns
        -------
        bool
            True if the same model is loaded on the same device with the same precision.
        """
        loaded_settings: DetectorSettings | None = self.loaded_settings
        if loaded_settings is None:
            return False
        return replace(loaded_settings, thresholds=settings.thresholds, batch_size=settings.batch_size) == settings

    def detect(self, request: DetectionRequest) -> DetectionOutcome:
        """
        Run detection, loading the requested model first if needed.

        Parameters
        ----------
        request : DetectionRequest
            Settings, image and prompt.

        Returns
        -------
        DetectionOutcome
            Detections and timing.
        """
        is_model_reloaded: bool = not self.is_loaded_for(request.settings)
        detector: OpenVocabularyDetector = self._prepare(request.settings)
        started_at: float = perf_counter()
        result: DetectionResult = detector.detect(request.image, request.labeled_prompt.prompt)
        return DetectionOutcome(
            request=request,
            result=result,
            inference_seconds=perf_counter() - started_at,
            is_model_reloaded=is_model_reloaded,
        )

    def unload(self) -> None:
        """
        Release the loaded detector.
        """
        self._detector = None
        gc.collect()

    def _prepare(self, settings: DetectorSettings) -> OpenVocabularyDetector:
        if self._detector is not None and self.is_loaded_for(settings):
            self._detector.settings = settings
            return self._detector
        self.unload()
        self._detector = settings.build()
        return self._detector
