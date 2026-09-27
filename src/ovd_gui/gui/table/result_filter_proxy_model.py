from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPalette

from ...detection import DetectionRecord
from ...review import ClassThresholds
from .column_condition import ColumnCondition
from .funnel_icon import FunnelIcon
from .number_span import NumberSpan
from .range_condition import RangeCondition
from .result_column import ResultColumn
from .result_row import ResultRow
from .result_row_model import ResultRowModel
from .table_filter import TableFilter
from .value_condition import ValueCondition


class ResultFilterProxyModel(QSortFilterProxyModel):
    """
    Sorted view of a ``ResultRowModel`` listing only the rows passing a ``TableFilter``.

    Detections below the minimum confidence of their class are never listed, whatever the filter. The header of a
    filtered column carries a filled funnel icon and a tooltip naming its condition; other headers carry no icon.
    """

    def __init__(self, source_model: ResultRowModel) -> None:
        """
        Parameters
        ----------
        source_model : ResultRowModel
            Rows to filter and sort.
        """
        super().__init__()
        self._source_model: ResultRowModel = source_model
        self._table_filter: TableFilter = TableFilter()
        self._class_thresholds: ClassThresholds = ClassThresholds()
        self._funnel_icons: dict[bool, QIcon] = {}
        self.setSourceModel(source_model)
        self.setSortRole(ResultRowModel.SORT_ROLE)
        self.setDynamicSortFilter(True)

    @property
    def table_filter(self) -> TableFilter:
        """
        Conditions of the listed rows.

        Returns
        -------
        TableFilter
            Filter in effect.
        """
        return self._table_filter

    def set_table_filter(self, table_filter: TableFilter) -> None:
        """
        List only the rows passing ``table_filter``.

        Parameters
        ----------
        table_filter : TableFilter
            New conditions.
        """
        if table_filter == self._table_filter:
            return
        self.beginFilterChange()
        self._table_filter = table_filter
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, len(ResultColumn) - 1)

    @property
    def class_thresholds(self) -> ClassThresholds:
        """
        Minimum confidence of each class.

        Returns
        -------
        ClassThresholds
            Thresholds in effect.
        """
        return self._class_thresholds

    def set_class_thresholds(self, class_thresholds: ClassThresholds) -> None:
        """
        List only the detections reaching the minimum confidence of their class.

        Parameters
        ----------
        class_thresholds : ClassThresholds
            New thresholds.
        """
        if class_thresholds == self._class_thresholds:
            return
        self.beginFilterChange()
        self._class_thresholds = class_thresholds
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def is_above_minimum(self, row: ResultRow) -> bool:
        """
        Whether a row reaches the minimum confidence of its class.

        Parameters
        ----------
        row : ResultRow
            Row to test.

        Returns
        -------
        bool
            False for a detection below the minimum of its class; True for image status rows.
        """
        match row:
            case DetectionRecord():
                return self._class_thresholds.accepts(row.detection.class_name, row.detection.confidence)
            case _:
                return True

    def row_at(self, proxy_row: int) -> ResultRow:
        """
        Content of one listed row.

        Parameters
        ----------
        proxy_row : int
            Row of this proxy.

        Returns
        -------
        ResultRow
            Detection or image status shown in ``proxy_row``.
        """
        return self._source_model.row_at(self.mapToSource(self.index(proxy_row, 0)).row())

    def visible_rows(self) -> tuple[ResultRow, ...]:
        """
        Listed rows in display order.

        Returns
        -------
        tuple[ResultRow, ...]
            Every row passing the filter.
        """
        return tuple(self.row_at(proxy_row) for proxy_row in range(self.rowCount()))

    def candidate_texts(self, column: ResultColumn) -> tuple[str, ...]:
        """
        Values offered when filtering a text column.

        Parameters
        ----------
        column : ResultColumn
            Column to filter.

        Returns
        -------
        tuple[str, ...]
            Distinct texts of the rows passing the conditions of the other columns, together with the values
            already checked in ``column``, sorted case-insensitively.
        """
        other_filter: TableFilter = self._table_filter.with_condition(column, None)
        texts: set[str] = {
            self._source_model.cell_text(row, column)
            for row in self._source_model.rows
            if self._passes(row, other_filter)
        }
        condition: ColumnCondition | None = self._table_filter.condition_of(column)
        if isinstance(condition, ValueCondition):
            texts |= condition.accepted_texts
        return tuple(sorted(texts, key=str.casefold))

    def number_span(self, column: ResultColumn) -> NumberSpan | None:
        """
        Smallest and largest value of a numeric column over every row.

        Parameters
        ----------
        column : ResultColumn
            Numeric column.

        Returns
        -------
        NumberSpan | None
            Span of the values, or ``None`` when no row has a value.
        """
        values: list[float] = [
            value for row in self._source_model.rows if (value := ResultRowModel.cell_number(row, column)) is not None
        ]
        return NumberSpan(min(values), max(values)) if values else None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if orientation != Qt.Orientation.Horizontal:
            return super().headerData(section, orientation, role)
        column: ResultColumn = ResultColumn(section)
        condition: ColumnCondition | None = self._table_filter.condition_of(column)
        if role == Qt.ItemDataRole.DecorationRole:
            return None if condition is None else self._funnel_icon(True)
        if role == Qt.ItemDataRole.ToolTipRole:
            if condition is None:
                return f"{column.header}: right-click to filter"
            return f"{column.header}: {condition.description}"
        return super().headerData(section, orientation, role)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex | QPersistentModelIndex) -> bool:
        return self._passes(self._source_model.row_at(source_row), self._table_filter)

    def _passes(self, row: ResultRow, table_filter: TableFilter) -> bool:
        if not self.is_above_minimum(row):
            return False
        for column, condition in table_filter.conditions.items():
            match condition:
                case ValueCondition():
                    if not condition.accepts(self._source_model.cell_text(row, column)):
                        return False
                case RangeCondition():
                    if not condition.accepts(ResultRowModel.cell_number(row, column)):
                        return False
        return True

    def _funnel_icon(self, is_filtered: bool) -> QIcon:
        if is_filtered not in self._funnel_icons:
            color_role: QPalette.ColorRole = (
                QPalette.ColorRole.Highlight if is_filtered else QPalette.ColorRole.PlaceholderText
            )
            color: QColor = QGuiApplication.palette().color(color_role)
            self._funnel_icons[is_filtered] = FunnelIcon(color, is_filtered).to_icon()
        return self._funnel_icons[is_filtered]
