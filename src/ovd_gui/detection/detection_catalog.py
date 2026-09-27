from collections.abc import Iterable
from pathlib import Path

from open_vocabulary_detector import DetectionResult

from .detection_record import DetectionRecord
from .labeled_prompt import LabeledPrompt
from .prompt_change import PromptChange
from .prompt_signature import PromptSignature


class DetectionCatalog:
    """
    Latest detection result of every image, searchable as individual detections.

    Recording an image again replaces its previous result; images keep the order in which they were first recorded.
    Each result is kept with the labeled prompt it was detected with, so detections name the query that matched them
    and a result can tell how the classes have changed since.

    Every detection is accepted until the user rejects it; rejected detections stay stored but are left out of
    exports. Recording an image again accepts every detection of its new result.
    """

    def __init__(self) -> None:
        self._results: dict[Path, DetectionResult] = {}
        self._prompts: dict[Path, LabeledPrompt] = {}
        self._rejected_indices: dict[Path, frozenset[int]] = {}

    def __len__(self) -> int:
        return len(self._results)

    def __contains__(self, image_path: object) -> bool:
        return image_path in self._results

    def record(
        self, image_path: Path, result: DetectionResult, labeled_prompt: LabeledPrompt
    ) -> tuple[DetectionRecord, ...]:
        """
        Store the result of one image, replacing an earlier one.

        Parameters
        ----------
        image_path : Path
            Image file the result was detected in.
        result : DetectionResult
            Detections of the image.
        labeled_prompt : LabeledPrompt
            Prompt the result was detected with.

        Returns
        -------
        tuple[DetectionRecord, ...]
            Detections of the image in result order.

        Raises
        ------
        ValueError
            If the prompt does not have as many queries as the prompt of the result.
        """
        if len(labeled_prompt.query_labels) != len(result.prompt.queries):
            raise ValueError(
                f"expected {len(result.prompt.queries)} query labels. got {len(labeled_prompt.query_labels)}"
            )
        self._results[image_path] = result
        self._prompts[image_path] = labeled_prompt
        self._rejected_indices.pop(image_path, None)
        return self.records_of(image_path)

    def result_of(self, image_path: Path) -> DetectionResult | None:
        """
        Stored result of one image.

        Parameters
        ----------
        image_path : Path
            Image to look up.

        Returns
        -------
        DetectionResult | None
            ``None`` if the image has not been detected.
        """
        return self._results.get(image_path)

    def labeled_prompt_of(self, image_path: Path) -> LabeledPrompt | None:
        """
        Prompt one image was detected with.

        Parameters
        ----------
        image_path : Path
            Image to look up.

        Returns
        -------
        LabeledPrompt | None
            ``None`` if the image has not been detected.
        """
        return self._prompts.get(image_path)

    @property
    def image_paths(self) -> tuple[Path, ...]:
        """
        Detected images.

        Returns
        -------
        tuple[Path, ...]
            Images in recording order.
        """
        return tuple(self._results)

    def is_accepted(self, record: DetectionRecord) -> bool:
        """
        Whether a detection is kept for export.

        Parameters
        ----------
        record : DetectionRecord
            Detection of a recorded image.

        Returns
        -------
        bool
            False once the user rejected it.
        """
        return record.detection_index not in self._rejected_indices.get(record.image_path, frozenset())

    def rejected_indices_of(self, image_path: Path) -> frozenset[int]:
        """
        Rejected detections of one image.

        Parameters
        ----------
        image_path : Path
            Image to look up.

        Returns
        -------
        frozenset[int]
            Indices of the rejected detections in the result of the image; empty if none is rejected or the image
            has not been detected.
        """
        return self._rejected_indices.get(image_path, frozenset())

    def set_accepted(self, image_path: Path, detection_indices: Iterable[int], is_accepted: bool) -> None:
        """
        Accept or reject some detections of one image.

        Parameters
        ----------
        image_path : Path
            Recorded image.
        detection_indices : Iterable[int]
            Indices of the detections in the result of the image.
        is_accepted : bool
            True to accept them, False to reject them.

        Raises
        ------
        KeyError
            If the image has not been detected.
        IndexError
            If an index is outside the result of the image; nothing is changed.
        """
        result: DetectionResult | None = self._results.get(image_path)
        if result is None:
            raise KeyError(f"{image_path} has not been detected")
        indices: frozenset[int] = frozenset(detection_indices)
        if any(not 0 <= index < len(result) for index in indices):
            raise IndexError(f"detection indices must be in [0, {len(result)}). got {sorted(indices)}")
        rejected: frozenset[int] = self.rejected_indices_of(image_path)
        rejected = rejected - indices if is_accepted else rejected | indices
        if rejected:
            self._rejected_indices[image_path] = rejected
        else:
            self._rejected_indices.pop(image_path, None)

    def remove(self, image_path: Path) -> None:
        """
        Forget the result of one image.

        Parameters
        ----------
        image_path : Path
            Image to forget; nothing happens if it has not been detected.
        """
        self._results.pop(image_path, None)
        self._prompts.pop(image_path, None)
        self._rejected_indices.pop(image_path, None)

    def prompt_change_of(self, image_path: Path, current: PromptSignature) -> PromptChange | None:
        """
        How the classes have changed since one image was detected.

        Parameters
        ----------
        image_path : Path
            Image to look up.
        current : PromptSignature
            Prompt a detection would use now.

        Returns
        -------
        PromptChange | None
            ``None`` if the image has not been detected.
        """
        labeled_prompt: LabeledPrompt | None = self._prompts.get(image_path)
        if labeled_prompt is None:
            return None
        return PromptChange.between(labeled_prompt.signature, current)

    def outdated_images(self, current: PromptSignature) -> dict[Path, PromptChange]:
        """
        Images detected with another prompt than the current one.

        Parameters
        ----------
        current : PromptSignature
            Prompt a detection would use now.

        Returns
        -------
        dict[Path, PromptChange]
            Change of every outdated image, in recording order.
        """
        changes: dict[Path, PromptChange] = {
            image_path: PromptChange.between(labeled_prompt.signature, current)
            for image_path, labeled_prompt in self._prompts.items()
        }
        return {image_path: change for image_path, change in changes.items() if not change.is_unchanged}

    def records_of(self, image_path: Path) -> tuple[DetectionRecord, ...]:
        """
        Detections of one image.

        Parameters
        ----------
        image_path : Path
            Image to look up.

        Returns
        -------
        tuple[DetectionRecord, ...]
            Detections in result order; empty if the image has not been detected.
        """
        result: DetectionResult | None = self._results.get(image_path)
        if result is None:
            return ()
        query_labels: tuple[str, ...] = self._prompts[image_path].query_labels
        return tuple(
            DetectionRecord(
                image_path=image_path,
                detection_index=index,
                detection=detection,
                query_label=query_labels[int(query_id)],
            )
            for index, (detection, query_id) in enumerate(zip(result, result.query_ids.tolist(), strict=True))
        )

    def records(self) -> tuple[DetectionRecord, ...]:
        """
        Detections of every image.

        Returns
        -------
        tuple[DetectionRecord, ...]
            Detections grouped by image in recording order.
        """
        return tuple(record for image_path in self._results for record in self.records_of(image_path))

    def clear(self) -> None:
        """
        Forget every stored result.
        """
        self._results.clear()
        self._prompts.clear()
        self._rejected_indices.clear()
