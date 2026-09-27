from PySide6.QtWidgets import QDoubleSpinBox, QWidget


class MinimumSpinBox(QDoubleSpinBox):
    """
    Spin box of an optional minimum confidence: ``Default`` below 0 means the class uses the default minimum.
    """

    DEFAULT_TEXT = "Default"
    STEP = 0.05

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Parameters
        ----------
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self.setDecimals(2)
        self.setSingleStep(self.STEP)
        self.setRange(-self.STEP, 1.0)
        self.setSpecialValueText(self.DEFAULT_TEXT)
        self.setValue(-self.STEP)

    @property
    def minimum_confidence(self) -> float | None:
        """
        Chosen minimum.

        Returns
        -------
        float | None
            Minimum in ``[0, 1]``, or ``None`` while ``Default`` is shown.
        """
        return None if self.value() < 0.0 else self.value()

    def set_minimum_confidence(self, minimum_confidence: float | None) -> None:
        """
        Show a minimum without reporting it as a change.

        Parameters
        ----------
        minimum_confidence : float | None
            Minimum in ``[0, 1]``, or ``None`` for ``Default``.
        """
        self.blockSignals(True)
        self.setValue(-self.STEP if minimum_confidence is None else minimum_confidence)
        self.blockSignals(False)
