# ui/ocr_worker.py
"""QThread worker for background OCR processing."""
from PyQt6.QtCore import QThread, pyqtSignal


class OcrWorker(QThread):
    """Runs OCR in background thread. Emits progress and result signals."""
    progress = pyqtSignal(str)           # status message
    result_ready = pyqtSignal(dict)      # parsed OCR result
    error_occurred = pyqtSignal(str)     # error message

    def __init__(self, image_path: str, doc_type: str = "gcn", parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.doc_type = doc_type
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            from core import ocr_service, land_parser

            def _cb(msg):
                if not self._cancelled:
                    self.progress.emit(msg)

            if self._cancelled:
                return

            self.progress.emit("🔄 Đang chuẩn bị ảnh...")
            raw = ocr_service.run_ocr(self.image_path, self.doc_type, progress_callback=_cb)

            if self._cancelled:
                return

            if raw.get("error"):
                self.error_occurred.emit(raw["error"])
                return

            self.progress.emit("🔍 Đang phân tích dữ liệu đất đai...")
            parsed = land_parser.parse_ocr_result(raw)

            if not self._cancelled:
                self.progress.emit("✅ OCR hoàn thành!")
                self.result_ready.emit(parsed)

        except Exception as e:
            if not self._cancelled:
                self.error_occurred.emit(f"Lỗi không xác định: {e}")
