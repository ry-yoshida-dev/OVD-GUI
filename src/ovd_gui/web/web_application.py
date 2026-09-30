import asyncio
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from pathlib import Path
from typing import ClassVar

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ..detection import DetectorSession
from ..workspace import ModelSelector, Workspace, WorkspaceStores
from .access_guard import AccessGuard
from .asyncio_task_scheduler import AsyncioTaskScheduler
from .class_routes import ClassRoutes
from .detection_routes import DetectionRoutes
from .export_routes import ExportRoutes
from .image_routes import ImageRoutes
from .web_context import WebContext


class WebApplication:
    """
    Web server of the application: a JSON API over the workspace, a WebSocket telling the browsers what changed, and
    the single-page user interface built into ``static``.

    The workspace is created when the server starts, on its event loop, and shut down with it. Errors caused by the
    request, such as an invalid class name or an unknown image, are answered with status 400 and their message. Only a
    browser that opened the address with the access token can use the server (see ``AccessGuard``).
    """

    STATIC_DIRECTORY: ClassVar[Path] = Path(__file__).parent / "static"
    MISSING_FRONTEND_PAGE: ClassVar[str] = (
        "<!doctype html><title>OVD GUI</title><h1>OVD GUI</h1>"
        + "<p>The web interface has not been built. Run <code>npm install && npm run build</code> in "
        + "<code>frontend/</code>; the API is served under <code>/api</code>.</p>"
    )

    def __init__(
        self,
        model_selector: ModelSelector,
        stores: WorkspaceStores,
        initial_paths: Sequence[Path],
        working_directory: Path,
        access_token: str,
        cookie_name: str,
        session: DetectorSession | None = None,
    ) -> None:
        """
        Parameters
        ----------
        model_selector : ModelSelector
            Presets that can be chosen and the devices of this machine.
        stores : WorkspaceStores
            Data directories of the workspace.
        initial_paths : Sequence[Path]
            Images or directories opened at start; without any, the images of the last session are opened again.
        working_directory : Path
            Directory the server was started in.
        access_token : str
            Secret a browser presents once, in the ``token`` query parameter, to use the server.
        cookie_name : str
            Name of the cookie keeping the access token in the browser.
        session : DetectorSession | None, optional
            Session keeping the loaded model; a new one by default.
        """
        self._model_selector: ModelSelector = model_selector
        self._stores: WorkspaceStores = stores
        self._initial_paths: tuple[Path, ...] = tuple(initial_paths)
        self._session: DetectorSession | None = session
        self._access_token: str = access_token
        self._cookie_name: str = cookie_name
        self._context: WebContext = WebContext(working_directory)

    @property
    def context(self) -> WebContext:
        """
        Workspace and helpers shared by the request handlers.

        Returns
        -------
        WebContext
            Context of the application.
        """
        return self._context

    def build(self) -> FastAPI:
        """
        Assemble the ASGI application.

        Returns
        -------
        FastAPI
            Application serving the API, the event WebSocket and the user interface.
        """
        application: FastAPI = FastAPI(title="OVD GUI", lifespan=self._lifespan)
        application.add_middleware(AccessGuard, token=self._access_token, cookie_name=self._cookie_name)
        for error_type in (ValueError, KeyError, IndexError, OSError):
            application.add_exception_handler(error_type, self._client_error)
        for routes in (
            ImageRoutes(self._context),
            DetectionRoutes(self._context),
            ClassRoutes(self._context),
            ExportRoutes(self._context),
        ):
            application.include_router(routes.router())
        context: WebContext = self._context

        @application.websocket("/api/events")
        async def events(socket: WebSocket) -> None:
            await context.hub.serve(socket)

        if (self.STATIC_DIRECTORY / "index.html").is_file():
            application.mount("/", StaticFiles(directory=self.STATIC_DIRECTORY, html=True), name="static")
        else:

            @application.get("/")
            async def missing_frontend() -> HTMLResponse:
                return HTMLResponse(self.MISSING_FRONTEND_PAGE)

        return application

    @asynccontextmanager
    async def _lifespan(self, application: FastAPI) -> AsyncGenerator[None]:
        workspace: Workspace = Workspace(
            self._model_selector,
            self._stores,
            AsyncioTaskScheduler(asyncio.get_running_loop()),
            self._session,
        )
        self._context.attach(workspace)
        if self._initial_paths:
            workspace.open_paths(self._initial_paths)
        else:
            workspace.restore_session()
        try:
            yield
        finally:
            self._context.detach()
            workspace.stop_detection()
            await asyncio.to_thread(workspace.join_detection)
            await asyncio.sleep(0)
            workspace.save()

    @staticmethod
    async def _client_error(request: Request, error: Exception) -> JSONResponse:
        message: str = str(error.args[0]) if isinstance(error, KeyError) and error.args else str(error)
        return JSONResponse(status_code=400, content={"detail": message})
