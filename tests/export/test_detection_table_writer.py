import csv
from pathlib import Path

import numpy as np
from open_vocabulary_detector import DetectionResult, ImageSize, PromptKind

from ovd_gui.detection import DetectionCatalog, LabeledPrompt, ReferenceBoard
from ovd_gui.export import DetectionTableWriter
from ovd_gui.vocabulary import ClassDefinition

LABELED_PROMPT: LabeledPrompt = ReferenceBoard().build_prompt(
    (ClassDefinition.parse("car: car, taxi"),), frozenset({PromptKind.TEXT})
)


def test_every_detection_is_one_row_with_its_prompt_box_and_acceptance(tmp_path: Path) -> None:
    catalog: DetectionCatalog = DetectionCatalog()
    image_path: Path = tmp_path / "street, 1.jpg"
    catalog.record(
        image_path,
        DetectionResult.from_xyxy(
            xyxy=np.array([[1.0, 2.0, 30.5, 40.0], [5.0, 6.0, 7.0, 8.0]]),
            confidences=np.array([0.75, 0.25]),
            query_ids=np.array([1, 0], dtype=np.int64),
            prompt=LABELED_PROMPT.prompt,
            image_size=ImageSize(width=100, height=50),
        ),
        LABELED_PROMPT,
    )
    catalog.set_accepted(image_path, (1,), is_accepted=False)
    table_path: Path = tmp_path / "table.csv"
    DetectionTableWriter().write(tuple(reversed(catalog.records_of(image_path))), catalog, table_path)
    with table_path.open(encoding="utf-8", newline="") as table_file:
        rows: list[list[str]] = list(csv.reader(table_file))
    assert rows[0] == list(DetectionTableWriter.HEADER)
    assert rows[1][:3] == [str(image_path), "car", "car"]
    assert [float(value) for value in rows[1][3:8]] == [0.25, 5.0, 6.0, 7.0, 8.0]
    assert rows[1][8] == "false"
    assert rows[2][:3] == [str(image_path), "car", "taxi"]
    assert [float(value) for value in rows[2][3:8]] == [0.75, 1.0, 2.0, 30.5, 40.0]
    assert rows[2][8] == "true"
