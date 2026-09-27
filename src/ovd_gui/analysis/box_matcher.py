import numpy as np
from geometry import BboxCalculator
from numpy.typing import NDArray


class BoxMatcher:
    """
    One-to-one pairing of two sets of boxes by overlap.

    Pairs are formed greedily from the most overlapping one; each box joins at most one pair, and only pairs whose
    intersection over union reaches the threshold are formed.
    """

    DEFAULT_IOU_THRESHOLD = 0.5

    def __init__(self, iou_threshold: float = DEFAULT_IOU_THRESHOLD) -> None:
        """
        Parameters
        ----------
        iou_threshold : float, optional
            Smallest intersection over union of a pair, in ``(0, 1]``.

        Raises
        ------
        ValueError
            If ``iou_threshold`` is outside ``(0, 1]``.
        """
        if not 0.0 < iou_threshold <= 1.0:
            raise ValueError(f"iou_threshold must be in (0, 1]. got {iou_threshold}")
        self._iou_threshold: float = iou_threshold

    @property
    def iou_threshold(self) -> float:
        """
        Smallest intersection over union of a pair.

        Returns
        -------
        float
            Threshold given at construction.
        """
        return self._iou_threshold

    def pairs(self, first_xyxy: NDArray[np.float64], second_xyxy: NDArray[np.float64]) -> tuple[tuple[int, int], ...]:
        """
        Pair the boxes of two sets.

        Parameters
        ----------
        first_xyxy : NDArray[np.float64]
            XYXY boxes, shape (N, 4).
        second_xyxy : NDArray[np.float64]
            XYXY boxes, shape (M, 4).

        Returns
        -------
        tuple[tuple[int, int], ...]
            ``(first index, second index)`` of every pair, most overlapping first.

        Raises
        ------
        ValueError
            If a set does not have shape (K, 4).
        """
        for name, boxes in (("first_xyxy", first_xyxy), ("second_xyxy", second_xyxy)):
            if boxes.ndim != 2 or boxes.shape[1] != 4:
                raise ValueError(f"{name} must have shape (K, 4). got {boxes.shape}")
        if not len(first_xyxy) or not len(second_xyxy):
            return ()
        overlaps: NDArray[np.float64] = np.asarray(
            BboxCalculator.compute_iou(first_xyxy, second_xyxy), dtype=np.float64
        ).reshape(len(first_xyxy), len(second_xyxy))
        candidate_order: NDArray[np.int64] = np.argsort(-overlaps, axis=None, kind="stable").astype(np.int64)
        used_first: set[int] = set()
        used_second: set[int] = set()
        pairs: list[tuple[int, int]] = []
        for flat_index in candidate_order.tolist():
            first_index, second_index = divmod(int(flat_index), len(second_xyxy))
            if overlaps[first_index, second_index] < self._iou_threshold:
                break
            if first_index in used_first or second_index in used_second:
                continue
            used_first.add(first_index)
            used_second.add(second_index)
            pairs.append((first_index, second_index))
        return tuple(pairs)
