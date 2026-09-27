from ovd_gui.storage import ClassSetSummary


def test_description_counts_classes_prompts_and_images() -> None:
    assert ClassSetSummary(("car", "mug"), 3, 2).description == "2 classes · 3 text prompts · 2 images"
    assert ClassSetSummary(("mug",), 1, 1).description == "1 class · 1 text prompt · 1 image"


def test_description_leaves_out_zero_prompt_and_image_counts() -> None:
    assert ClassSetSummary(("cat",), 0, 0).description == "1 class"
