from collections.abc import Sequence
from pathlib import Path

from .detection_failure import DetectionFailure
from .detection_failure_kind import DetectionFailureKind
from .detection_request import DetectionRequest
from .detector_profile import DetectorProfile
from .prompt_change import PromptChange
from .prompt_signature import PromptSignature
from .result_library import ResultLibrary


class BackgroundQueue:
    """
    Chooses the open image to detect next in the background, and remembers the images to leave alone.

    An image needs detecting when the profile has no result for it or its result was detected with other classes.
    The shown image comes first, then the other images in list order. A file that could not be read is skipped from
    then on. An image whose detection failed is not detected again with the same profile until the failures are
    forgotten, and the failure pauses the other images until the queue is resumed; the shown image is still chosen
    while paused, so showing an image again retries it. While a profile the user selected is pinned, no other
    profile is detected in the background.
    """

    def __init__(self, result_library: ResultLibrary) -> None:
        """
        Parameters
        ----------
        result_library : ResultLibrary
            Stored results, deciding which images are up to date.
        """
        self._result_library: ResultLibrary = result_library
        self._is_paused: bool = False
        self._is_pinned: bool = False
        self._failed_detections: set[tuple[DetectorProfile, Path]] = set()
        self._unreadable_paths: set[Path] = set()

    @property
    def is_paused(self) -> bool:
        """
        Whether only the shown image is detected, after a failed detection.

        Returns
        -------
        bool
            True from a failed detection until ``resume``.
        """
        return self._is_paused

    @property
    def is_pinned(self) -> bool:
        """
        Whether the shown profile was selected by the user and must not be replaced by another profile.

        Returns
        -------
        bool
            True from ``pin`` until ``unpin``.
        """
        return self._is_pinned

    def resume(self) -> None:
        """
        Detect every image again after a failed detection paused the queue.
        """
        self._is_paused = False

    def pin(self) -> None:
        """
        Keep the shown profile: detect nothing in the background with another profile.
        """
        self._is_pinned = True

    def unpin(self) -> None:
        """
        Allow background detection with any profile again.
        """
        self._is_pinned = False

    def forget_failures(self) -> None:
        """
        Allow the images whose detection failed to be detected again, e.g. after the classes changed.
        """
        self._failed_detections.clear()

    def is_failed(self, profile: DetectorProfile, image_path: Path) -> bool:
        """
        Whether an image is left alone after a failed background detection.

        Parameters
        ----------
        profile : DetectorProfile
            Profile of the model settings chosen now.
        image_path : Path
            Open image.

        Returns
        -------
        bool
            True when the file could not be read, or its detection with ``profile`` failed since the failures were
            last forgotten.
        """
        return image_path in self._unreadable_paths or (profile, image_path) in self._failed_detections

    def record_failure(self, request: DetectionRequest, failure: DetectionFailure) -> None:
        """
        Leave the image of a failed background detection alone.

        Parameters
        ----------
        request : DetectionRequest
            Background detection that failed.
        failure : DetectionFailure
            Why it failed: an unreadable file is skipped from then on, while a model error pauses the queue.
        """
        match failure.kind:
            case DetectionFailureKind.UNREADABLE_IMAGE:
                self._unreadable_paths.add(request.image_path)
            case DetectionFailureKind.DETECTION_ERROR:
                self._failed_detections.add((DetectorProfile.of(request.settings), request.image_path))
                self._is_paused = True

    def next_image(
        self,
        profile: DetectorProfile,
        shown_profile: DetectorProfile | None,
        signature: PromptSignature,
        shown_image_path: Path | None,
        image_paths: Sequence[Path],
    ) -> Path | None:
        """
        Image to detect next in the background.

        Parameters
        ----------
        profile : DetectorProfile
            Profile of the model settings chosen now.
        shown_profile : DetectorProfile | None
            Profile whose results are shown, if any.
        signature : PromptSignature
            What the current classes query.
        shown_image_path : Path | None
            Image shown on the canvas, if any.
        image_paths : Sequence[Path]
            Open images in list order.

        Returns
        -------
        Path | None
            Image file to detect, or ``None`` when nothing needs detecting now.
        """
        is_other_profile_pinned: bool = self._is_pinned and shown_profile is not None and profile != shown_profile
        if is_other_profile_pinned:
            return None
        is_shown_image_pending: bool = (
            shown_image_path is not None
            and shown_image_path not in self._unreadable_paths
            and not self._is_up_to_date(shown_image_path, profile, signature)
        )
        if is_shown_image_pending:
            return shown_image_path
        if self._is_paused:
            return None
        for image_path in image_paths:
            is_skipped: bool = (
                image_path in self._unreadable_paths
                or (profile, image_path) in self._failed_detections
                or self._is_up_to_date(image_path, profile, signature)
            )
            if not is_skipped:
                return image_path
        return None

    def _is_up_to_date(self, image_path: Path, profile: DetectorProfile, signature: PromptSignature) -> bool:
        change: PromptChange | None = self._result_library.prompt_change_of(profile, image_path, signature)
        return change is not None and change.is_unchanged
