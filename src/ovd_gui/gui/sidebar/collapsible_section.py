from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QPushButton, QSizePolicy, QVBoxLayout, QWidget


class CollapsibleSection(QWidget):
    """
    Titled section whose content folds away when its header is clicked.

    The header is a flat, uppercase caption with a chevron and a thin rule above it, so that it reads as the top
    edge of its content rather than as a separate button.

    Signals
    -------
    expanded_changed : Signal(bool)
        The section was expanded (True) or collapsed (False).
    """

    expanded_changed: Signal = Signal(bool)

    EXPANDED_CHEVRON = "\u25bc"
    COLLAPSED_CHEVRON = "\u25b6"
    HEADER_STYLE_SHEET = (
        "QPushButton#SectionHeader { border: none; border-top: 1px solid palette(mid); background: transparent; "
        + "padding: 6px 2px 4px 2px; min-height: 0px; text-align: left; color: palette(text); }"
        + "QPushButton#SectionHeader:hover { color: palette(highlight); }"
    )

    def __init__(self, title: str, content: QWidget, is_stretched: bool, parent: QWidget | None = None) -> None:
        """
        Parameters
        ----------
        title : str
            Text of the header.
        content : QWidget
            Widget shown while the section is expanded.
        is_stretched : bool
            Whether the expanded section takes up spare height, e.g. for lists and tables.
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self._content: QWidget = content
        self._is_stretched: bool = is_stretched
        self._is_expanded: bool = True
        self._title: str = title

        self._header: QPushButton = QPushButton()
        self._header.setFlat(True)
        self._header.setObjectName("SectionHeader")
        self._header.setStyleSheet(self.HEADER_STYLE_SHEET)
        self._header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        header_font: QFont = QFont(self._header.font())
        header_font.setWeight(QFont.Weight.Bold)
        header_font.setPointSizeF(header_font.pointSizeF() * 0.85)
        header_font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 108)
        self._header.setFont(header_font)
        self._header.clicked.connect(self.toggle)
        self._update_header()

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self._header)
        layout.addWidget(content, stretch=1)
        self._apply_size_policy()

    @property
    def is_expanded(self) -> bool:
        """
        Whether the content is shown.

        Returns
        -------
        bool
            True while expanded.
        """
        return self._is_expanded

    @property
    def is_stretching(self) -> bool:
        """
        Whether the section currently wants spare height.

        Returns
        -------
        bool
            True for an expanded section created with ``is_stretched``.
        """
        return self._is_stretched and self._is_expanded

    def set_title(self, title: str) -> None:
        """
        Change the header text.

        Parameters
        ----------
        title : str
            New header text.
        """
        self._title = title
        self._update_header()

    def set_expanded(self, is_expanded: bool) -> None:
        """
        Show or fold the content.

        Parameters
        ----------
        is_expanded : bool
            True to show the content.
        """
        if is_expanded == self._is_expanded:
            return
        self._is_expanded = is_expanded
        self._content.setVisible(is_expanded)
        self._update_header()
        self._apply_size_policy()
        self.expanded_changed.emit(is_expanded)

    def toggle(self) -> None:
        """
        Fold an expanded section or expand a folded one.
        """
        self.set_expanded(not self._is_expanded)

    def _update_header(self) -> None:
        chevron: str = self.EXPANDED_CHEVRON if self._is_expanded else self.COLLAPSED_CHEVRON
        self._header.setText(f"{chevron}  {self._title.upper()}")

    def _apply_size_policy(self) -> None:
        vertical_policy: QSizePolicy.Policy = (
            QSizePolicy.Policy.Expanding if self.is_stretching else QSizePolicy.Policy.Maximum
        )
        self.setSizePolicy(QSizePolicy.Policy.Preferred, vertical_policy)
