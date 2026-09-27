from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

from .collapsible_section import CollapsibleSection


class SectionStack(QScrollArea):
    """
    Vertical stack of collapsible sections.

    Expanded stretched sections share the spare height; when every section is folded, the headers stay at the top.
    The stack scrolls when the expanded sections do not fit.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Parameters
        ----------
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self._sections: list[CollapsibleSection] = []
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        stack: QWidget = QWidget()
        self._layout: QVBoxLayout = QVBoxLayout(stack)
        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setSpacing(8)
        self._layout.addStretch(0)
        self.setWidget(stack)

    @property
    def sections(self) -> tuple[CollapsibleSection, ...]:
        """
        Sections from top to bottom.

        Returns
        -------
        tuple[CollapsibleSection, ...]
            Every added section.
        """
        return tuple(self._sections)

    def add_section(self, title: str, content: QWidget, is_stretched: bool) -> CollapsibleSection:
        """
        Append a section below the existing ones.

        Parameters
        ----------
        title : str
            Text of the header.
        content : QWidget
            Widget shown while the section is expanded.
        is_stretched : bool
            Whether the expanded section takes up spare height.

        Returns
        -------
        CollapsibleSection
            The added section.
        """
        section: CollapsibleSection = CollapsibleSection(title, content, is_stretched)
        self._layout.insertWidget(len(self._sections), section)
        self._sections.append(section)
        section.expanded_changed.connect(self._on_section_toggled)
        self._update_stretches()
        return section

    def _on_section_toggled(self, is_expanded: bool) -> None:
        self._update_stretches()

    def _update_stretches(self) -> None:
        for section in self._sections:
            self._layout.setStretchFactor(section, 1 if section.is_stretching else 0)
        is_any_stretching: bool = any(candidate.is_stretching for candidate in self._sections)
        self._layout.setStretch(self._layout.count() - 1, 0 if is_any_stretching else 1)
