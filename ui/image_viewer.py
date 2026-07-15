# ui/image_viewer.py
"""
Interactive image viewer with crop/region selection tools.
QGraphicsView-based, supports zoom, pan, rubber-band crop.
"""
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsRectItem, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QSizeF
from PyQt6.QtGui import (
    QPixmap, QPen, QBrush, QColor, QWheelEvent,
    QMouseEvent, QPainter, QFont, QCursor
)
import os


class ImageCanvas(QGraphicsView):
    """Interactive canvas for viewing images with crop rectangle tool."""
    region_selected = pyqtSignal(float, float, float, float)  # x1,y1,x2,y2 normalized 0-1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._rubber_rect: QGraphicsRectItem | None = None
        self._region_items: list[QGraphicsRectItem] = []
        self._draw_origin: QPointF | None = None
        self._tool = "pan"  # 'pan' | 'crop'
        self._zoom = 1.0
        self._image_path: str = ""

        self.setStyleSheet("background-color: #080f1d; border: none;")

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def load_image(self, path: str):
        self._scene.clear()
        self._pixmap_item = None
        self._region_items.clear()
        self._rubber_rect = None
        self._image_path = path

        pix = QPixmap(path)
        if pix.isNull():
            return
        self._pixmap_item = QGraphicsPixmapItem(pix)
        self._pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self._scene.addItem(self._pixmap_item)
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom = 1.0

    def set_tool(self, tool: str):
        self._tool = tool
        if tool == "pan":
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

    def clear_regions(self):
        for item in self._region_items:
            self._scene.removeItem(item)
        self._region_items.clear()

    def fit_to_window(self):
        if self._pixmap_item:
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    # -----------------------------------------------------------------------
    # Zoom
    # -----------------------------------------------------------------------

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            factor = 1.12 if delta > 0 else (1 / 1.12)
            self._zoom *= factor
            self._zoom = max(0.1, min(self._zoom, 20.0))
            self.scale(factor, factor)
        else:
            super().wheelEvent(event)

    # -----------------------------------------------------------------------
    # Draw rubber-band crop region
    # -----------------------------------------------------------------------

    def _scene_pos(self, event: QMouseEvent) -> QPointF:
        return self.mapToScene(event.pos())

    def mousePressEvent(self, event: QMouseEvent):
        if self._tool == "crop" and event.button() == Qt.MouseButton.LeftButton:
            self._draw_origin = self._scene_pos(event)
            if self._rubber_rect:
                self._scene.removeItem(self._rubber_rect)
            pen = QPen(QColor("#2563eb"), 2, Qt.PenStyle.SolidLine)
            brush = QBrush(QColor(37, 99, 235, 40))
            self._rubber_rect = QGraphicsRectItem()
            self._rubber_rect.setPen(pen)
            self._rubber_rect.setBrush(brush)
            self._scene.addItem(self._rubber_rect)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._tool == "crop" and self._draw_origin and self._rubber_rect:
            cur = self._scene_pos(event)
            rect = QRectF(self._draw_origin, cur).normalized()
            self._rubber_rect.setRect(rect)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._tool == "crop" and event.button() == Qt.MouseButton.LeftButton and self._rubber_rect:
            rect = self._rubber_rect.rect()
            if rect.width() > 10 and rect.height() > 10 and self._pixmap_item:
                img_rect = self._pixmap_item.boundingRect()
                x1 = max(0.0, rect.left() / img_rect.width())
                y1 = max(0.0, rect.top() / img_rect.height())
                x2 = min(1.0, rect.right() / img_rect.width())
                y2 = min(1.0, rect.bottom() / img_rect.height())

                # Add a persistent region indicator
                pen = QPen(QColor("#059669"), 2)
                brush = QBrush(QColor(5, 150, 105, 30))
                region_item = QGraphicsRectItem(rect)
                region_item.setPen(pen)
                region_item.setBrush(brush)
                self._scene.addItem(region_item)
                self._region_items.append(region_item)

                self._scene.removeItem(self._rubber_rect)
                self._rubber_rect = None
                self._draw_origin = None

                self.region_selected.emit(x1, y1, x2, y2)
            else:
                self._scene.removeItem(self._rubber_rect)
                self._rubber_rect = None
                self._draw_origin = None
        else:
            super().mouseReleaseEvent(event)


class ImageViewer(QWidget):
    """Full image viewer panel with toolbar."""
    region_selected = pyqtSignal(float, float, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = QFrame()
        toolbar.setFixedHeight(40)
        toolbar.setStyleSheet("""
            QFrame { background: #0a1628; border-bottom: 1px solid #1e3a5f; }
            QPushButton { min-width: 32px; min-height: 28px; border-radius: 4px; font-size: 13px; }
        """)
        tbar_layout = QHBoxLayout(toolbar)
        tbar_layout.setContentsMargins(8, 4, 8, 4)
        tbar_layout.setSpacing(4)

        self.btn_pan = QPushButton("🖐 Di chuyển")
        self.btn_crop = QPushButton("✂️ Chọn vùng OCR")
        self.btn_clear = QPushButton("🗑")
        self.btn_fit = QPushButton("⊡")
        self.btn_zoom_in = QPushButton("🔍+")
        self.btn_zoom_out = QPushButton("🔍-")

        self.btn_pan.setCheckable(True)
        self.btn_crop.setCheckable(True)
        self.btn_pan.setChecked(True)

        self.btn_pan.setObjectName("btn-primary")
        self.btn_crop.setStyleSheet("QPushButton:checked { background: #065f46; border-color: #059669; }")

        for btn in (self.btn_pan, self.btn_crop, self.btn_fit, self.btn_zoom_in, self.btn_zoom_out, self.btn_clear):
            tbar_layout.addWidget(btn)
        tbar_layout.addStretch()
        self.lbl_info = QLabel("")
        self.lbl_info.setStyleSheet("color: #64748b; font-size: 11px;")
        tbar_layout.addWidget(self.lbl_info)

        # Canvas
        self.canvas = ImageCanvas()
        self.canvas.region_selected.connect(self.region_selected)

        layout.addWidget(toolbar)
        layout.addWidget(self.canvas, 1)

        # Connect toolbar
        self.btn_pan.clicked.connect(lambda: self._set_tool("pan"))
        self.btn_crop.clicked.connect(lambda: self._set_tool("crop"))
        self.btn_clear.clicked.connect(self.canvas.clear_regions)
        self.btn_fit.clicked.connect(self.canvas.fit_to_window)
        self.btn_zoom_in.clicked.connect(lambda: self.canvas.scale(1.2, 1.2))
        self.btn_zoom_out.clicked.connect(lambda: self.canvas.scale(1/1.2, 1/1.2))

    def _set_tool(self, tool: str):
        self.canvas.set_tool(tool)
        self.btn_pan.setChecked(tool == "pan")
        self.btn_crop.setChecked(tool == "crop")

    def load_image(self, path: str):
        self.canvas.load_image(path)
        if path:
            size = os.path.getsize(path)
            self.lbl_info.setText(f"{os.path.basename(path)}  ({size//1024} KB)")
