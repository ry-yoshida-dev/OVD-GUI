import pytest

from ovd_gui.review import ClassThresholds


def test_classes_without_their_own_minimum_use_the_default() -> None:
    thresholds: ClassThresholds = ClassThresholds(0.2, {"car": 0.5})
    assert thresholds.minimum_of("car") == 0.5
    assert thresholds.minimum_of("person") == 0.2
    assert thresholds.has_own_minimum("car")
    assert not thresholds.has_own_minimum("person")
    assert thresholds.accepts("car", 0.5)
    assert not thresholds.accepts("car", 0.49)
    assert thresholds.accepts("person", 0.3)


def test_copies_change_one_minimum_and_compare_by_value() -> None:
    thresholds: ClassThresholds = ClassThresholds()
    assert not thresholds.is_effective
    updated: ClassThresholds = thresholds.with_class_minimum("car", 0.4).with_default_minimum(0.1)
    assert updated == ClassThresholds(0.1, {"car": 0.4})
    assert hash(updated) == hash(ClassThresholds(0.1, {"car": 0.4}))
    assert updated.is_effective
    assert updated.with_class_minimum("car", None) == ClassThresholds(0.1)
    assert thresholds == ClassThresholds()


@pytest.mark.parametrize("minimum", [-0.1, 1.5])
def test_minimums_outside_the_unit_interval_are_rejected(minimum: float) -> None:
    with pytest.raises(ValueError):
        ClassThresholds(minimum)
    with pytest.raises(ValueError):
        ClassThresholds().with_class_minimum("car", minimum)


def test_blank_class_names_are_rejected() -> None:
    with pytest.raises(ValueError):
        ClassThresholds(0.0, {" ": 0.3})
