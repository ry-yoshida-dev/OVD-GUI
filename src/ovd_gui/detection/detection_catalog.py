from pathlib import Path

from open_vocabulary_detector import DetectionResult

from .detection_record import DetectionRecord


class DetectionCatalog:
    """
    Latest detection result of every image, searchable as individual detections.

    Recording an image again replaces its previous result; images keep the order in which they were first recorded.
    Each result is kept with the labels of its prompt queries, so detections name the query that matched them.
    """

    def __init__(self) -> None:
        self._results: dict[Path, DetectionResult] = {}
        self._query_labels: dict[Path, tuple[str, ...]] = {}

    def __len__(self) -> int:
        return len(self._results)

    def __contains__(self, image_path: object) -> bool:
        return image_path in self._results

    def record(
        self, image_path: Path, result: DetectionResult, query_labels: tuple[str, ...]
    ) -> tuple[DetectionRecord, ...]:
        """
        Store the result of one image, replacing an earlier one.

        Parameters
        ----------
        image_path : Path
            Image file the result was detected in.
        result : DetectionResult
            Detections of the image.
        query_labels : tuple[str, ...]
            Label of each query of the prompt the result was detected with.

        Returns
        -------
        tuple[DetectionRecord, ...]
            Detections of the image in result order.

        Raises
        ------
        ValueError
            If there is not exactly one label per prompt query.
        """
        if len(query_labels) != len(result.prompt.queries):
            raise ValueError(f"expected {len(result.prompt.queries)} query labels. got {len(query_labels)}")
        self._results[image_path] = result
        self._query_labels[image_path] = query_labels
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
        query_labels: tuple[str, ...] = self._query_labels[image_path]
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
        self._query_labels.clear()
