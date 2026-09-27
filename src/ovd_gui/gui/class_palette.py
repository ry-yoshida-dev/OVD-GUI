from PySide6.QtGui import QColor, QIcon, QPixmap


class ClassPalette:
    """
    Distinct, stable colors for class ids.
    """

    HEX_COLORS: tuple[str, ...] = (
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
    SWATCH_SIZE = 12

    def color_of(self, class_id: int) -> QColor:
        """
        Color of a class.

        Parameters
        ----------
        class_id : int
            Class index of the prompt.

        Returns
        -------
        QColor
            Color cycling through ``HEX_COLORS``.

        Raises
        ------
        ValueError
            If ``class_id`` is negative.
        """
        if class_id < 0:
            raise ValueError(f"class_id must not be negative. got {class_id}")
        return QColor(self.HEX_COLORS[class_id % len(self.HEX_COLORS)])

    def swatch_of(self, class_id: int) -> QIcon:
        """
        Small square icon filled with the color of a class.

        Parameters
        ----------
        class_id : int
            Class index of the prompt.

        Returns
        -------
        QIcon
            Swatch of ``SWATCH_SIZE`` pixels.
        """
        swatch: QPixmap = QPixmap(self.SWATCH_SIZE, self.SWATCH_SIZE)
        swatch.fill(self.color_of(class_id))
        return QIcon(swatch)

    @staticmethod
    def text_color_on(background: QColor) -> QColor:
        """
        Black or white, whichever reads better on ``background``.

        Parameters
        ----------
        background : QColor
            Fill color behind the text.

        Returns
        -------
        QColor
            Black on light backgrounds, white otherwise.
        """
        luminance: float = 0.299 * background.redF() + 0.587 * background.greenF() + 0.114 * background.blueF()
        return QColor("black") if luminance > 0.6 else QColor("white")
