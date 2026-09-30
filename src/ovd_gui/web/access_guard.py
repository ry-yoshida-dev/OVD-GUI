import secrets
from http import HTTPMethod
from typing import ClassVar
from urllib.parse import urlsplit

from starlette.datastructures import URL
from starlette.requests import HTTPConnection
from starlette.responses import PlainTextResponse, RedirectResponse
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.websockets import WebSocketClose

from .connection_kind import ConnectionKind


class AccessGuard:
    """
    ASGI middleware letting only the browser that opened the address printed at start use the server.

    The address carries a secret token; a request presenting it gets the token as a ``SameSite=Lax``, HTTP-only cookie
    and is redirected to the same address without it. Every other request, and every WebSocket, must carry the cookie.
    Pages of other sites therefore cannot use the API, neither by posting forms to it nor by rebinding their domain name
    to this machine, since their requests do not carry the cookie.

    Browsers send the cookie from pages on any port of the same host, so every WebSocket and every request that can
    change state must also come from a page of this server: its ``Origin`` header, when present, must name the host
    and port the request was sent to.
    """

    TOKEN_PARAMETER: ClassVar[str] = "token"
    FORBIDDEN_MESSAGE: ClassVar[str] = (
        "Open the address printed in the terminal where ovd-gui was started; it carries the access token."
    )
    CROSS_ORIGIN_MESSAGE: ClassVar[str] = "Requests from pages of other origins are refused."
    POLICY_VIOLATION_CODE: ClassVar[int] = 1008
    SAFE_METHODS: ClassVar[frozenset[HTTPMethod]] = frozenset({HTTPMethod.GET, HTTPMethod.HEAD, HTTPMethod.OPTIONS})

    def __init__(self, application: ASGIApp, token: str, cookie_name: str) -> None:
        """
        Parameters
        ----------
        application : ASGIApp
            Application served to the requests carrying the token.
        token : str
            Secret of this server run.
        cookie_name : str
            Name of the cookie keeping the token in the browser.

        Raises
        ------
        ValueError
            If ``token`` or ``cookie_name`` is empty.
        """
        if not token:
            raise ValueError("token must not be empty")
        if not cookie_name:
            raise ValueError("cookie_name must not be empty")
        self._application: ASGIApp = application
        self._token: str = token
        self._cookie_name: str = cookie_name

    @staticmethod
    def new_token() -> str:
        """
        Create a secret for one server run.

        Returns
        -------
        str
            URL-safe random token.
        """
        return secrets.token_urlsafe(32)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Serve a request that carries the token, and refuse any other HTTP request or WebSocket.

        Parameters
        ----------
        scope : Scope
            ASGI connection scope.
        receive : Receive
            ASGI receive channel.
        send : Send
            ASGI send channel.
        """
        connection_kind: ConnectionKind = ConnectionKind(scope["type"])
        match connection_kind:
            case ConnectionKind.LIFESPAN:
                await self._application(scope, receive, send)
            case ConnectionKind.HTTP:
                connection: HTTPConnection = HTTPConnection(scope)
                is_safe: bool = scope["method"] in self.SAFE_METHODS
                if not is_safe and not self._is_same_origin(connection):
                    await PlainTextResponse(self.CROSS_ORIGIN_MESSAGE, status_code=403)(scope, receive, send)
                elif self._is_valid(connection.query_params.get(self.TOKEN_PARAMETER)):
                    await self._remember_token(connection.url)(scope, receive, send)
                elif self._is_valid(connection.cookies.get(self._cookie_name)):
                    await self._application(scope, receive, send)
                else:
                    await PlainTextResponse(self.FORBIDDEN_MESSAGE, status_code=403)(scope, receive, send)
            case ConnectionKind.WEBSOCKET:
                socket_connection: HTTPConnection = HTTPConnection(scope)
                if self._is_same_origin(socket_connection) and self._is_valid(
                    socket_connection.cookies.get(self._cookie_name)
                ):
                    await self._application(scope, receive, send)
                else:
                    await WebSocketClose(code=self.POLICY_VIOLATION_CODE)(scope, receive, send)

    def _is_valid(self, presented_token: str | None) -> bool:
        return presented_token is not None and secrets.compare_digest(presented_token.encode(), self._token.encode())

    @staticmethod
    def _is_same_origin(connection: HTTPConnection) -> bool:
        origin: str | None = connection.headers.get("origin")
        if origin is None:
            return True
        host: str = connection.headers.get("host", "")
        return urlsplit(origin).netloc.lower() == host.lower()

    def _remember_token(self, url: URL) -> RedirectResponse:
        target: URL = url.remove_query_params(self.TOKEN_PARAMETER)
        location: str = target.path + (f"?{target.query}" if target.query else "")
        response: RedirectResponse = RedirectResponse(location, status_code=303)
        response.set_cookie(self._cookie_name, self._token, httponly=True, samesite="lax")
        return response
