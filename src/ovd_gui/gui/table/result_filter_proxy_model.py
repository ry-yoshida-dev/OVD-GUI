from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QSortFilterProxyModel

from ...detection import DetectionFilter, DetectionRecord
from .image_status_row import ImageStatusRow
from .result_row import ResultRow
from .result_row_model import ResultRowModel


class ResultFilterProxyModel(QSortFilterProxyModel):
    """
    Sorted view of a ``ResultRowModel`` listing only the rows accepted by a ``DetectionFilter``.

    Image status rows follow ``DetectionFilter.accepts_image_without_detections``.
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
        self._detection_filter: DetectionFilter = DetectionFilter()
        self.setSourceModel(source_model)
        self.setSortRole(ResultRowModel.SORT_ROLE)
        self.setDynamicSortFilter(True)

    @property
    def detection_filter(self) -> DetectionFilter:
        """
        Conditions of the listed rows.

        Returns
        -------
        DetectionFilter
            Filter in effect.
        """
        return self._detection_filter

    def set_detection_filter(self, detection_filter: DetectionFilter) -> None:
        """
        List only the rows accepted by ``detection_filter``.

        Parameters
        ----------
        detection_filter : DetectionFilter
            New conditions.
        """
        if detection_filter == self._detection_filter:
            return
        self.beginFilterChange()
        self._detection_filter = detection_filter
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

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

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex | QPersistentModelIndex) -> bool:
        row: ResultRow = self._source_model.row_at(source_row)
        match row:
            case DetectionRecord():
                return self._detection_filter.accepts(row)
            case ImageStatusRow():
                return self._detection_filter.accepts_image_without_detections(row.image_path)
