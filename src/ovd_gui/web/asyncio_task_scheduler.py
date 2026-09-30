import asyncio
from collections.abc import Callable

from ..workspace import ScheduledCall


class AsyncioTaskScheduler:
    """
    ``TaskScheduler`` running the workspace on the event loop of the web server.

    The event loop plays the role of the GUI thread: request handlers and every callback run on it, and blocking work
    runs in the default executor.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        """
        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            Running event loop of the server.
        """
        self._loop: asyncio.AbstractEventLoop = loop

    def dispatch(self, callback: Callable[[], None]) -> None:
        """
        Run a callback on the event loop soon; safe to call from any thread.

        Parameters
        ----------
        callback : Callable[[], None]
            Work to run.
        """
        self._loop.call_soon_threadsafe(callback)

    def call_later(self, delay_seconds: float, callback: Callable[[], None]) -> ScheduledCall:
        """
        Run a callback on the event loop after a delay.

        Parameters
        ----------
        delay_seconds : float
            Delay before the callback runs.
        callback : Callable[[], None]
            Work to run.

        Returns
        -------
        ScheduledCall
            Handle cancelling the callback.
        """
        return self._loop.call_later(delay_seconds, callback)

    def run_blocking[ResultT](
        self,
        task: Callable[[], ResultT],
        on_done: Callable[[ResultT], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        """
        Run blocking work in the default executor and report its outcome on the event loop.

        Parameters
        ----------
        task : Callable[[], ResultT]
            Work to run on another thread.
        on_done : Callable[[ResultT], None]
            Called on the event loop with the result of ``task``.
        on_error : Callable[[Exception], None]
            Called on the event loop with the error ``task`` raised.
        """
        future: asyncio.Future[ResultT] = self._loop.run_in_executor(None, task)

        def report(finished: asyncio.Future[ResultT]) -> None:
            error: BaseException | None = finished.exception()
            match error:
                case None:
                    on_done(finished.result())
                case Exception():
                    on_error(error)
                case _:
                    raise error

        future.add_done_callback(report)
