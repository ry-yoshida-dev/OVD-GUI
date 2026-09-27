from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QFormLayout, QLabel, QWidget

from .number_span import NumberSpan
from .range_condition import RangeCondition
from .result_column import ResultColumn


class RangeEditor(QWidget):
    """
    Editor of a ``RangeCondition``: optional lower and upper bounds of a numeric column.

    Editing a bound turns it on; leaving both off means no condition.
    """

    COORDINATE_LIMIT = 1_000_000.0

    def __init__(
        self,
        column: ResultColumn,
        span: NumberSpan | None,
        condition: RangeCondition | None,
        parent: QWidget | None = None,
    ) -> None:
        """
        Parameters
        ----------
        column : ResultColumn
            Numeric column to filter.
        span : NumberSpan | None
            Values found in the column, shown as a hint and used as the starting bounds; ``None`` when there are none.
        condition : RangeCondition | None
            Condition in effect, whose bounds start on; ``None`` starts with both bounds off.
        parent : QWidget | None, optional
            Parent widget.

        Raises
        ------
        ValueError
            If ``column`` is not numeric.
        """
        super().__init__(parent)
        if not column.is_numeric:
            raise ValueError(f"{column.header} is not a numeric column")
        self._column: ResultColumn = column
        self._minimum_check: QCheckBox = QCheckBox("Min ≥")
        self._maximum_check: QCheckBox = QCheckBox("Max ≤")
        self._minimum_spin: QDoubleSpinBox = self._bound_spin()
        self._maximum_spin: QDoubleSpinBox = self._bound_spin()
        if span is not None:
            self._minimum_spin.setValue(span.smallest)
            self._maximum_spin.setValue(span.largest)
        if condition is not None:
            self._set_bound(self._minimum_check, self._minimum_spin, condition.minimum)
            self._set_bound(self._maximum_check, self._maximum_spin, condition.maximum)
        span_text: str = "No values" if span is None else f"Values: {span.smallest:g} – {span.largest:g}"

        layout: QFormLayout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addRow(self._minimum_check, self._minimum_spin)
        layout.addRow(self._maximum_check, self._maximum_spin)
        layout.addRow(QLabel(span_text))

        self._minimum_spin.valueChanged.connect(lambda: self._minimum_check.setChecked(True))
        self._maximum_spin.valueChanged.connect(lambda: self._maximum_check.setChecked(True))

    @property
    def condition(self) -> RangeCondition | None:
        """
        Condition chosen by the bounds.

        Returns
        -------
        RangeCondition | None
            Bounds turned on, ordered so that the lower one comes first, or ``None`` when both are off.
        """
        minimum: float | None = self._minimum_spin.value() if self._minimum_check.isChecked() else None
        maximum: float | None = self._maximum_spin.value() if self._maximum_check.isChecked() else None
        if minimum is None and maximum is None:
            return None
        if minimum is not None and maximum is not None and minimum > maximum:
            minimum, maximum = maximum, minimum
        return RangeCondition(minimum, maximum)

    def set_minimum(self, value: float | None) -> None:
        """
        Turn the lower bound on at a value, or off.

        Parameters
        ----------
        value : float | None
            Lowest accepted value; ``None`` turns the bound off.
        """
        self._set_bound(self._minimum_check, self._minimum_spin, value)

    def set_maximum(self, value: float | None) -> None:
        """
        Turn the upper bound on at a value, or off.

        Parameters
        ----------
        value : float | None
            Highest accepted value; ``None`` turns the bound off.
        """
        self._set_bound(self._maximum_check, self._maximum_spin, value)

    @staticmethod
    def _set_bound(check: QCheckBox, spin: QDoubleSpinBox, value: float | None) -> None:
        if value is not None:
            spin.setValue(value)
        check.setChecked(value is not None)

    def _bound_spin(self) -> QDoubleSpinBox:
        spin: QDoubleSpinBox = QDoubleSpinBox()
        match self._column:
            case ResultColumn.CONFIDENCE:
                spin.setRange(0.0, 1.0)
                spin.setDecimals(3)
                spin.setSingleStep(0.05)
            case _:
                spin.setRange(-self.COORDINATE_LIMIT, self.COORDINATE_LIMIT)
                spin.setDecimals(1)
                spin.setSingleStep(1.0)
        return spin
