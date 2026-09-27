from collections.abc import Sequence

from open_vocabulary_detector import DetectionResult
from PIL import Image
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPen, QPixmap, QResizeEvent, QWheelEvent
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene, QGraphicsView, QWidget

from ...detection import ReferenceBox
from ..class_palette import ClassPalette
from .detection_box_item import DetectionBoxItem
from .reference_box_item import ReferenceBoxItem


class ImageCanvas(QGraphicsView):
    """
    Zoomable view of an image with detection and reference boxes drawn over it.

    The image fits the view until the user zooms with the mouse wheel; double-click fits it again.
    While drawing is enabled, dragging with the left button draws a rectangle instead of panning.

    Signals
    -------
    rectangle_drawn : Signal(QRectF)
        A rectangle was drawn, in image pixel coordinates clamped to the image.
    """

    rectangle_drawn: Signal = Signal(QRectF)

    ZOOM_STEP = 1.25
    MINIMUM_RECTANGLE_SIZE = 4.0
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
        self._box_items: list[DetectionBoxItem] = []
        self._reference_items: list[ReferenceBoxItem] = []
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

    def set_image(self, image: Image.Image) -> None:
        """
        Show a new image and remove every detection and reference box.

        Parameters
        ----------
        image : Image.Image
            RGB image to show.
        """
        self._scene.clear()
        self._box_items = []
        self._reference_items = []
        self._rubber_band = None
        self._pixmap_item = self._scene.addPixmap(QPixmap.fromImage(self._to_qimage(image)))
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self.fit_to_view()

    def show_result(self, result: DetectionResult) -> None:
        """
        Replace the drawn boxes with the detections of ``result``.

        Parameters
        ----------
        result : DetectionResult
            Detections in the shown image's pixel coordinates.
        """
        self.clear_detections()
        for detection in result:
            box_item: DetectionBoxItem = DetectionBoxItem(detection, self._palette.color_of(detection.class_id))
            self._scene.addItem(box_item)
            self._box_items.append(box_item)

    def clear_detections(self) -> None:
        """
        Remove every detection box.
        """
        for box_item in self._box_items:
            self._scene.removeItem(box_item)
        self._box_items = []

    def show_references(self, boxes: Sequence[ReferenceBox], class_names: tuple[str, ...]) -> None:
        """
        Replace the drawn reference boxes.

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
        for box in boxes:
            if box.class_name not in class_names:
                continue
            reference_item: ReferenceBoxItem = ReferenceBoxItem(
                box, self._palette.color_of(class_names.index(box.class_name))
            )
            self._scene.addItem(reference_item)
            self._reference_items.append(reference_item)

    def set_drawing_enabled(self, is_enabled: bool) -> None:
        """
        Switch left-button dragging between drawing rectangles and panning.

        Parameters
        ----------
        is_enabled : bool
            Whether dragging draws rectangles.
        """
        self._is_drawing_enabled = is_enabled
        self._discard_rubber_band()
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
        for index, box_item in enumerate(self._box_items):
            box_item.set_highlighted(index == detection_index)
        if detection_index is not None and 0 <= detection_index < len(self._box_items):
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
        self._drag_origin = self._clamped_scene_position(event)
        pen: QPen = QPen(self.RUBBER_BAND_COLOR)
        pen.setCosmetic(True)
        pen.setStyle(Qt.PenStyle.DashLine)
        self._rubber_band = self._scene.addRect(QRectF(self._drag_origin, self._drag_origin), pen)
        self._rubber_band.setZValue(3.0)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._rubber_band is None:
            super().mouseMoveEvent(event)
            return
        self._rubber_band.setRect(QRectF(self._drag_origin, self._clamped_scene_position(event)).normalized())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._rubber_band is None or event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return
        rectangle: QRectF = QRectF(self._drag_origin, self._clamped_scene_position(event)).normalized()
        self._discard_rubber_band()
        if min(rectangle.width(), rectangle.height()) >= self.MINIMUM_RECTANGLE_SIZE:
            self.rectangle_drawn.emit(rectangle)

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

    def _discard_rubber_band(self) -> None:
        if self._rubber_band is not None:
            self._scene.removeItem(self._rubber_band)
            self._rubber_band = None
