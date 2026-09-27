import json
from typing import cast

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]


class JsonFields:
    """
    Typed access to the values of parsed JSON, raising ``TypeError`` naming the field when a value has another type.
    """

    @staticmethod
    def parse(text: str) -> JsonValue:
        """
        Parse JSON text.

        Parameters
        ----------
        text : str
            JSON document.

        Returns
        -------
        JsonValue
            Parsed value.

        Raises
        ------
        json.JSONDecodeError
            If ``text`` is not valid JSON.
        """
        return cast(JsonValue, json.loads(text))

    @staticmethod
    def object_of(value: JsonValue, description: str) -> dict[str, JsonValue]:
        """
        Read a JSON object.

        Parameters
        ----------
        value : JsonValue
            Parsed value.
        description : str
            Name of the field, used in the error message.

        Returns
        -------
        dict[str, JsonValue]
            The object.

        Raises
        ------
        TypeError
            If ``value`` is not an object.
        """
        if not isinstance(value, dict):
            raise TypeError(f"{description} must be a JSON object. got {type(value).__name__}")
        return value

    @staticmethod
    def list_of(value: JsonValue, description: str) -> list[JsonValue]:
        """
        Read a JSON array.

        Parameters
        ----------
        value : JsonValue
            Parsed value.
        description : str
            Name of the field, used in the error message.

        Returns
        -------
        list[JsonValue]
            The array.

        Raises
        ------
        TypeError
            If ``value`` is not an array.
        """
        if not isinstance(value, list):
            raise TypeError(f"{description} must be a JSON array. got {type(value).__name__}")
        return value

    @staticmethod
    def string_of(value: JsonValue, description: str) -> str:
        """
        Read a JSON string.

        Parameters
        ----------
        value : JsonValue
            Parsed value.
        description : str
            Name of the field, used in the error message.

        Returns
        -------
        str
            The string.

        Raises
        ------
        TypeError
            If ``value`` is not a string.
        """
        if not isinstance(value, str):
            raise TypeError(f"{description} must be a string. got {type(value).__name__}")
        return value

    @staticmethod
    def number_of(value: JsonValue, description: str) -> float:
        """
        Read a JSON number.

        Parameters
        ----------
        value : JsonValue
            Parsed value.
        description : str
            Name of the field, used in the error message.

        Returns
        -------
        float
            The number.

        Raises
        ------
        TypeError
            If ``value`` is not a number; booleans are rejected.
        """
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise TypeError(f"{description} must be a number. got {value!r}")
        return float(value)

    @staticmethod
    def integer_of(value: JsonValue, description: str) -> int:
        """
        Read a JSON integer.

        Parameters
        ----------
        value : JsonValue
            Parsed value.
        description : str
            Name of the field, used in the error message.

        Returns
        -------
        int
            The integer.

        Raises
        ------
        TypeError
            If ``value`` is not an integer; booleans are rejected.
        """
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{description} must be an integer. got {value!r}")
        return value

    @staticmethod
    def boolean_of(value: JsonValue, description: str) -> bool:
        """
        Read a JSON boolean.

        Parameters
        ----------
        value : JsonValue
            Parsed value.
        description : str
            Name of the field, used in the error message.

        Returns
        -------
        bool
            The boolean.

        Raises
        ------
        TypeError
            If ``value`` is not a boolean.
        """
        if not isinstance(value, bool):
            raise TypeError(f"{description} must be a boolean. got {value!r}")
        return value
