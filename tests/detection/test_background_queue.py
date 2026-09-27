from dataclasses import replace
from pathlib import Path

from open_vocabulary_detector import (
    DetectionResult,
    DetectionThresholds,
    DetectorBackend,
    DetectorSettings,
    Device,
    ImageSize,
    Prompt,
    PromptKind,
)

from ovd_gui.detection import (
    BackgroundQueue,
    DetectionFailure,
    DetectionFailureKind,
    DetectionRequest,
    DetectorProfile,
    LabeledPrompt,
    PromptSignature,
    ReferenceBoard,
    ResultLibrary,
)
from ovd_gui.vocabulary import ClassDefinition

SETTINGS: DetectorSettings = DetectorSettings(
    backend=DetectorBackend.YOLO_WORLD,
    weights_path="yolov8s-worldv2.pt",
    thresholds=DetectionThresholds(confidence_threshold=0.25, nms_iou_threshold=0.7),
    device=Device.CPU,
)
PROFILE: DetectorProfile = DetectorProfile.of(SETTINGS)
OTHER_PROFILE: DetectorProfile = DetectorProfile.of(replace(SETTINGS, weights_path="yolov8l-worldv2.pt"))
BOARD: ReferenceBoard = ReferenceBoard()
CAT: tuple[ClassDefinition, ...] = (ClassDefinition.named("cat"),)
CAT_PROMPT: LabeledPrompt = BOARD.build_prompt(CAT, frozenset({PromptKind.TEXT}))
CAT_SIGNATURE: PromptSignature = BOARD.signature_of(CAT)
IMAGE_PATHS: tuple[Path, ...] = (Path("a.jpg"), Path("b.jpg"), Path("c.jpg"))
DETECTION_ERROR: DetectionFailure = DetectionFailure(DetectionFailureKind.DETECTION_ERROR, "ValueError: broken")
UNREADABLE: DetectionFailure = DetectionFailure(DetectionFailureKind.UNREADABLE_IMAGE, "OSError: broken")


def _request(image_path: Path) -> DetectionRequest:
    return DetectionRequest(settings=SETTINGS, image_path=image_path, labeled_prompt=CAT_PROMPT)


def _record(library: ResultLibrary, image_path: Path) -> None:
    library.record(
        PROFILE, image_path, DetectionResult.empty(Prompt.from_class_names(("cat",)), ImageSize(10, 10)), CAT_PROMPT
    )


def _next(queue: BackgroundQueue, shown_image_path: Path | None = None) -> Path | None:
    return queue.next_image(PROFILE, PROFILE, CAT_SIGNATURE, shown_image_path, IMAGE_PATHS)


def test_shown_image_comes_first_then_the_images_without_an_up_to_date_result() -> None:
    library: ResultLibrary = ResultLibrary()
    queue: BackgroundQueue = BackgroundQueue(library)
    assert _next(queue, IMAGE_PATHS[2]) == IMAGE_PATHS[2]
    assert _next(queue) == IMAGE_PATHS[0]
    _record(library, IMAGE_PATHS[0])
    _record(library, IMAGE_PATHS[2])
    assert _next(queue, IMAGE_PATHS[2]) == IMAGE_PATHS[1]
    _record(library, IMAGE_PATHS[1])
    assert _next(queue) is None


def test_images_detected_with_other_classes_are_detected_again() -> None:
    library: ResultLibrary = ResultLibrary()
    queue: BackgroundQueue = BackgroundQueue(library)
    for image_path in IMAGE_PATHS:
        _record(library, image_path)
    dog_signature: PromptSignature = BOARD.signature_of((ClassDefinition.named("dog"),))
    assert queue.next_image(PROFILE, PROFILE, dog_signature, None, IMAGE_PATHS) == IMAGE_PATHS[0]


def test_detection_error_pauses_the_other_images_until_resumed_and_is_not_retried() -> None:
    queue: BackgroundQueue = BackgroundQueue(ResultLibrary())
    queue.record_failure(_request(IMAGE_PATHS[0]), DETECTION_ERROR)
    assert queue.is_paused
    assert _next(queue) is None
    assert _next(queue, IMAGE_PATHS[0]) == IMAGE_PATHS[0]
    queue.resume()
    assert _next(queue) == IMAGE_PATHS[1]
    queue.forget_failures()
    assert _next(queue) == IMAGE_PATHS[0]


def test_unreadable_image_is_skipped_without_pausing() -> None:
    queue: BackgroundQueue = BackgroundQueue(ResultLibrary())
    queue.record_failure(_request(IMAGE_PATHS[0]), UNREADABLE)
    assert not queue.is_paused
    assert _next(queue, IMAGE_PATHS[0]) == IMAGE_PATHS[1]
    queue.forget_failures()
    assert _next(queue) == IMAGE_PATHS[1]


def test_pinned_profile_blocks_background_detection_with_another_profile() -> None:
    queue: BackgroundQueue = BackgroundQueue(ResultLibrary())
    queue.pin()
    assert queue.next_image(OTHER_PROFILE, PROFILE, CAT_SIGNATURE, None, IMAGE_PATHS) is None
    assert queue.next_image(PROFILE, PROFILE, CAT_SIGNATURE, None, IMAGE_PATHS) == IMAGE_PATHS[0]
    assert queue.next_image(OTHER_PROFILE, None, CAT_SIGNATURE, None, IMAGE_PATHS) == IMAGE_PATHS[0]
    queue.unpin()
    assert queue.next_image(OTHER_PROFILE, PROFILE, CAT_SIGNATURE, None, IMAGE_PATHS) == IMAGE_PATHS[0]
