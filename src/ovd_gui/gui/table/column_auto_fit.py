from collections.abc import Callable

from PySide6.QtWidgets import QHeaderView


class ColumnAutoFit:
    """
    Sizes the columns of a view to a width chosen per column until the user resizes one, then leaves every width
    alone.

    The header is made interactive, so every column can be resized by dragging its edge; double-clicking an edge fits
    that column to its contents and header again.
    """

    def __init__(self, header: QHeaderView, width_of: Callable[[int], int]) -> None:
        """
        Parameters
        ----------
        header : QHeaderView
            Header of the view whose columns are sized.
        width_of : Callable[[int], int]
            Default width of one column, by logical index, e.g. the width of its cells.
        """
        self._header: QHeaderView = header
        self._width_of: Callable[[int], int] = width_of
        self._is_fitting: bool = False
        self._is_customized: bool = False
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.sectionResized.connect(self._on_section_resized)

    @property
    def is_customized(self) -> bool:
        """
        Whether the user has resized a column.

        Returns
        -------
        bool
            True from the first resize by the user on.
        """
        return self._is_customized

    def fit(self) -> None:
        """
        Give every column its default width, unless the user has resized one.
        """
        if self._is_customized:
            return
        self._is_fitting = True
        for logical_index in range(self._header.count()):
            self._header.resizeSection(logical_index, self._width_of(logical_index))
        self._is_fitting = False

    def _on_section_resized(self, logical_index: int, old_size: int, new_size: int) -> None:
        if not self._is_fitting:
            self._is_customized = True
