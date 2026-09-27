import pytest

from ovd_gui.vocabulary import ClassDefinition


def test_plain_name_is_queried_by_itself() -> None:
    definition: ClassDefinition = ClassDefinition.parse("  traffic   cone ")
    assert definition == ClassDefinition(name="traffic cone", text_queries=("traffic cone",))
    assert definition.is_named_query
    assert definition.text == "traffic cone"


def test_colon_lists_the_phrases() -> None:
    definition: ClassDefinition = ClassDefinition.parse("car: car,  suv , , taxi")
    assert definition.text_queries == ("car", "suv", "taxi")
    assert definition.text == "car: car, suv, taxi"
    assert ClassDefinition.parse(definition.text) == definition
    assert ClassDefinition.parse("my mug:").text_queries == ()


@pytest.mark.parametrize("text", ["", " : suv", "a,b", "car: suv, SUV"])
def test_invalid_classes_are_rejected(text: str) -> None:
    with pytest.raises(ValueError):
        ClassDefinition.parse(text)


def test_renaming_a_named_query_renames_the_phrase_too() -> None:
    assert ClassDefinition.named("cat").renamed("kitten") == ClassDefinition.named("kitten")
    assert ClassDefinition.parse("car: suv").renamed("vehicle").text_queries == ("suv",)
