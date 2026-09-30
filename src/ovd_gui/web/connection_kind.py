from enum import Enum


class ConnectionKind(Enum):
    """
    Type of an ASGI connection scope.
    """

    HTTP = "http"
    WEBSOCKET = "websocket"
    LIFESPAN = "lifespan"
