from dataclasses import dataclass

from ...detection import BatchDetectionRequest
from ...export import ExportOptions
from .batch_purpose import BatchPurpose


@dataclass(frozen=True, eq=False)
class BatchJob:
    """
    Batch detection together with the reason it runs.

    Attributes
    ----------
    purpose : BatchPurpose
        Whether the batch serves Detect All or an export.
    request : BatchDetectionRequest
        Settings, prompt and image files of the batch.
    export_options : ExportOptions | None
        Where the results are written; given exactly when ``purpose`` is ``EXPORT``.

    Raises
    ------
    ValueError
        If ``export_options`` does not match ``purpose``.
    """

    purpose: BatchPurpose
    request: BatchDetectionRequest
    export_options: ExportOptions | None

    def __post_init__(self) -> None:
        match self.purpose:
            case BatchPurpose.DETECT_ALL:
                if self.export_options is not None:
                    raise ValueError("export_options must be None for Detect All")
            case BatchPurpose.EXPORT:
                if self.export_options is None:
                    raise ValueError("export_options are required for an export")

    @classmethod
    def detect_all(cls, request: BatchDetectionRequest) -> "BatchJob":
        """
        Batch listing the detections of every image in the table.

        Parameters
        ----------
        request : BatchDetectionRequest
            Settings, prompt and image files.

        Returns
        -------
        BatchJob
            Job with the ``DETECT_ALL`` purpose.
        """
        return cls(purpose=BatchPurpose.DETECT_ALL, request=request, export_options=None)

    @classmethod
    def export(cls, request: BatchDetectionRequest, export_options: ExportOptions) -> "BatchJob":
        """
        Batch whose results are written as annotation files.

        Parameters
        ----------
        request : BatchDetectionRequest
            Settings, prompt and image files.
        export_options : ExportOptions
            Format and output directory of the files.

        Returns
        -------
        BatchJob
            Job with the ``EXPORT`` purpose.
        """
        return cls(purpose=BatchPurpose.EXPORT, request=request, export_options=export_options)
