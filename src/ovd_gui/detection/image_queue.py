from collections import deque
from collections.abc import Sequence
from pathlib import Path
from threading import Lock


class ImageQueue:
    """
    Image files waiting to be detected, taken in order but reorderable from any thread.

    The worker thread takes the next image while the GUI thread may move an image to the front, so the image the
    user is looking at is detected before the rest.
    """

    def __init__(self, image_paths: Sequence[Path]) -> None:
        """
        Parameters
        ----------
        image_paths : Sequence[Path]
            Image files in their initial order.
        """
        self._lock: Lock = Lock()
        self._waiting_paths: deque[Path] = deque(image_paths)

    def take(self) -> Path | None:
        """
        Remove the image to detect next.

        Returns
        -------
        Path | None
            First waiting image, or ``None`` once every image has been taken.
        """
        with self._lock:
            return self._waiting_paths.popleft() if self._waiting_paths else None

    def prioritize(self, image_path: Path) -> bool:
        """
        Move a waiting image to the front.

        Parameters
        ----------
        image_path : Path
            Image to detect next.

        Returns
        -------
        bool
            True when the image was still waiting; False when it was already taken or never queued.
        """
        with self._lock:
            if image_path not in self._waiting_paths:
                return False
            self._waiting_paths.remove(image_path)
            self._waiting_paths.appendleft(image_path)
            return True
