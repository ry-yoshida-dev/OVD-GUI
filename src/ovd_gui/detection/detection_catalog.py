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
    """

    def __init__(self) -> None:
        self._results: dict[Path, DetectionResult] = {}
        self._prompts: dict[Path, LabeledPrompt] = {}

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
