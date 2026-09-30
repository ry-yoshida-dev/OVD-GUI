import asyncio
from typing import ClassVar

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from ..workspace import Notice, WorkspaceTopic
from .json_value import JsonObject, JsonValue


class EventHub:
    """
    Pushes the changes and notices of the workspace to every connected browser over WebSockets.

    Changes arriving in quick succession, such as the results of a batch, are merged into one message naming every
    changed topic, so browsers fetch each part once. Notices are sent at once.
    """

    FLUSH_DELAY_SECONDS: ClassVar[float] = 0.05

    def __init__(self) -> None:
        self._sockets: set[WebSocket] = set()
        self._pending_topics: set[WorkspaceTopic] = set()
        self._flush_handle: asyncio.TimerHandle | None = None
        self._send_tasks: set[asyncio.Task[None]] = set()

    async def serve(self, socket: WebSocket) -> None:
        """
        Keep one browser connected until it leaves.

        Parameters
        ----------
        socket : WebSocket
            Connection of the browser, not accepted yet.
        """
        await socket.accept()
        self._sockets.add(socket)
        try:
            while True:
                await socket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            self._sockets.discard(socket)

    def on_changed(self, topics: frozenset[WorkspaceTopic]) -> None:
        """
        Tell the browsers shortly which parts of the workspace changed.

        Parameters
        ----------
        topics : frozenset[WorkspaceTopic]
            Changed parts.
        """
        self._pending_topics.update(topics)
        if self._flush_handle is None:
            self._flush_handle = asyncio.get_running_loop().call_later(self.FLUSH_DELAY_SECONDS, self._flush)

    def on_notice(self, notice: Notice) -> None:
        """
        Show a notice in every browser.

        Parameters
        ----------
        notice : Notice
            Message for the user.
        """
        self._broadcast(
            {"type": "notice", "level": notice.level.value, "title": notice.title, "message": notice.message}
        )

    def _flush(self) -> None:
        self._flush_handle = None
        topics: list[JsonValue] = [topic.value for topic in sorted(self._pending_topics, key=lambda topic: topic.value)]
        self._pending_topics.clear()
        self._broadcast({"type": "changed", "topics": topics})

    def _broadcast(self, message: JsonObject) -> None:
        for socket in tuple(self._sockets):
            task: asyncio.Task[None] = asyncio.get_running_loop().create_task(self._send(socket, message))
            self._send_tasks.add(task)
            task.add_done_callback(self._send_tasks.discard)

    async def _send(self, socket: WebSocket, message: JsonObject) -> None:
        try:
            await socket.send_json(message)
        except (WebSocketDisconnect, RuntimeError):
            self._sockets.discard(socket)
