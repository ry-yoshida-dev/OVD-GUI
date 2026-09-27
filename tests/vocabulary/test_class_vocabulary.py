import pytest

from ovd_gui.vocabulary import ClassDefinition, ClassVocabulary


def _vocabulary(*texts: str) -> ClassVocabulary:
    vocabulary: ClassVocabulary = ClassVocabulary()
    for text in texts:
        vocabulary.add(ClassDefinition.parse(text))
    return vocabulary


def test_adding_an_existing_name_extends_its_phrases() -> None:
    vocabulary: ClassVocabulary = _vocabulary("car: car, suv", "Car: SUV, taxi", "dog")
    assert [definition.text for definition in vocabulary.classes] == ["car: car, suv, taxi", "dog"]
    assert vocabulary.index_of("DOG") == 1


def test_a_phrase_can_query_only_one_class() -> None:
    vocabulary: ClassVocabulary = _vocabulary("car: car, van")
    with pytest.raises(ValueError, match="is already a prompt of the class 'car'"):
        vocabulary.add(ClassDefinition.named("Van"))
    with pytest.raises(ValueError, match="is already a prompt"):
        vocabulary.add(ClassDefinition.parse("truck: truck, van"))
    assert vocabulary.class_names == ("car",)


def test_replace_drops_repeated_names_and_phrases() -> None:
    vocabulary: ClassVocabulary = ClassVocabulary()
    vocabulary.replace(ClassDefinition.parse(text) for text in ("car: car, van", "CAR", "truck: van, lorry"))
    assert [definition.text for definition in vocabulary.classes] == ["car: car, van", "truck: lorry"]


def test_rename_class_and_phrase_keep_the_rules() -> None:
    vocabulary: ClassVocabulary = _vocabulary("cat", "dog: dog, puppy")
    assert vocabulary.rename_class(0, "kitten").name == "cat"
    assert vocabulary.classes[0] == ClassDefinition.named("kitten")
    with pytest.raises(ValueError, match="already exists"):
        vocabulary.rename_class(0, "DOG")
    with pytest.raises(ValueError, match="is already a prompt"):
        vocabulary.rename_class(0, "puppy")
    vocabulary.rename_phrase(1, 1, "hound")
    assert vocabulary.classes[1].text_queries == ("dog", "hound")
    with pytest.raises(ValueError, match="is already a prompt"):
        vocabulary.rename_phrase(1, 1, "Kitten")
    assert vocabulary.classes[1].text_queries == ("dog", "hound")


def test_remove_classes_and_phrases() -> None:
    vocabulary: ClassVocabulary = _vocabulary("cat", "dog: dog, puppy", "bird")
    vocabulary.remove_phrases(1, [0])
    vocabulary.remove_classes([0, 5])
    assert [definition.text for definition in vocabulary.classes] == ["dog: puppy", "bird"]


def test_insert_places_classes_and_phrases_at_a_position() -> None:
    vocabulary: ClassVocabulary = _vocabulary("cat", "dog: dog, puppy")
    vocabulary.insert(1, ClassDefinition.named("bird"))
    vocabulary.insert_phrases(2, 1, ["hound", "Dog"])
    assert [definition.text for definition in vocabulary.classes] == ["cat", "bird", "dog: dog, hound, puppy"]
    with pytest.raises(ValueError, match="already exists"):
        vocabulary.insert(0, ClassDefinition.named("BIRD"))


def test_move_phrase_within_and_across_classes() -> None:
    vocabulary: ClassVocabulary = _vocabulary("car: car, suv, van", "truck")
    vocabulary.move_phrase(0, 0, 0, 3)
    assert vocabulary.classes[0].text_queries == ("suv", "van", "car")
    vocabulary.move_phrase(0, 1, 1, 0)
    assert [definition.text for definition in vocabulary.classes] == ["car: suv, car", "truck: van, truck"]


def test_promote_phrase_makes_a_class_of_it() -> None:
    vocabulary: ClassVocabulary = _vocabulary("car: car, van", "truck")
    assert vocabulary.promote_phrase(0, 1, 1) == 1
    assert [definition.text for definition in vocabulary.classes] == ["car", "van", "truck"]
    with pytest.raises(ValueError, match="already exists"):
        vocabulary.promote_phrase(2, 0, 0)
    assert [definition.text for definition in vocabulary.classes] == ["car", "van", "truck"]
