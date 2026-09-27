import pytest

from ovd_gui.analysis import ConfidenceHistogram


def test_confidences_fall_in_equal_bins_with_one_in_the_last() -> None:
    histogram: ConfidenceHistogram = ConfidenceHistogram.of([0.0, 0.1, 0.49, 0.5, 0.99, 1.0], bin_count=4)
    assert histogram.bin_counts == (2, 1, 1, 2)
    assert histogram.bin_width == 0.25
    assert histogram.largest_count == 2
    assert histogram.total_count == 6


def test_empty_histogram_has_zero_counts() -> None:
    histogram: ConfidenceHistogram = ConfidenceHistogram.of([])
    assert histogram.bin_counts == (0,) * ConfidenceHistogram.DEFAULT_BIN_COUNT
    assert histogram.largest_count == 0


@pytest.mark.parametrize(("confidences", "bin_count"), [([0.5], 0), ([1.2], 10), ([-0.1], 10)])
def test_invalid_input_is_rejected(confidences: list[float], bin_count: int) -> None:
    with pytest.raises(ValueError):
        ConfidenceHistogram.of(confidences, bin_count)
