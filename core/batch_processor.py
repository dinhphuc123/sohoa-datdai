# core/batch_processor.py
"""
Batch OCR Processor — Số hóa hàng loạt nhiều tập tin đất đai.
Tự động quét PDF/Ảnh, thực hiện OCR, chuẩn hóa dữ liệu và lưu vào SQLite CSDL.
"""
import os
import json
from typing import Callable, Optional
from PyQt6.QtCore import QThread, pyqtSignal

from core import ocr_service, land_parser, database, file_handler


class BatchWorker(QThread):
    """
    QThread processing a queue of land document files in the background.
    Signals progress per item and overall completion statistics.
    """
    file_started = pyqtSignal(int, int, str)        # current, total, filename
    file_finished = pyqtSignal(int, int, str, dict) # current, total, filename, result
    file_error = pyqtSignal(int, int, str, str)    # current, total, filename, err_msg
    batch_complete = pyqtSignal(int, int)           # success_count, fail_count

    def __init__(self, file_paths: list[str], doc_type: str = "gcn", parent=None):
        super().__init__(parent)
        self.file_paths = file_paths
        self.doc_type = doc_type
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        total = len(self.file_paths)
        success = 0
        failed = 0

        for idx, file_path in enumerate(self.file_paths, 1):
            if self._is_cancelled:
                break

            filename = os.path.basename(file_path)
            self.file_started.emit(idx, total, filename)

            try:
                # Handle PDF vs Image
                if file_handler.is_pdf(file_path):
                    # Process 1st page by default for batch
                    page_path = file_handler.render_pdf_page(file_path, 0, dpi=200)
                else:
                    page_path = file_path

                if self._is_cancelled:
                    break

                # Run OCR
                raw = ocr_service.run_ocr(page_path, self.doc_type)

                if raw.get("error"):
                    failed += 1
                    self.file_error.emit(idx, total, filename, raw["error"])
                    continue

                # Parse & normalize
                parsed = land_parser.parse_ocr_result(raw)

                # Auto-save to Database
                if self.doc_type == "gcn":
                    parsed["_doc_type"] = "gcn"
                    rec_id = database.save_gcn_record(parsed, filename, 0, page_path)
                elif self.doc_type == "hop_dong":
                    parsed["_doc_type"] = "hop_dong"
                    rec_id = database.save_hop_dong_record(parsed, filename, 0, page_path)

                success += 1
                self.file_finished.emit(idx, total, filename, parsed)

            except Exception as e:
                failed += 1
                self.file_error.emit(idx, total, filename, str(e))

        self.batch_complete.emit(success, failed)
