# ui/batch_dialog.py
"""
Batch Processing Dialog — Giao diện số hóa hàng loạt tài liệu đất đai.
"""
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QFileDialog, QComboBox, QGroupBox, QMessageBox, QFrame,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QColor, QBrush

from core.batch_processor import BatchWorker


class BatchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚡ Số hóa hàng loạt (Batch Processing)")
        self.setMinimumSize(800, 560)
        self.setModal(True)

        self._files: list[str] = []
        self._worker: BatchWorker | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Header / Options ──
        opts_frame = QFrame()
        opts_frame.setStyleSheet("QFrame { background: #0a1628; border: 1px solid #1e3a5f; border-radius: 6px; }")
        opts_layout = QHBoxLayout(opts_frame)
        opts_layout.setContentsMargins(10, 8, 10, 8)
        opts_layout.setSpacing(12)

        lbl_doc = QLabel("Loại hồ sơ:")
        lbl_doc.setStyleSheet("color: #94a3b8; font-weight: 600;")
        self.cb_doc_type = QComboBox()
        self.cb_doc_type.addItems(["GCN / Sổ đỏ", "Hợp đồng chuyển nhượng"])
        self.cb_doc_type.setFixedWidth(180)

        self.btn_add_files = QPushButton("📁 Chọn Tập Tin...")
        self.btn_add_files.clicked.connect(self._add_files)

        self.btn_add_folder = QPushButton("📂 Chọn Thư Mục...")
        self.btn_add_folder.clicked.connect(self._add_folder)

        self.btn_clear_list = QPushButton("🗑 Xóa danh sách")
        self.btn_clear_list.clicked.connect(self._clear_files)

        opts_layout.addWidget(lbl_doc)
        opts_layout.addWidget(self.cb_doc_type)
        opts_layout.addWidget(self.btn_add_files)
        opts_layout.addWidget(self.btn_add_folder)
        opts_layout.addWidget(self.btn_clear_list)
        opts_layout.addStretch()

        layout.addWidget(opts_frame)

        # ── Table Queue ──
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["STT", "Tên Tập Tin", "Kích thước", "Trạng thái"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        # ── Progress Section ──
        self.lbl_status = QLabel("Chưa có tập tin nào được chọn.")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # ── Action Buttons ──
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("🚀 Bắt đầu Số hóa Hàng loạt")
        self.btn_start.setObjectName("btn-primary")
        self.btn_start.setStyleSheet("padding: 8px 20px; font-weight: bold;")
        self.btn_start.clicked.connect(self._start_batch)

        self.btn_cancel = QPushButton("⏹ Dừng")
        self.btn_cancel.setObjectName("btn-danger")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_batch)

        btn_close = QPushButton("Đóng")
        btn_close.clicked.connect(self.close)

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Chọn các hồ sơ đất đai", "",
            "Tài liệu (*.pdf *.png *.jpg *.jpeg *.webp);;Tất cả (*.*)"
        )
        if paths:
            for p in paths:
                if p not in self._files:
                    self._files.append(p)
            self._update_table()

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục chứa hồ sơ")
        if folder:
            valid_exts = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
            for root, _, files in os.walk(folder):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in valid_exts:
                        full_p = os.path.join(root, f)
                        if full_p not in self._files:
                            self._files.append(full_p)
            self._update_table()

    def _clear_files(self):
        if self._worker and self._worker.isRunning():
            return
        self._files.clear()
        self._update_table()

    def _update_table(self):
        self.table.setRowCount(0)
        for idx, path in enumerate(self._files, 1):
            row = self.table.rowCount()
            self.table.insertRow(row)
            size_kb = os.path.getsize(path) // 1024 if os.path.exists(path) else 0

            self.table.setItem(row, 0, QTableWidgetItem(str(idx)))
            self.table.setItem(row, 1, QTableWidgetItem(os.path.basename(path)))
            self.table.setItem(row, 2, QTableWidgetItem(f"{size_kb} KB"))
            status_item = QTableWidgetItem("Đang chờ")
            status_item.setForeground(QBrush(QColor("#94a3b8")))
            self.table.setItem(row, 3, status_item)

        self.lbl_status.setText(f"Đã chọn {len(self._files)} tập tin.")
        self.btn_start.setEnabled(len(self._files) > 0)

    def _start_batch(self):
        if not self._files:
            return

        doc_type = "gcn" if self.cb_doc_type.currentIndex() == 0 else "hop_dong"
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_add_files.setEnabled(False)
        self.btn_add_folder.setEnabled(False)
        self.btn_clear_list.setEnabled(False)

        self.progress_bar.setRange(0, len(self._files))
        self.progress_bar.setValue(0)

        self._worker = BatchWorker(self._files, doc_type)
        self._worker.file_started.connect(self._on_file_started)
        self._worker.file_finished.connect(self._on_file_finished)
        self._worker.file_error.connect(self._on_file_error)
        self._worker.batch_complete.connect(self._on_batch_complete)
        self._worker.start()

    def _cancel_batch(self):
        if self._worker:
            self._worker.cancel()
            self.lbl_status.setText("⏹ Đã gửi yêu cầu dừng số hóa...")

    @pyqtSlot(int, int, str)
    def _on_file_started(self, cur: int, total: int, filename: str):
        row = cur - 1
        if 0 <= row < self.table.rowCount():
            item = QTableWidgetItem("⚡ Đang OCR...")
            item.setForeground(QBrush(QColor("#38bdf8")))
            self.table.setItem(row, 3, item)
        self.lbl_status.setText(f"🚀 [{cur}/{total}] Đang xử lý: {filename}...")

    @pyqtSlot(int, int, str, dict)
    def _on_file_finished(self, cur: int, total: int, filename: str, result: dict):
        row = cur - 1
        if 0 <= row < self.table.rowCount():
            item = QTableWidgetItem("✅ Đã lưu CSDL")
            item.setForeground(QBrush(QColor("#34d399")))
            self.table.setItem(row, 3, item)
        self.progress_bar.setValue(cur)

    @pyqtSlot(int, int, str, str)
    def _on_file_error(self, cur: int, total: int, filename: str, err: str):
        row = cur - 1
        if 0 <= row < self.table.rowCount():
            item = QTableWidgetItem(f"❌ Lỗi: {err[:30]}")
            item.setForeground(QBrush(QColor("#f87171")))
            self.table.setItem(row, 3, item)
        self.progress_bar.setValue(cur)

    @pyqtSlot(int, int)
    def _on_batch_complete(self, success: int, failed: int):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_add_files.setEnabled(True)
        self.btn_add_folder.setEnabled(True)
        self.btn_clear_list.setEnabled(True)

        QMessageBox.information(
            self, "Hoàn tất Số hóa hàng loạt",
            f"🎉 Đã hoàn tất số hóa hàng loạt!\n\n"
            f"• Thành công: {success} hồ sơ (đã lưu CSDL)\n"
            f"• Lỗi: {failed} hồ sơ"
        )
        self.lbl_status.setText(f"✅ Hoàn thành: {success} thành công, {failed} lỗi.")
