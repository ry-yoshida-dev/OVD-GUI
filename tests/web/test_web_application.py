import io
import time
import zipfile
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import ClassVar

import numpy as np
import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect
from httpx import Response
from open_vocabulary_detector import DetectionResult, DetectorBackend, ImageSize, OpenVocabularyDetector, Prompt
from PIL import Image

from ovd_gui.detection import DetectorSession, DeviceAvailability
from ovd_gui.preset import PresetCatalog
from ovd_gui.storage import ClassSetStore, ClassThresholdStore, ResultStore, SessionStore
from ovd_gui.vocabulary import ClassListStore
from ovd_gui.web import WebApplication
from ovd_gui.workspace import ModelSelector, UploadStore, WorkspaceStores

ACCESS_TOKEN: str = "test-token"
COOKIE_NAME: str = "ovd_gui_token_test"


class OneBoxDetector(OpenVocabularyDetector):
    BACKEND: ClassVar[DetectorBackend] = DetectorBackend.GROUNDING_DINO

    def _detect_mini_batch(self, images: Sequence[Image.Image], prompt: Prompt) -> list[DetectionResult]:
        return [
            DetectionResult.from_xyxy(
                xyxy=np.array([[1.0, 2.0, 10.0, 12.0]]),
                confidences=np.array([0.8]),
                query_ids=np.array([0], dtype=np.int64),
                prompt=prompt,
                image_size=ImageSize(width=image.width, height=image.height),
            )
            for image in images
        ]


@pytest.fixture
def image_directory(tmp_path: Path) -> Path:
    directory: Path = tmp_path / "images"
    directory.mkdir()
    for index in range(2):
        Image.new("RGB", (40, 20)).save(directory / f"image{index}.png")
    return directory


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    data_directory: Path = tmp_path / "data"
    model_selector: ModelSelector = ModelSelector(
        PresetCatalog.from_package(), DeviceAvailability(is_cuda_available=False, is_mps_available=False)
    )
    session: DetectorSession = DetectorSession()
    session._detector = OneBoxDetector(model_selector.settings_of(model_selector.default_selection()))
    application: WebApplication = WebApplication(
        model_selector,
        WorkspaceStores(
            class_list_store=ClassListStore(data_directory),
            class_set_store=ClassSetStore(data_directory),
            result_store=ResultStore(data_directory),
            class_threshold_store=ClassThresholdStore(data_directory),
            session_store=SessionStore(data_directory),
            upload_store=UploadStore(data_directory),
        ),
        (),
        tmp_path,
        ACCESS_TOKEN,
        COOKIE_NAME,
        session,
    )
    with TestClient(application.build()) as test_client:
        opened: Response = test_client.get("/", params={"token": ACCESS_TOKEN})
        assert opened.status_code == 200
        assert test_client.cookies.get(COOKIE_NAME) == ACCESS_TOKEN
        yield test_client


def _object(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return {str(key): item for key, item in value.items()}


def _list(value: object) -> list[object]:
    assert isinstance(value, list)
    return list(value)


def _field(value: object, key: str) -> object:
    return _object(value)[key]


def _state(client: TestClient) -> dict[str, object]:
    response: Response = client.get("/api/state")
    assert response.status_code == 200
    return _object(response.json())


def _wait_until(client: TestClient, condition: Callable[[dict[str, object]], bool]) -> dict[str, object]:
    deadline: float = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        state: dict[str, object] = _state(client)
        if condition(state):
            return state
        time.sleep(0.02)
    raise AssertionError("condition not reached")


def _is_idle(state: dict[str, object]) -> bool:
    return state["is_busy"] is False and state["background_image_path"] is None


def test_state_lists_the_default_classes_and_the_model_settings(client: TestClient) -> None:
    state: dict[str, object] = _state(client)
    assert [_field(entry, "name") for entry in _list(state["classes"])] == ["person", "car", "dog"]
    assert state["images"] == []
    assert state["current_image"] is None


def test_opened_folder_is_detected_in_the_background(client: TestClient, image_directory: Path) -> None:
    assert client.post("/api/images/open", json={"paths": [str(image_directory)]}).status_code == 200
    state: dict[str, object] = _wait_until(
        client, lambda current: _is_idle(current) and len(_list(current["images"])) == 2
    )
    assert [_field(image, "state") for image in _list(state["images"])] == ["detected", "detected"]
    first_image: object = _list(_field(client.get("/api/detections").json(), "images"))[0]
    assert _field(first_image, "detections") == [
        {
            "index": 0,
            "class_id": 0,
            "class_name": "person",
            "query": "person",
            "confidence": 0.8,
            "box": [1.0, 2.0, 10.0, 12.0],
            "is_accepted": True,
        }
    ]


def test_uploaded_images_are_stored_and_opened(client: TestClient, tmp_path: Path) -> None:
    image_path: Path = tmp_path / "upload.png"
    Image.new("RGB", (8, 8)).save(image_path)
    response: Response = client.post(
        "/api/uploads", files=[("files", ("folder/upload.png", image_path.read_bytes(), "image/png"))]
    )
    assert response.status_code == 200
    state: dict[str, object] = _state(client)
    current_image: dict[str, object] = _object(state["current_image"])
    assert current_image["path"] == str(tmp_path / "data" / "uploads" / "folder" / "upload.png")
    assert current_image["width"] == 8
    preview: Response = client.get("/api/image", params={"path": current_image["path"]})
    assert preview.headers["content-type"] == "image/jpeg"


def test_invalid_class_edit_answers_with_its_message(client: TestClient) -> None:
    response: Response = client.post("/api/classes/rows", json={"text": "car", "position": 0})
    assert response.status_code == 400
    assert response.json() == {"detail": "A class named 'car' already exists."}


def test_classes_can_be_replaced_as_text_and_saved_as_a_set(client: TestClient) -> None:
    assert client.put("/api/classes/text", json={"text": "cat\nvehicle: car, truck\n"}).status_code == 200
    assert client.post("/api/class-sets/save", json={"name": "animals"}).status_code == 200
    state: dict[str, object] = _state(client)
    assert [_field(entry, "phrases") for entry in _list(state["classes"])] == [["cat"], ["car", "truck"]]
    assert state["class_set"] == {
        "name": "animals",
        "is_edited": False,
        "is_unsaved": False,
        "names": ["animals"],
        "directory": _field(state["class_set"], "directory"),
    }


def test_detect_without_images_is_refused(client: TestClient) -> None:
    response: Response = client.post("/api/detect", json={})
    assert response.json() == {"status": "rejected", "message": "Open an image first.", "skipped_class_names": []}


def test_server_folders_are_listed_with_their_images(client: TestClient, image_directory: Path) -> None:
    listing: object = client.get("/api/files", params={"path": str(image_directory.parent)}).json()
    assert "images" in _list(_field(listing, "directories"))
    images: object = client.get("/api/files", params={"path": str(image_directory)}).json()
    assert _field(images, "images") == ["image0.png", "image1.png"]


def test_requests_without_the_access_cookie_are_refused(client: TestClient) -> None:
    client.cookies.clear()
    assert client.get("/api/state").status_code == 403
    assert client.get("/", params={"token": "wrong"}).status_code == 403
    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/api/events") as socket:
        socket.receive_json()


def test_changes_and_websockets_from_pages_of_other_origins_are_refused(client: TestClient) -> None:
    foreign_origin: dict[str, str] = {"origin": "http://testserver:3000"}
    assert client.post("/api/detect", headers=foreign_origin).status_code == 403
    assert client.post("/api/detect", headers={"origin": "http://testserver"}).status_code != 403
    assert client.get("/api/state", headers=foreign_origin).status_code == 200
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect("/api/events", headers=foreign_origin) as socket,
    ):
        socket.receive_json()


def test_download_holds_only_the_files_the_export_wrote(
    client: TestClient, image_directory: Path, tmp_path: Path
) -> None:
    output_directory: Path = tmp_path / "export"
    output_directory.mkdir()
    (output_directory / "unrelated.txt").write_text("kept out")
    client.post("/api/images/open", json={"paths": [str(image_directory)]})
    _wait_until(client, _is_idle)
    response: Response = client.post(
        "/api/export",
        json={
            "annotation_format": "yolo",
            "output_directory": str(output_directory),
            "is_confidence_included": False,
            "scope": "kept",
        },
    )
    assert _field(response.json(), "status") == "done"
    _wait_until(client, lambda state: state["last_export"] is not None)
    download: Response = client.get("/api/export/download")
    assert download.status_code == 200
    with zipfile.ZipFile(io.BytesIO(download.content)) as archive:
        names: list[str] = archive.namelist()
    assert "unrelated.txt" not in names
    assert names
    assert all((output_directory / name).is_file() for name in names)
