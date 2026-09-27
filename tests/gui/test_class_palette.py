import pytest

from ovd_gui.gui.class_palette import ClassPalette


def test_colors_cycle_and_are_stable() -> None:
    palette: ClassPalette = ClassPalette()
    assert palette.color_of(0) == palette.color_of(len(ClassPalette.HEX_COLORS))
    assert palette.color_of(0) != palette.color_of(1)


def test_negative_class_id_is_rejected() -> None:
    with pytest.raises(ValueError):
        ClassPalette().color_of(-1)
