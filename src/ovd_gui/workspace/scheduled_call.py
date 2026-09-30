from typing import Protocol


class ScheduledCall(Protocol):
    """
    Callback scheduled to run later, which can still be cancelled.
    """

    def cancel(self) -> None:
        """
        Keep the callback from running; nothing happens if it already ran.
        """
        ...
