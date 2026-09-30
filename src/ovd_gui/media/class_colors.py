from typing import ClassVar


class ClassColors:
    """
    Distinct, stable colors of class ids, shared by every view and by the images saved with boxes drawn.
    """

    HEX_COLORS: ClassVar[tuple[str, ...]] = (
        "#e6194b",
        "#3cb44b",
        "#4363d8",
        "#f58231",
        "#911eb4",
        "#42d4f4",
        "#f032e6",
        "#bfef45",
        "#fabed4",
        "#469990",
        "#dcbeff",
        "#9a6324",
        "#fffac8",
        "#800000",
        "#aaffc3",
        "#808000",
        "#ffd8b1",
        "#000075",
    )

    @classmethod
    def hex_of(cls, class_id: int) -> str:
        """
        Color of a class.

        Parameters
        ----------
        class_id : int
            Class id, cycling through the colors.

        Returns
        -------
        str
            ``#rrggbb`` color.

        Raises
        ------
        ValueError
            If ``class_id`` is negative.
        """
        if class_id < 0:
            raise ValueError(f"class_id must not be negative. got {class_id}")
        return cls.HEX_COLORS[class_id % len(cls.HEX_COLORS)]
