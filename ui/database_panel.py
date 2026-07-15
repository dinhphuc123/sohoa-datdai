# ui/database_panel.py
"""
Database panel: search, view, and manage land records.
"""
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QFrame, QSplitter,
    QTextEdit, QMessageBox, QFileDialog, QGroupBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QColor, QBrush, QFont
from core import database, export


class DatabasePanel(QWidget):
    record_selected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_records: list = []
        self._selected_id: int | None = None
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Stats bar ──
        stats_frame = QFrame()
        stats_frame.setFixedHeight(64)
        stats_frame.setStyleSheet("QFrame { background: #0a1628; border-bottom: 1px solid #1e3a5f; }")
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(12, 8, 12, 8)
        stats_layout.setSpacing(16)

        self.lbl_total = self._stat_card("Tổng hồ sơ", "0", "#2563eb")
        self.lbl_gcn = self._stat_card("GCN / Sổ đỏ", "0", "#059669")
        self.lbl_hd = self._stat_card("Hợp đồng", "0", "#d97706")
        self.lbl_verified = self._stat_card("Đã xác minh", "0", "#7c3aed")
        self.lbl_area = self._stat_card("Tổng DT (m²)", "0", "#0891b2")

        for card in (self.lbl_total, self.lbl_gcn, self.lbl_hd, self.lbl_verified, self.lbl_area):
            stats_layout.addWidget(card)
        stats_layout.addStretch()

        # Refresh button
        btn_refresh = QPushButton("🔄 Làm mới")
        btn_refresh.clicked.connect(self.refresh)
        stats_layout.addWidget(btn_refresh)
        layout.addWidget(stats_frame)

        # ── Search bar ──
        search_frame = QFrame()
        search_frame.setFixedHeight(46)
        search_frame.setStyleSheet("QFrame { background: #132238; border-bottom: 1px solid #1e3a5f; }")
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(10, 6, 10, 6)
        search_layout.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Tìm kiếm: tên chủ, số thửa, số GCN, địa chỉ...")
        self.search_input.returnPressed.connect(self._do_search)

        self.filter_type = QComboBox()
        self.filter_type.addItems(["Tất cả loại", "GCN / Sổ đỏ", "Hợp đồng"])
        self.filter_type.setFixedWidth(130)

        self.filter_status = QComboBox()
        self.filter_status.addItems(["Tất cả TT", "draft", "verified", "archived"])
        self.filter_status.setFixedWidth(100)

        btn_search = QPushButton("Tìm")
        btn_search.setObjectName("btn-primary")
        btn_search.clicked.connect(self._do_search)
        btn_clear_search = QPushButton("✕")
        btn_clear_search.setFixedWidth(28)
        btn_clear_search.clicked.connect(self._clear_search)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.filter_type)
        search_layout.addWidget(self.filter_status)
        search_layout.addWidget(btn_search)
        search_layout.addWidget(btn_clear_search)
        layout.addWidget(search_frame)

        # ── Main content: table + detail ──
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Loại", "Chủ sở hữu / Bên chuyển", "Số thửa",
            "Tờ BĐ", "Diện tích", "Địa chỉ", "Trạng thái"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._on_row_select)
        self.table.doubleClicked.connect(self._on_row_double_click)
        splitter.addWidget(self.table)

        # Detail panel
        detail_frame = QWidget()
        detail_layout = QVBoxLayout(detail_frame)
        detail_layout.setContentsMargins(8, 4, 8, 8)
        detail_layout.setSpacing(4)

        detail_header = QHBoxLayout()
        detail_lbl = QLabel("Chi tiết hồ sơ")
        detail_lbl.setStyleSheet("font-weight: 700; color: #94a3b8; font-size: 11px; text-transform: uppercase;")
        detail_header.addWidget(detail_lbl)
        detail_header.addStretch()

        self.btn_verify = QPushButton("✅ Xác minh")
        self.btn_verify.setObjectName("btn-success")
        self.btn_verify.setEnabled(False)
        self.btn_verify.clicked.connect(lambda: self._set_status("verified"))
        self.btn_delete = QPushButton("🗑 Xóa")
        self.btn_delete.setObjectName("btn-danger")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._delete_selected)
        self.btn_export_pdf = QPushButton("📄 Xuất PDF")
        self.btn_export_pdf.setEnabled(False)
        self.btn_export_pdf.clicked.connect(self._export_pdf)
        self.btn_export_excel = QPushButton("📊 Xuất Excel (tất cả)")
        self.btn_export_excel.clicked.connect(self._export_excel_all)

        for btn in (self.btn_verify, self.btn_delete, self.btn_export_pdf, self.btn_export_excel):
            detail_header.addWidget(btn)

        detail_layout.addLayout(detail_header)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setObjectName("ocr-result-box")
        self.detail_text.setFixedHeight(140)
        self.detail_text.setPlaceholderText("Chọn một hồ sơ để xem chi tiết...")
        detail_layout.addWidget(self.detail_text)

        splitter.addWidget(detail_frame)
        splitter.setSizes([500, 200])
        layout.addWidget(splitter, 1)

    def _stat_card(self, title: str, value: str, color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: #132238;
                border: 1px solid #1e3a5f;
                border-left: 3px solid {color};
                border-radius: 6px;
                padding: 4px 10px;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(4, 2, 4, 2)
        card_layout.setSpacing(0)
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {color};")
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 10px; color: #64748b; font-weight: 600;")
        card_layout.addWidget(lbl_val)
        card_layout.addWidget(lbl_title)
        card._value_label = lbl_val
        return card

    def refresh(self):
        """Reload all records from DB."""
        stats = database.get_statistics()
        self.lbl_total._value_label.setText(str(stats.get("total", 0)))
        self.lbl_gcn._value_label.setText(str(stats.get("gcn_count", 0)))
        self.lbl_hd._value_label.setText(str(stats.get("hop_dong_count", 0)))
        self.lbl_verified._value_label.setText(str(stats.get("verified", 0)))
        self.lbl_area._value_label.setText(f"{stats.get('total_area', 0):,.1f}")
        self._do_search()

    def _do_search(self):
        q = self.search_input.text().strip()
        type_map = {"Tất cả loại": "", "GCN / Sổ đỏ": "gcn", "Hợp đồng": "hop_dong"}
        status_map = {"Tất cả TT": ""}
        doc_type = type_map.get(self.filter_type.currentText(), "")
        status = status_map.get(self.filter_status.currentText(), self.filter_status.currentText())
        self._current_records = database.search_records(q, doc_type, status)
        self._populate_table(self._current_records)

    def _clear_search(self):
        self.search_input.clear()
        self.filter_type.setCurrentIndex(0)
        self.filter_status.setCurrentIndex(0)
        self._do_search()

    def _populate_table(self, records: list):
        self.table.setRowCount(0)
        for rec in records:
            raw = {}
            try:
                raw = json.loads(rec.get("raw_ocr", "{}")) if rec.get("raw_ocr") else {}
            except Exception:
                pass

            doc_type = rec.get("doc_type", "")
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(str(rec.get("id", ""))))

            type_item = QTableWidgetItem("GCN/Sổ đỏ" if doc_type == "gcn" else "Hợp đồng")
            type_item.setForeground(QBrush(QColor("#6ee7b7" if doc_type == "gcn" else "#93c5fd")))
            self.table.setItem(row, 1, type_item)

            if doc_type == "gcn":
                owners = raw.get("chu_so_huu", [])
                name = owners[0].get("ho_ten", "") if owners and isinstance(owners[0], dict) else ""
                self.table.setItem(row, 2, QTableWidgetItem(name))
                self.table.setItem(row, 3, QTableWidgetItem(raw.get("so_thua_dat", "")))
                self.table.setItem(row, 4, QTableWidgetItem(raw.get("so_to_ban_do", "")))
                self.table.setItem(row, 5, QTableWidgetItem(f"{raw.get('dien_tich','')} {raw.get('dien_tich_don_vi','m²')}"))
                addr = f"{raw.get('phuong_xa','')}, {raw.get('quan_huyen','')}, {raw.get('tinh_thanh','')}".strip(", ")
                self.table.setItem(row, 6, QTableWidgetItem(addr))
            else:
                bc = raw.get("ben_chuyen_nhuong", [{}])
                name = bc[0].get("ho_ten", "") if bc and isinstance(bc[0], dict) else ""
                thua = raw.get("thong_tin_thua_dat") or {}
                self.table.setItem(row, 2, QTableWidgetItem(name))
                self.table.setItem(row, 3, QTableWidgetItem(thua.get("so_thua_dat", "")))
                self.table.setItem(row, 4, QTableWidgetItem(thua.get("so_to_ban_do", "")))
                self.table.setItem(row, 5, QTableWidgetItem(f"{thua.get('dien_tich','')} m²"))
                self.table.setItem(row, 6, QTableWidgetItem(thua.get("dia_chi", "")))

            status = rec.get("status", "draft")
            status_item = QTableWidgetItem(status)
            if status == "verified":
                status_item.setForeground(QBrush(QColor("#34d399")))
            elif status == "archived":
                status_item.setForeground(QBrush(QColor("#94a3b8")))
            else:
                status_item.setForeground(QBrush(QColor("#a1a1aa")))
            self.table.setItem(row, 7, status_item)

        self.table.resizeColumnsToContents()

    def _get_selected_record_id(self) -> int | None:
        rows = self.table.selectedItems()
        if not rows:
            return None
        row = self.table.currentRow()
        item = self.table.item(row, 0)
        return int(item.text()) if item else None

    def _on_row_select(self):
        rec_id = self._get_selected_record_id()
        self._selected_id = rec_id
        enabled = rec_id is not None
        self.btn_verify.setEnabled(enabled)
        self.btn_delete.setEnabled(enabled)
        self.btn_export_pdf.setEnabled(enabled)

        if rec_id:
            detail = database.get_record_detail(rec_id)
            raw = {}
            try:
                raw = json.loads(detail.get("raw_ocr", "{}")) if detail.get("raw_ocr") else {}
            except Exception:
                pass
            lines = [f"ID: {rec_id} | Loại: {detail.get('doc_type','').upper()} | TT: {detail.get('status','').upper()}"]
            lines.append(f"File: {detail.get('source_file','N/A')}")
            lines.append(f"Ngày nhập: {detail.get('created_at','')}")
            lines.append("─" * 60)
            if detail.get("doc_type") == "gcn":
                d = detail.get("detail", raw)
                lines.append(f"Số GCN: {d.get('so_gcn','')}")
                lines.append(f"Ngày cấp: {d.get('ngay_cap','')}")
                for o in detail.get("owners", []):
                    lines.append(f"Chủ: {o.get('ho_ten','')} | CMND: {o.get('cmnd_cccd','')}")
                lines.append(f"Thửa {d.get('so_thua_dat','')} - Tờ {d.get('so_to_ban_do','')} | DT: {d.get('dien_tich','')} {d.get('dien_tich_don_vi','m²')}")
                lines.append(f"Mục đích: {d.get('muc_dich_su_dung','')}")
                lines.append(f"Địa chỉ: {d.get('phuong_xa','')}, {d.get('quan_huyen','')}, {d.get('tinh_thanh','')}")
            else:
                d = detail.get("detail", raw)
                lines.append(f"Số HĐ: {d.get('so_hop_dong','')}")
                lines.append(f"Ngày ký: {d.get('ngay_ky','')} | Nơi ký: {d.get('noi_ky','')}")
                for o in detail.get("owners", []):
                    role = "Chuyển" if o.get("role") == "ben_chuyen" else "Nhận"
                    lines.append(f"Bên {role}: {o.get('ho_ten','')} | CMND: {o.get('cmnd_cccd','')}")
                lines.append(f"Giá: {d.get('gia_chuyen_nhuong',''):,} VNĐ" if str(d.get('gia_chuyen_nhuong','')).isdigit() else f"Giá: {d.get('gia_chuyen_nhuong','')} VNĐ")
                lines.append(f"CC: {d.get('so_cong_chung','')} | {d.get('van_phong_cong_chung','')}")
            self.detail_text.setPlainText("\n".join(lines))

    def _on_row_double_click(self):
        rec_id = self._get_selected_record_id()
        if rec_id:
            detail = database.get_record_detail(rec_id)
            self.record_selected.emit(detail)

    def _set_status(self, status: str):
        if self._selected_id:
            database.update_record_status(self._selected_id, status)
            self.refresh()

    def _delete_selected(self):
        if not self._selected_id:
            return
        reply = QMessageBox.question(self, "Xác nhận xóa",
                                     f"Xóa hồ sơ ID {self._selected_id}? Không thể hoàn tác!",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            database.delete_record(self._selected_id)
            self._selected_id = None
            self.refresh()

    def _export_pdf(self):
        if not self._selected_id:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Xuất PDF", f"ho_so_{self._selected_id}.pdf", "PDF Files (*.pdf)")
        if path:
            detail = database.get_record_detail(self._selected_id)
            try:
                export.export_record_to_pdf(detail, path)
                QMessageBox.information(self, "Thành công", f"✅ Đã xuất PDF:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Xuất PDF thất bại:\n{e}")

    def _export_excel_all(self):
        path, _ = QFileDialog.getSaveFileName(self, "Xuất Excel", "danh_sach_dat_dai.xlsx", "Excel Files (*.xlsx)")
        if path:
            try:
                export.export_to_excel(self._current_records, path)
                QMessageBox.information(self, "Thành công", f"✅ Đã xuất {len(self._current_records)} hồ sơ:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Xuất Excel thất bại:\n{e}")
