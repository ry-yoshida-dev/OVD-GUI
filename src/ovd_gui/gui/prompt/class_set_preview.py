from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...detection import ReferenceBox, ReferenceImage
from ...storage import ClassSet, ClassSetEntry
from ..class_palette import ClassPalette
from .reference_thumbnail import ReferenceThumbnail


class ClassSetPreview(QWidget):
    """
    Read-only view of one class set: its name and counts, its classes with their text prompts, and a thumbnail of
    every image prompt with the reference boxes outlined in the class color.

    Without a selected set, or for a set that cannot be read, a centered notice replaces the content.
    """

    THUMBNAIL_EDGE = 84
    MAXIMUM_VISIBLE_CLASS_ROWS = 8
    WARNING_COLOR = QColor("#d9822b")
    THUMBNAIL_SPACING = 10
    TITLE_FONT_SCALE = 1.35
    SECTION_FONT_SCALE = 0.8
    SECTION_LETTER_SPACING = 110.0
    NOTICE_INDEX = 0
    CONTENT_INDEX = 1
    NAME_COLUMN = 0
    PHRASE_COLUMN = 1
    IMAGE_COUNT_COLUMN = 2

    def __init__(self, palette: ClassPalette, parent: QWidget | None = None) -> None:
        """
        Parameters
        ----------
        palette : ClassPalette
            Colors of the classes, by their index in the set.
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self._palette: ClassPalette = palette

        self._notice_label: QLabel = QLabel()
        self._notice_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._notice_label.setWordWrap(True)
        self._notice_label.setForegroundRole(QPalette.ColorRole.PlaceholderText)
        self._notice_label.setContentsMargins(24, 24, 24, 24)

        self._title_label: QLabel = QLabel()
        title_font: QFont = QFont(self._title_label.font())
        title_font.setPointSizeF(title_font.pointSizeF() * self.TITLE_FONT_SCALE)
        title_font.setWeight(QFont.Weight.DemiBold)
        self._title_label.setFont(title_font)
        self._title_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._meta_label: QLabel = QLabel()
        self._meta_label.setForegroundRole(QPalette.ColorRole.PlaceholderText)

        self._class_tree: QTreeWidget = QTreeWidget()
        self._class_tree.setColumnCount(3)
        self._class_tree.setHeaderHidden(True)
        self._class_tree.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._class_tree.setRootIsDecorated(False)
        self._class_tree.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._class_tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._class_tree.setFrameShape(QFrame.Shape.NoFrame)
        self._class_tree.setAlternatingRowColors(True)
        self._class_tree.setUniformRowHeights(True)
        header: QHeaderView = self._class_tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(self.NAME_COLUMN, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.PHRASE_COLUMN, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.IMAGE_COUNT_COLUMN, QHeaderView.ResizeMode.ResizeToContents)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._image_section_label: QLabel = self._section_label("IMAGE PROMPTS")
        self._thumbnail_list: QListWidget = QListWidget()
        self._thumbnail_list.setViewMode(QListView.ViewMode.IconMode)
        self._thumbnail_list.setIconSize(QSize(self.THUMBNAIL_EDGE, self.THUMBNAIL_EDGE))
        self._thumbnail_list.setSpacing(self.THUMBNAIL_SPACING // 2)
        self._thumbnail_list.setResizeMode(QListView.ResizeMode.Adjust)
        self._thumbnail_list.setMovement(QListView.Movement.Static)
        self._thumbnail_list.setWordWrap(True)
        self._thumbnail_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._thumbnail_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._thumbnail_list.setFrameShape(QFrame.Shape.NoFrame)
        self._thumbnail_list.setGridSize(
            QSize(
                self.THUMBNAIL_EDGE + self.THUMBNAIL_SPACING * 2, self.THUMBNAIL_EDGE + 3 * self.fontMetrics().height()
            )
        )

        content: QWidget = QWidget()
        content_layout: QVBoxLayout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 16, 20, 12)
        content_layout.setSpacing(4)
        content_layout.addWidget(self._title_label)
        content_layout.addWidget(self._meta_label)
        content_layout.addSpacing(14)
        content_layout.addWidget(self._section_label("CLASSES"))
        content_layout.addWidget(self._class_tree)
        content_layout.addSpacing(12)
        content_layout.addWidget(self._image_section_label)
        content_layout.addWidget(self._thumbnail_list, stretch=1)
        content_layout.addStretch(0)

        self._stack: QStackedWidget = QStackedWidget()
        self._stack.insertWidget(self.NOTICE_INDEX, self._notice_label)
        self._stack.insertWidget(self.CONTENT_INDEX, content)
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)
        self.show_notice("Select a class set to see its classes and image prompts.")

    @property
    def is_showing_content(self) -> bool:
        """
        Whether a class set is shown rather than a notice.

        Returns
        -------
        bool
            True after ``show_class_set``.
        """
        return self._stack.currentIndex() == self.CONTENT_INDEX

    @property
    def class_texts(self) -> tuple[str, ...]:
        """
        Class rows as shown, for checks and accessibility.

        Returns
        -------
        tuple[str, ...]
            ``name: phrase, phrase`` per class row.
        """
        return tuple(
            f"{item.text(self.NAME_COLUMN)}: {item.text(self.PHRASE_COLUMN)}"
            for item in (self._class_tree.topLevelItem(row) for row in range(self._class_tree.topLevelItemCount()))
            if item is not None
        )

    @property
    def thumbnail_count(self) -> int:
        """
        Number of image prompt thumbnails shown.

        Returns
        -------
        int
            One per class and reference image pair.
        """
        return self._thumbnail_list.count()

    def show_notice(self, text: str, is_warning: bool = False) -> None:
        """
        Replace the content with a centered notice.

        Parameters
        ----------
        text : str
            Notice to show.
        is_warning : bool, optional
            Whether the notice reports a problem, shown in a warning color.
        """
        self._notice_label.setText(text)
        self._notice_label.setStyleSheet(f"color: {self.WARNING_COLOR.name()};" if is_warning else "")
        self._stack.setCurrentIndex(self.NOTICE_INDEX)

    def show_class_set(self, entry: ClassSetEntry, class_set: ClassSet, saved_at_text: str) -> None:
        """
        Show a class set.

        Parameters
        ----------
        entry : ClassSetEntry
            Listed set, giving the name and counts.
        class_set : ClassSet
            Content of the set.
        saved_at_text : str
            Save time as shown in the list.
        """
        self._title_label.setText(entry.name)
        description: str = entry.summary.description if entry.summary is not None else ""
        self._meta_label.setText(
            f"{description}  ·  Saved {saved_at_text}" if description else f"Saved {saved_at_text}"
        )
        self._class_tree.clear()
        for class_index, definition in enumerate(class_set.classes):
            image_count: int = len(
                {box.reference_image for box in class_set.reference_boxes if box.class_name == definition.name}
            )
            phrases: str = ", ".join(definition.text_queries) if definition.text_queries else "—"
            image_text: str = f"{image_count} image{'' if image_count == 1 else 's'}" if image_count else ""
            class_item: QTreeWidgetItem = QTreeWidgetItem([definition.name, phrases, image_text])
            class_item.setTextAlignment(
                self.IMAGE_COUNT_COLUMN, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            class_item.setForeground(self.IMAGE_COUNT_COLUMN, self.palette().color(QPalette.ColorRole.PlaceholderText))
            class_item.setIcon(self.NAME_COLUMN, self._palette.swatch_of(class_index))
            class_item.setToolTip(self.PHRASE_COLUMN, phrases)
            if not definition.text_queries:
                class_item.setForeground(self.PHRASE_COLUMN, self.palette().color(QPalette.ColorRole.PlaceholderText))
            self._class_tree.addTopLevelItem(class_item)
        self._fit_class_tree_height()
        self._show_thumbnails(class_set)
        self._stack.setCurrentIndex(self.CONTENT_INDEX)

    def _fit_class_tree_height(self) -> None:
        row_count: int = self._class_tree.topLevelItemCount()
        first_item: QTreeWidgetItem | None = self._class_tree.topLevelItem(0)
        row_height: int = (
            self._class_tree.visualItemRect(first_item).height() if first_item is not None else 0
        ) or self.fontMetrics().height() + 6
        visible_rows: int = max(1, min(row_count, self.MAXIMUM_VISIBLE_CLASS_ROWS))
        self._class_tree.setFixedHeight(visible_rows * row_height + 2 * self._class_tree.frameWidth())

    def _show_thumbnails(self, class_set: ClassSet) -> None:
        self._thumbnail_list.clear()
        background: QColor = self.palette().color(QPalette.ColorRole.AlternateBase)
        thumbnail: ReferenceThumbnail = ReferenceThumbnail(self.THUMBNAIL_EDGE, background)
        for class_index, definition in enumerate(class_set.classes):
            class_boxes: list[ReferenceBox] = [
                box for box in class_set.reference_boxes if box.class_name == definition.name
            ]
            for reference_image in dict.fromkeys(box.reference_image for box in class_boxes):
                image_boxes: list[ReferenceBox] = [box for box in class_boxes if box.reference_image == reference_image]
                self._thumbnail_list.addItem(
                    self._thumbnail_item(
                        thumbnail, class_set, reference_image, definition.name, class_index, image_boxes
                    )
                )
        is_empty: bool = self._thumbnail_list.count() == 0
        self._image_section_label.setHidden(is_empty)
        self._thumbnail_list.setHidden(is_empty)

    def _thumbnail_item(
        self,
        thumbnail: ReferenceThumbnail,
        class_set: ClassSet,
        reference_image: ReferenceImage,
        class_name: str,
        class_index: int,
        boxes: list[ReferenceBox],
    ) -> QListWidgetItem:
        icon: QIcon = thumbnail.render(
            class_set.reference_pixels[reference_image],
            [box.xyxy for box in boxes],
            self._palette.color_of(class_index),
        )
        item: QListWidgetItem = QListWidgetItem(icon, f"{class_name}\n{reference_image.name}")
        item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        item.setToolTip(
            f"{reference_image.name}\nPrompts '{class_name}' with {len(boxes)} box{'' if len(boxes) == 1 else 'es'}"
        )
        return item

    def _section_label(self, text: str) -> QLabel:
        label: QLabel = QLabel(text)
        section_font: QFont = QFont(label.font())
        section_font.setWeight(QFont.Weight.Bold)
        section_font.setPointSizeF(section_font.pointSizeF() * self.SECTION_FONT_SCALE)
        section_font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, self.SECTION_LETTER_SPACING)
        label.setFont(section_font)
        label.setForegroundRole(QPalette.ColorRole.PlaceholderText)
        return label
