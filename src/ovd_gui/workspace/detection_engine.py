from functools import partial
from pathlib import Path
from queue import SimpleQueue
from threading import Thread

from open_vocabulary_detector import DetectionResult

from ..detection import (
    BatchDetectionRequest,
    BatchDetectionSummary,
    DetectionFailure,
    DetectionFailureKind,
    DetectionOutcome,
    DetectionRequest,
    DetectorProfile,
    DetectorSession,
)
from ..media import LoadedImage
from .batch_job import BatchJob
from .detection_listener import DetectionListener
from .task_scheduler import TaskScheduler


class DetectionEngine:
    """
    Runs the detections the user asked for on a worker thread, and background detections in between.

    The engine is used from the thread owning the workspace; requests are queued to its worker thread, whose outcomes
    come back to the owning thread through the ``TaskScheduler`` and are reported to the ``DetectionListener``. Call
    ``shutdown`` before the application quits, or ``stop`` and then ``join`` to wait for the worker on another thread
    while the owning thread keeps receiving the last outcomes.

    A run the user asked for (``detect`` or ``detect_batch``) is a foreground run: only one at a time, and ``is_busy``
    is True from its request until its outcome is reported. A background detection (``detect_in_background``) never
    makes the engine busy and always yields: it is ignored while a foreground run is requested, a foreground run
    requested meanwhile starts as soon as the image being inferred is done, and of the background detections requested
    meanwhile only the latest is kept. The waiting run is sent before a background outcome is reported, so the
    listener can request the next background detection from its callback.
    """

    def __init__(
        self, scheduler: TaskScheduler, listener: DetectionListener, session: DetectorSession | None = None
    ) -> None:
        """
        Parameters
        ----------
        scheduler : TaskScheduler
            Thread receiving the outcomes.
        listener : DetectionListener
            Receiver of the outcomes.
        session : DetectorSession | None, optional
            Session keeping the loaded model; a new one by default.
        """
        self._scheduler: TaskScheduler = scheduler
        self._listener: DetectionListener = listener
        self._session: DetectorSession = session or DetectorSession()
        self._is_busy: bool = False
        self._job: BatchJob | None = None
        self._background_request: DetectionRequest | None = None
        self._waiting_background_request: DetectionRequest | None = None
        self._waiting_foreground_run: DetectionRequest | BatchJob | None = None
        self._is_stopped: bool = False
        self._inbox: SimpleQueue[DetectionRequest | BatchDetectionRequest | None] = SimpleQueue()
        self._thread: Thread = Thread(target=self._work, name="detection-worker", daemon=True)
        self._thread.start()

    @property
    def is_busy(self) -> bool:
        """
        Whether a foreground detection or batch is in progress.

        Returns
        -------
        bool
            True from a foreground request until its outcome is reported.
        """
        return self._is_busy

    @property
    def is_idle(self) -> bool:
        """
        Whether the worker has nothing to do, in the foreground or the background.

        Returns
        -------
        bool
            True when no run is in progress or waiting.
        """
        return not self._is_busy and self._background_request is None

    @property
    def running_job(self) -> BatchJob | None:
        """
        Batch in progress.

        Returns
        -------
        BatchJob | None
            ``None`` while no batch runs.
        """
        return self._job

    @property
    def background_request(self) -> DetectionRequest | None:
        """
        Background detection in progress.

        Returns
        -------
        DetectionRequest | None
            ``None`` while no background detection runs.
        """
        return self._background_request

    def detect(self, request: DetectionRequest) -> None:
        """
        Run one foreground detection, after the background detection in progress if any.

        Parameters
        ----------
        request : DetectionRequest
            Settings, image file and prompt.

        Raises
        ------
        RuntimeError
            If a foreground run is already in progress.
        """
        self._start()
        self._queue_foreground(request)

    def detect_batch(self, job: BatchJob) -> None:
        """
        Run a foreground batch, after the background detection in progress if any.

        Parameters
        ----------
        job : BatchJob
            Batch request and its purpose.

        Raises
        ------
        RuntimeError
            If a foreground run is already in progress.
        """
        self._start()
        self._job = job
        self._queue_foreground(job)

    def detect_in_background(self, request: DetectionRequest) -> None:
        """
        Detect when no foreground run needs the worker, replacing a background detection still waiting.

        Ignored while a foreground run is in progress, and when the same image is already being inferred with the
        same detector profile.

        Parameters
        ----------
        request : DetectionRequest
            Settings, image file and prompt.
        """
        if self._is_busy:
            return
        if self._background_request is None:
            self._send_background(request)
            return
        is_in_progress: bool = self._is_same_detection(request, self._background_request)
        self._waiting_background_request = None if is_in_progress else request

    def prioritize(self, image_path: Path) -> bool:
        """
        Detect an image of the running batch before its other images.

        Parameters
        ----------
        image_path : Path
            Image to detect next.

        Returns
        -------
        bool
            True when a batch is running and the image is still waiting in it.
        """
        return self._job is not None and self._job.request.prioritize(image_path)

    def cancel_batch(self) -> None:
        """
        Ask the running batch, if any, to stop before its next image.
        """
        if self._job is not None:
            self._job.request.cancel()

    def stop(self) -> None:
        """
        Cancel the running batch and ask the worker thread to quit after the current image, without waiting.

        Requests made afterwards are not sent to the worker; the outcomes it already produced are still reported.
        """
        if self._is_stopped:
            return
        self._is_stopped = True
        self._waiting_background_request = None
        self._waiting_foreground_run = None
        self.cancel_batch()
        self._inbox.put(None)

    def join(self) -> None:
        """
        Wait until the worker thread has quit; safe to call from any thread once ``stop`` was called.

        Raises
        ------
        RuntimeError
            If ``stop`` was not called, since the worker would never quit.
        """
        if not self._is_stopped:
            raise RuntimeError("stop must be called before join.")
        self._thread.join()

    def shutdown(self) -> None:
        """
        Cancel the running batch and stop the worker thread, waiting for the current image to finish.
        """
        self.stop()
        self.join()

    @staticmethod
    def _is_same_detection(request: DetectionRequest, other: DetectionRequest) -> bool:
        return request.image_path == other.image_path and DetectorProfile.of(request.settings) == DetectorProfile.of(
            other.settings
        )

    def _start(self) -> None:
        if self._is_busy:
            raise RuntimeError("A detection is already running.")
        self._set_busy(True)

    def _set_busy(self, is_busy: bool) -> None:
        self._is_busy = is_busy
        self._listener.on_busy_changed(is_busy)

    def _queue_foreground(self, run: DetectionRequest | BatchJob) -> None:
        self._waiting_background_request = None
        if self._background_request is None:
            self._send_foreground(run)
        else:
            self._waiting_foreground_run = run

    def _send_foreground(self, run: DetectionRequest | BatchJob) -> None:
        if self._is_stopped:
            return
        match run:
            case BatchJob():
                self._inbox.put(run.request)
            case DetectionRequest():
                self._inbox.put(run)

    def _send_background(self, request: DetectionRequest) -> None:
        if self._is_stopped:
            return
        self._background_request = request
        self._inbox.put(request)

    def _send_waiting_run(self) -> None:
        foreground_run: DetectionRequest | BatchJob | None = self._waiting_foreground_run
        background_request: DetectionRequest | None = self._waiting_background_request
        self._waiting_foreground_run = None
        self._waiting_background_request = None
        if foreground_run is not None:
            self._send_foreground(foreground_run)
        elif background_request is not None:
            self._send_background(background_request)

    def _finish_batch(self) -> BatchJob | None:
        job: BatchJob | None = self._job
        self._job = None
        return job

    def _on_status_changed(self, message: str) -> None:
        self._listener.on_status_changed(message)

    def _on_succeeded(self, outcome: DetectionOutcome) -> None:
        if self._background_request is not None:
            self._background_request = None
            self._send_waiting_run()
            self._listener.on_background_succeeded(outcome)
            return
        try:
            self._listener.on_succeeded(outcome)
        finally:
            self._set_busy(False)

    def _on_failed(self, request: DetectionRequest, failure: DetectionFailure) -> None:
        if self._background_request is not None:
            self._background_request = None
            self._send_waiting_run()
            self._listener.on_background_failed(request, failure)
            return
        try:
            self._listener.on_failed(failure)
        finally:
            self._set_busy(False)

    def _on_batch_progressed(self, processed_count: int, total_count: int) -> None:
        if self._job is not None:
            self._listener.on_batch_progressed(self._job, processed_count, total_count)

    def _on_image_detected(self, image_path: Path, result: DetectionResult) -> None:
        if self._job is not None:
            self._listener.on_batch_image_detected(self._job, image_path, result)

    def _on_batch_finished(self, summary: BatchDetectionSummary) -> None:
        job: BatchJob | None = self._finish_batch()
        try:
            if job is not None:
                self._listener.on_batch_finished(job, summary)
        finally:
            self._set_busy(False)

    def _on_batch_failed(self, message: str) -> None:
        job: BatchJob | None = self._finish_batch()
        try:
            if job is not None:
                self._listener.on_batch_failed(job, message)
        finally:
            self._set_busy(False)

    def _work(self) -> None:
        while (item := self._inbox.get()) is not None:
            match item:
                case BatchDetectionRequest():
                    self._run_batch(item)
                case DetectionRequest():
                    self._run(item)

    def _report_status(self, message: str) -> None:
        self._scheduler.dispatch(lambda: self._on_status_changed(message))

    def _run(self, request: DetectionRequest) -> None:
        if not self._session.is_loaded_for(request.settings):
            self._report_status(f"Loading {request.settings.weights_path} ...")
        else:
            self._report_status(f"Detecting {request.image_path.name} ...")
        try:
            loaded_image: LoadedImage = LoadedImage.open(request.image_path)
        except Exception as error:
            unreadable: DetectionFailure = DetectionFailure.of(DetectionFailureKind.UNREADABLE_IMAGE, error)
            self._scheduler.dispatch(lambda: self._on_failed(request, unreadable))
            return
        try:
            outcome: DetectionOutcome = self._session.detect(request, loaded_image.image)
        except Exception as error:
            failure: DetectionFailure = DetectionFailure.of(DetectionFailureKind.DETECTION_ERROR, error)
            self._scheduler.dispatch(lambda: self._on_failed(request, failure))
            return
        self._scheduler.dispatch(lambda: self._on_succeeded(outcome))

    def _run_batch(self, request: BatchDetectionRequest) -> None:
        total_count: int = len(request.image_paths)
        detected_count: int = 0
        unreadable_paths: list[Path] = []
        if not self._session.is_loaded_for(request.settings):
            self._report_status(f"Loading {request.settings.weights_path} ...")
        while (image_path := request.take_next_image()) is not None:
            processed_count: int = detected_count + len(unreadable_paths)
            self._scheduler.dispatch(partial(self._on_batch_progressed, processed_count, total_count))
            try:
                loaded_image: LoadedImage = LoadedImage.open(image_path)
            except Exception:
                unreadable_paths.append(image_path)
                continue
            self._report_status(f"Detecting {image_path.name} ({processed_count + 1}/{total_count}) ...")
            try:
                outcome: DetectionOutcome = self._session.detect(
                    DetectionRequest(
                        settings=request.settings, image_path=image_path, labeled_prompt=request.labeled_prompt
                    ),
                    loaded_image.image,
                )
            except Exception as error:
                message: str = f"{image_path.name}: {type(error).__name__}: {error}"
                self._scheduler.dispatch(partial(self._on_batch_failed, message))
                return
            detected_count += 1
            self._scheduler.dispatch(partial(self._on_image_detected, image_path, outcome.result))
        is_cancelled: bool = detected_count + len(unreadable_paths) < total_count
        if not is_cancelled:
            self._scheduler.dispatch(lambda: self._on_batch_progressed(total_count, total_count))
        summary: BatchDetectionSummary = BatchDetectionSummary(
            detected_count=detected_count, unreadable_paths=tuple(unreadable_paths), is_cancelled=is_cancelled
        )
        self._scheduler.dispatch(lambda: self._on_batch_finished(summary))
