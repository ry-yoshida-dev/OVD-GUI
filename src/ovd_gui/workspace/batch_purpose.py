from enum import Enum


class BatchPurpose(Enum):
    """
    Why every open image is being detected.
    """

    DETECT_ALL = "detect_all"
    EXPORT = "export"

    @property
    def title(self) -> str:
        """
        Title of the progress dialog.

        Returns
        -------
        str
            Name of the running task.
        """
        match self:
            case BatchPurpose.DETECT_ALL:
                return "Detect All"
            case BatchPurpose.EXPORT:
                return "Export Detections"

    @property
    def is_blocking(self) -> bool:
        """
        Whether the window is blocked while the batch runs.

        Detect All runs in the background so images and detections can be browsed meanwhile. An export blocks the
        window because the files are written with the class names current when the batch ends.

        Returns
        -------
        bool
            True when the batch shows a window-modal progress dialog.
        """
        match self:
            case BatchPurpose.DETECT_ALL:
                return False
            case BatchPurpose.EXPORT:
                return True

    def progress_text(self, processed_count: int, total_count: int) -> str:
        """
        Progress message of the running batch.

        Parameters
        ----------
        processed_count : int
            Images processed so far.
        total_count : int
            Images in the batch.

        Returns
        -------
        str
            Message with the processed and total counts.
        """
        match self:
            case BatchPurpose.DETECT_ALL:
                return f"Detecting all images ({processed_count}/{total_count})..."
            case BatchPurpose.EXPORT:
                return f"Detecting images for export ({processed_count}/{total_count})..."
