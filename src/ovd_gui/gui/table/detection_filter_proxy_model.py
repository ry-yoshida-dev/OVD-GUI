from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QSortFilterProxyModel

from ...detection import DetectionFilter, DetectionRecord
from .detection_record_model import DetectionRecordModel


class DetectionFilterProxyModel(QSortFilterProxyModel):
    """
    Sorted view of a ``DetectionRecordModel`` listing only the detections accepted by a ``DetectionFilter``.
    """

    def __init__(self, source_model: DetectionRecordModel) -> None:
        """
        Parameters
        ----------
        source_model : DetectionRecordModel
            Detections to filter and sort.
        """
        super().__init__()
        self._source_model: DetectionRecordModel = source_model
        self._detection_filter: DetectionFilter = DetectionFilter()
        self.setSourceModel(source_model)
        self.setSortRole(DetectionRecordModel.SORT_ROLE)
        self.setDynamicSortFilter(True)

    @property
    def detection_filter(self) -> DetectionFilter:
        """
        Conditions of the listed detections.

        Returns
        -------
        DetectionFilter
            Filter in effect.
        """
        return self._detection_filter

    def set_detection_filter(self, detection_filter: DetectionFilter) -> None:
        """
        List only the detections accepted by ``detection_filter``.

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

    def record_at(self, proxy_row: int) -> DetectionRecord:
        """
        Detection of one listed row.

        Parameters
        ----------
        proxy_row : int
            Row of this proxy.

        Returns
        -------
        DetectionRecord
            Detection shown in ``proxy_row``.
        """
        return self._source_model.record_at(self.mapToSource(self.index(proxy_row, 0)).row())

    def visible_records(self) -> tuple[DetectionRecord, ...]:
        """
        Listed detections in display order.

        Returns
        -------
        tuple[DetectionRecord, ...]
            Every row passing the filter.
        """
        return tuple(self.record_at(proxy_row) for proxy_row in range(self.rowCount()))

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex | QPersistentModelIndex) -> bool:
        return self._detection_filter.accepts(self._source_model.record_at(source_row))
