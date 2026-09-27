from collections.abc import Sequence

from open_vocabulary_detector import Detection
from PIL import Image
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPen, QPixmap, QResizeEvent, QWheelEvent
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene, QGraphicsView, QWidget

from ...detection import ReferenceBox
from ..class_palette import ClassPalette
from .box_grab import BoxGrab
from .box_grab_kind import BoxGrabKind
from .box_style import BoxStyle
from .detection_box_item import DetectionBoxItem
from .detection_overlay import DetectionOverlay
from .display_options import DisplayOptions
from .reference_box_item import ReferenceBoxItem


class ImageCanvas(QGraphicsView):
    """
    Zoomable view of an image with detection and reference boxes drawn over it.

    The image fits the view until the user zooms with the mouse wheel; double-click fits it again. Only the detections
    listed in the detection table are drawn: kept ones solid, rejected ones dashed and faded, and those of a compared
    model dotted; ``DisplayOptions`` choose labels, confidences, line width and fill.
    While drawing is enabled, dragging with the left button draws a rectangle instead of panning, and the reference
    boxes become editable: dragging a round corner handle resizes a box and dragging inside a box moves it.

    Signals
    -------
    rectangle_drawn : Signal(QRectF)
        A rectangle was drawn, in image pixel coordinates clamped to the image.
    reference_adjusted : Signal(int, QRectF)
        A reference box was moved or resized: its index among the boxes last shown and its new rectangle, in image
        pixel coordinates clamped to the image.
    """

    rectangle_drawn: Signal = Signal(QRectF)
    reference_adjusted: Signal = Signal(int, QRectF)

    ZOOM_STEP = 1.25
    MINIMUM_RECTANGLE_SIZE = 4.0
    HANDLE_GRAB_DISTANCE = 9.0
    RUBBER_BAND_COLOR = QColor("#ffffff")

    def __init__(self, palette: ClassPalette, parent: QWidget | None = None) -> None:
        """
        Parameters
        ----------
        palette : ClassPalette
            Colors of the classes.
        parent : QWidget | None, optional
            Parent widget.
        """
        super().__init__(parent)
        self._palette: ClassPalette = palette
        self._scene: QGraphicsScene = QGraphicsScene(self)
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._box_items: dict[int, DetectionBoxItem] = {}
        self._comparison_items: list[DetectionBoxItem] = []
        self._overlay: DetectionOverlay | None = None
        self._options: DisplayOptions = DisplayOptions()
        self._highlighted_index: int | None = None
        self._reference_items: list[ReferenceBoxItem] = []
        self._reference_box_indices: list[int] = []
        self._shown_references: tuple[ReferenceBox, ...] = ()
        self._shown_class_names: tuple[str, ...] = ()
        self._grab: BoxGrab | None = None
        self._rubber_band: QGraphicsRectItem | None = None
        self._drag_origin: QPointF = QPointF()
        self._is_drawing_enabled: bool = False
        self._is_fitted: bool = True
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(Qt.GlobalColor.darkGray)
        self.viewport().setMouseTracking(True)

    def set_image(self, image: Image.Image) -> None:
        """
        Show a new image and remove every detection and reference box.

        Parameters
        ----------
        image : Image.Image
            RGB image to show.
        """
        self._scene.clear()
        self._box_items = {}
        self._comparison_items = []
        self._overlay = None
        self._highlighted_index = None
        self._reference_items = []
        self._reference_box_indices = []
        self._shown_references = ()
        self._grab = None
        self._rubber_band = None
        self._pixmap_item = self._scene.addPixmap(QPixmap.fromImage(self._to_qimage(image)))
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self.fit_to_view()

    @property
    def display_options(self) -> DisplayOptions:
        """
        How detection boxes are drawn.

        Returns
        -------
        DisplayOptions
            Options in effect.
        """
        return self._options

    @property
    def drawn_indices(self) -> tuple[int, ...]:
        """
        Detections of the shown result drawn now.

        Returns
        -------
        tuple[int, ...]
            Indices in the shown result, in ascending order.
        """
        return tuple(sorted(self._box_items))

    @property
    def drawn_comparison_count(self) -> int:
        """
        Boxes of the compared model drawn now.

        Returns
        -------
        int
            Number of dotted boxes.
        """
        return len(self._comparison_items)

    def set_display_options(self, options: DisplayOptions) -> None:
        """
        Draw the boxes again with other options.

        Parameters
        ----------
        options : DisplayOptions
            New options.
        """
        self._options = options
        self._redraw_detections()

    def show_overlay(self, overlay: DetectionOverlay) -> None:
        """
        Replace the drawn detection boxes.

        Parameters
        ----------
        overlay : DetectionOverlay
            Detections in the shown image's pixel coordinates, with the listed and rejected ones and those of a
            compared model; the highlighted detection stays highlighted while it is drawn.
        """
        self._overlay = overlay
        self._redraw_detections()

    def clear_detections(self) -> None:
        """
        Remove every detection box.
        """
        self._overlay = None
        self._highlighted_index = None
        self._redraw_detections()

    def show_references(self, boxes: Sequence[ReferenceBox], class_names: tuple[str, ...]) -> None:
        """
        Replace the drawn reference boxes; they are editable while drawing is enabled.

        Parameters
        ----------
        boxes : Sequence[ReferenceBox]
            Reference boxes of the shown image; boxes of classes missing from ``class_names`` are skipped.
        class_names : tuple[str, ...]
            Current classes, whose index selects the box color.
        """
        for previous_item in self._reference_items:
            self._scene.removeItem(previous_item)
        self._reference_items = []
        self._reference_box_indices = []
        self._shown_references = tuple(boxes)
        self._shown_class_names = class_names
        self._grab = None
        for box_index, box in enumerate(self._shown_references):
            if box.class_name not in class_names:
                continue
            reference_item: ReferenceBoxItem = ReferenceBoxItem(
                box, self._palette.color_of(class_names.index(box.class_name)), self._is_drawing_enabled
            )
            self._scene.addItem(reference_item)
            self._reference_items.append(reference_item)
            self._reference_box_indices.append(box_index)

    def set_drawing_enabled(self, is_enabled: bool) -> None:
        """
        Switch left-button dragging between drawing and editing rectangles, and panning.

        Parameters
        ----------
        is_enabled : bool
            Whether dragging draws rectangles and edits the reference boxes.
        """
        self._is_drawing_enabled = is_enabled
        self._discard_rubber_band()
        self.show_references(self._shown_references, self._shown_class_names)
        self.setDragMode(QGraphicsView.DragMode.NoDrag if is_enabled else QGraphicsView.DragMode.ScrollHandDrag)
        if is_enabled:
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.viewport().unsetCursor()

    def highlight(self, detection_index: int | None) -> None:
        """
        Emphasize one detection box.

        Parameters
        ----------
        detection_index : int | None
            Index of the detection in the shown result; ``None`` clears the emphasis.
        """
        self._highlighted_index = detection_index
        for index, box_item in self._box_items.items():
            box_item.set_highlighted(index == detection_index)
        if detection_index is not None and detection_index in self._box_items:
            self.ensureVisible(self._box_items[detection_index])

    def fit_to_view(self) -> None:
        """
        Scale the image to fit the view.
        """
        self._is_fitted = True
        if self._pixmap_item is not None:
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._is_fitted:
            self.fit_to_view()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._pixmap_item is None:
            return
        self._is_fitted = False
        factor: float = self.ZOOM_STEP if event.angleDelta().y() > 0 else 1.0 / self.ZOOM_STEP
        self.scale(factor, factor)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        self.fit_to_view()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self._is_drawing_enabled or self._pixmap_item is None or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self._discard_rubber_band()
        self._grab = self._grab_at(event.position())
        if self._grab is not None:
            return
        self._drag_origin = self._clamped_scene_position(event)
        pen: QPen = QPen(self.RUBBER_BAND_COLOR)
        pen.setCosmetic(True)
        pen.setStyle(Qt.PenStyle.DashLine)
        self._rubber_band = self._scene.addRect(QRectF(self._drag_origin, self._drag_origin), pen)
        self._rubber_band.setZValue(3.0)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._grab is not None:
            self._reference_items[self._grab.item_position].set_rectangle(self._dragged_rectangle(self._grab, event))
            return
        if self._rubber_band is None:
            if self._is_drawing_enabled:
                self.viewport().setCursor(self._cursor_for(self._grab_at(event.position())))
            super().mouseMoveEvent(event)
            return
        self._rubber_band.setRect(QRectF(self._drag_origin, self._clamped_scene_position(event)).normalized())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._grab is not None and event.button() == Qt.MouseButton.LeftButton:
            self._release_grab(self._grab, event)
            return
        if self._rubber_band is None or event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return
        rectangle: QRectF = QRectF(self._drag_origin, self._clamped_scene_position(event)).normalized()
        self._discard_rubber_band()
        if min(rectangle.width(), rectangle.height()) >= self.MINIMUM_RECTANGLE_SIZE:
            self.rectangle_drawn.emit(rectangle)

    def _redraw_detections(self) -> None:
        for drawn_item in (*self._box_items.values(), *self._comparison_items):
            self._scene.removeItem(drawn_item)
        self._box_items = {}
        self._comparison_items = []
        overlay: DetectionOverlay | None = self._overlay
        if overlay is None:
            return
        for index, detection in enumerate(overlay.result):
            is_rejected: bool = index in overlay.rejected_indices
            if index not in overlay.listed_indices or (is_rejected and not self._options.is_rejected_shown):
                continue
            box_item: DetectionBoxItem = self._box_item_of(
                detection, BoxStyle.REJECTED if is_rejected else BoxStyle.KEPT, ""
            )
            box_item.set_highlighted(index == self._highlighted_index)
            self._box_items[index] = box_item
        if overlay.comparison is not None and self._options.is_comparison_shown:
            self._comparison_items = [
                self._box_item_of(detection, BoxStyle.COMPARED, overlay.comparison_name)
                for detection in overlay.comparison
            ]

    def _box_item_of(self, detection: Detection, style: BoxStyle, label_prefix: str) -> DetectionBoxItem:
        box_item: DetectionBoxItem = DetectionBoxItem(
            detection, self._palette.color_of(detection.class_id), style, self._options, label_prefix
        )
        self._scene.addItem(box_item)
        return box_item

    @staticmethod
    def _to_qimage(image: Image.Image) -> QImage:
        width, height = image.size
        pixel_bytes: bytes = image.convert("RGB").tobytes("raw", "RGB")
        return QImage(pixel_bytes, width, height, 3 * width, QImage.Format.Format_RGB888).copy()

    def _clamped_scene_position(self, event: QMouseEvent) -> QPointF:
        position: QPointF = self.mapToScene(event.position().toPoint())
        bounds: QRectF = self._scene.sceneRect()
        return QPointF(
            min(max(position.x(), bounds.left()), bounds.right()),
            min(max(position.y(), bounds.top()), bounds.bottom()),
        )

    def _grab_at(self, view_position: QPointF) -> BoxGrab | None:
        item_positions: range = range(len(self._reference_items) - 1, -1, -1)
        for item_position in item_positions:
            corners: tuple[QPointF, QPointF, QPointF, QPointF] = self._reference_items[item_position].corners
            for corner_index, corner in enumerate(corners):
                handle_offset: QPointF = QPointF(self.mapFromScene(corner)) - view_position
                if handle_offset.manhattanLength() <= self.HANDLE_GRAB_DISTANCE:
                    return BoxGrab(
                        item_position=item_position,
                        kind=BoxGrabKind.RESIZE,
                        anchor=corners[(corner_index + 2) % len(corners)],
                        original_rectangle=self._reference_items[item_position].rect(),
                    )
        scene_position: QPointF = self.mapToScene(view_position.toPoint())
        for item_position in item_positions:
            rectangle: QRectF = self._reference_items[item_position].rect()
            if rectangle.contains(scene_position):
                return BoxGrab(
                    item_position=item_position,
                    kind=BoxGrabKind.MOVE,
                    anchor=scene_position,
                    original_rectangle=rectangle,
                )
        return None

    def _dragged_rectangle(self, grab: BoxGrab, event: QMouseEvent) -> QRectF:
        match grab.kind:
            case BoxGrabKind.RESIZE:
                return QRectF(grab.anchor, self._clamped_scene_position(event)).normalized()
            case BoxGrabKind.MOVE:
                offset: QPointF = self.mapToScene(event.position().toPoint()) - grab.anchor
                moved: QRectF = grab.original_rectangle.translated(offset)
                bounds: QRectF = self._scene.sceneRect()
                moved.moveLeft(min(max(moved.left(), bounds.left()), bounds.right() - moved.width()))
                moved.moveTop(min(max(moved.top(), bounds.top()), bounds.bottom() - moved.height()))
                return moved

    def _release_grab(self, grab: BoxGrab, event: QMouseEvent) -> None:
        self._grab = None
        rectangle: QRectF = self._dragged_rectangle(grab, event)
        if min(rectangle.width(), rectangle.height()) < self.MINIMUM_RECTANGLE_SIZE:
            self._reference_items[grab.item_position].set_rectangle(grab.original_rectangle)
            return
        if rectangle != grab.original_rectangle:
            self.reference_adjusted.emit(self._reference_box_indices[grab.item_position], rectangle)

    @staticmethod
    def _cursor_for(grab: BoxGrab | None) -> Qt.CursorShape:
        if grab is None:
            return Qt.CursorShape.CrossCursor
        match grab.kind:
            case BoxGrabKind.MOVE:
                return Qt.CursorShape.SizeAllCursor
            case BoxGrabKind.RESIZE:
                grabbed_corner: QPointF = grab.original_rectangle.center() * 2.0 - grab.anchor
                is_main_diagonal: bool = (grabbed_corner.x() - grab.anchor.x()) * (
                    grabbed_corner.y() - grab.anchor.y()
                ) > 0.0
                return Qt.CursorShape.SizeFDiagCursor if is_main_diagonal else Qt.CursorShape.SizeBDiagCursor

    def _discard_rubber_band(self) -> None:
        if self._rubber_band is not None:
            self._scene.removeItem(self._rubber_band)
            self._rubber_band = None
