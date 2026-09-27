import numpy as np
import pytest

from ovd_gui.analysis import BoxMatcher


def test_boxes_pair_one_to_one_from_the_most_overlapping() -> None:
    first: np.ndarray = np.array([[0, 0, 10, 10], [100, 100, 110, 110]], dtype=np.float64)
    second: np.ndarray = np.array([[1, 0, 11, 10], [0, 0, 10, 10], [50, 50, 60, 60]], dtype=np.float64)
    assert BoxMatcher().pairs(first, second) == ((0, 1),)


def test_pairs_below_the_threshold_are_not_formed() -> None:
    first: np.ndarray = np.array([[0, 0, 10, 10]], dtype=np.float64)
    second: np.ndarray = np.array([[5, 0, 15, 10]], dtype=np.float64)
    assert BoxMatcher(0.5).pairs(first, second) == ()
    assert BoxMatcher(0.3).pairs(first, second) == ((0, 0),)


def test_empty_sets_have_no_pairs_and_bad_input_is_rejected() -> None:
    assert BoxMatcher().pairs(np.zeros((0, 4)), np.array([[0, 0, 1, 1]], dtype=np.float64)) == ()
    with pytest.raises(ValueError):
        BoxMatcher().pairs(np.zeros((2, 3)), np.zeros((1, 4)))
    with pytest.raises(ValueError):
        BoxMatcher(0.0)
