from pathlib import Path

from ovd_gui.detection import ImageQueue


def test_images_are_taken_in_order_with_a_prioritized_image_first() -> None:
    queue: ImageQueue = ImageQueue((Path("a.png"), Path("b.png"), Path("c.png")))
    assert queue.take() == Path("a.png")
    assert queue.prioritize(Path("c.png"))
    assert not queue.prioritize(Path("a.png"))
    assert not queue.prioritize(Path("unknown.png"))
    assert [queue.take(), queue.take(), queue.take()] == [Path("c.png"), Path("b.png"), None]
