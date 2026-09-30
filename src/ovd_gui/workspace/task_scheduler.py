from collections.abc import Callable
from typing import Protocol

from .scheduled_call import ScheduledCall


class TaskScheduler(Protocol):
    """
    Thread owning the workspace state, like the GUI thread of a desktop application.

    Every callback given to the scheduler runs on the owning thread, so the workspace never needs locks: worker
    threads hand their results back through ``dispatch``.
    """

    def dispatch(self, callback: Callable[[], None]) -> None:
        """
        Run a callback on the owning thread soon; safe to call from any thread.

        Parameters
        ----------
        callback : Callable[[], None]
            Work to run.
        """
        ...

    def call_later(self, delay_seconds: float, callback: Callable[[], None]) -> ScheduledCall:
        """
        Run a callback on the owning thread after a delay; called on the owning thread.

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
        ...

    def run_blocking[ResultT](
        self,
        task: Callable[[], ResultT],
        on_done: Callable[[ResultT], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        """
        Run blocking work, such as writing files, off the owning thread.

        Parameters
        ----------
        task : Callable[[], ResultT]
            Work to run on another thread; it must not touch the workspace state.
        on_done : Callable[[ResultT], None]
            Called on the owning thread with the result of ``task``.
        on_error : Callable[[Exception], None]
            Called on the owning thread with the error ``task`` raised.
        """
        ...
