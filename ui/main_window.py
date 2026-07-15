# ui/main_window.py
"""
Main application window for Dat Dai Desktop.
Layout: Sidebar | Image Viewer | Form + OCR Panel
Supports: Gemini API · Mistral API · LM Studio
"""
import os
import json
import tempfile
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QLabel, QPushButton, QFrame, QTabWidget,
    QFileDialog, QListWidget, QListWidgetItem, QTextEdit,
    QComboBox, QProgressBar, QMessageBox, QStatusBar,
    QMenuBar, QMenu, QStackedWidget, QApplication
)
from PyQt6.QtCore import Qt, QSize, pyqtSlot, QTimer
from PyQt6.QtGui import QAction, QPixmap, QIcon, QFont

from ui.image_viewer import ImageViewer
from ui.land_form import GcnForm, HopDongForm
from ui.database_panel import DatabasePanel
from ui.ocr_worker import OcrWorker
from ui.settings_dialog import SettingsDialog
from ui.batch_dialog import BatchDialog
from core import database, file_handler, config_manager as cfg


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        database.init_db()
        self.setWindowTitle("🏡 Số hóa Dữ liệu Đất đai Việt Nam")
        self.setMinimumSize(1200, 720)
        self.resize(1440, 900)

        self._current_doc_path: str = ""
        self._current_pages: list = []
        self._current_page_index: int = 0
        self._current_doc_type: str = "gcn"
        self._ocr_worker: OcrWorker | None = None
        self._ocr_result: dict = {}

        self._build_menu()
        self._build_ui()
        self._build_statusbar()
        self._set_status("Sẵn sàng. Mở file hồ sơ để bắt đầu số hóa.")

    # =========================================================================
    # MENU
    # =========================================================================

    def _build_menu(self):
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("&File")
        act_open = QAction("📂 Mở file hồ sơ...", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self._open_file)

        act_batch = QAction("⚡ Số hóa hàng loạt (Batch)...", self)
        act_batch.setShortcut("Ctrl+B")
        act_batch.triggered.connect(self._open_batch_dialog)

        act_settings = QAction("⚙️ Cài đặt...", self)
        act_settings.triggered.connect(self._open_settings)
        act_quit = QAction("Thoát", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)

        file_menu.addAction(act_open)
        file_menu.addAction(act_batch)
        file_menu.addSeparator()
        file_menu.addAction(act_settings)
        file_menu.addSeparator()
        file_menu.addAction(act_quit)

        # Edit
        edit_menu = mb.addMenu("&Chỉnh sửa")
        act_clear = QAction("🗑 Xóa dữ liệu form", self)
        act_clear.triggered.connect(self._clear_form)
        edit_menu.addAction(act_clear)

        # View
        view_menu = mb.addMenu("&Xem")
        act_db = QAction("🗄 Mở Cơ sở dữ liệu", self)
        act_db.triggered.connect(lambda: self._switch_view("db"))
        act_ocr = QAction("📷 Về Số hóa", self)
        act_ocr.triggered.connect(lambda: self._switch_view("ocr"))
        view_menu.addAction(act_db)
        view_menu.addAction(act_ocr)

        # Help
        help_menu = mb.addMenu("&Trợ giúp")
        act_about = QAction("ℹ️ Về ứng dụng", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    # =========================================================================
    # UI BUILD
    # =========================================================================

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ─── Left Sidebar ───
        sidebar = self._build_sidebar()
        root_layout.addWidget(sidebar)

        # ─── Main stacked area ───
        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack, 1)

        # Page 0: OCR digitization view
        self.ocr_page = self._build_ocr_view()
        self.stack.addWidget(self.ocr_page)

        # Page 1: Database view
        self.db_panel = DatabasePanel()
        self.stack.addWidget(self.db_panel)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo
        logo_frame = QFrame()
        logo_frame.setObjectName("sidebar-logo")
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(14, 14, 14, 10)
        lbl_logo = QLabel("🏡 Đất Đai VN")
        lbl_logo.setStyleSheet("font-size: 16px; font-weight: 800; color: #2563eb;")
        lbl_sub = QLabel("Số hóa hồ sơ địa chính")
        lbl_sub.setStyleSheet("font-size: 10px; color: #64748b;")
        logo_layout.addWidget(lbl_logo)
        logo_layout.addWidget(lbl_sub)
        layout.addWidget(logo_frame)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #1e3a5f;")
        layout.addWidget(sep)
        layout.addSpacing(8)

        # Nav buttons
        self.btn_nav_ocr = self._sidebar_btn("📷 Số hóa hồ sơ", True)
        self.btn_nav_batch = self._sidebar_btn("⚡ Số hóa hàng loạt", False)
        self.btn_nav_db = self._sidebar_btn("🗄 Cơ sở dữ liệu", False)
        self.btn_nav_settings = self._sidebar_btn("⚙️ Cài đặt", False)

        self.btn_nav_ocr.clicked.connect(lambda: self._switch_view("ocr"))
        self.btn_nav_batch.clicked.connect(self._open_batch_dialog)
        self.btn_nav_db.clicked.connect(lambda: self._switch_view("db"))
        self.btn_nav_settings.clicked.connect(self._open_settings)

        layout.addWidget(self.btn_nav_ocr)
        layout.addWidget(self.btn_nav_batch)
        layout.addWidget(self.btn_nav_db)
        layout.addWidget(self.btn_nav_settings)
        layout.addSpacing(16)

        # File section label
        lbl_files = QLabel("HỒ SƠ ĐÃ MỞ")
        lbl_files.setObjectName("section-title")
        lbl_files.setContentsMargins(16, 0, 16, 0)
        layout.addWidget(lbl_files)

        # Pages list
        self.pages_list = QListWidget()
        self.pages_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; }
            QListWidget::item { padding: 7px 12px; border-radius: 5px; color: #94a3b8; font-size: 12px; }
            QListWidget::item:selected { background: #1d4ed8; color: #ffffff; }
            QListWidget::item:hover:!selected { background: #1e3a5f; color: #e2e8f0; }
        """)
        self.pages_list.currentRowChanged.connect(self._on_page_selected)
        layout.addWidget(self.pages_list, 1)

        # Open file button
        layout.addSpacing(8)
        btn_open = QPushButton("📂 Mở file hồ sơ")
        btn_open.setObjectName("btn-primary")
        btn_open.setContentsMargins(8, 0, 8, 0)
        btn_open.setStyleSheet("margin: 8px; padding: 10px;")
        btn_open.clicked.connect(self._open_file)
        layout.addWidget(btn_open)
        layout.addSpacing(8)

        return sidebar

    def _sidebar_btn(self, text: str, active: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setProperty("active", "true" if active else "false")
        btn.setStyleSheet("""
            QPushButton {
                text-align: left; padding: 10px 16px; border: none;
                border-radius: 6px; margin: 2px 8px; font-size: 13px;
                background: transparent; color: #94a3b8;
            }
            QPushButton:hover { background: #1e3a5f; color: #e2e8f0; }
            QPushButton[active="true"] { background: #1d4ed8; color: #ffffff; font-weight: 600; }
        """)
        return btn

    def _build_ocr_view(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ─── Left: Image Viewer ───
        viewer_container = QWidget()
        viewer_layout = QVBoxLayout(viewer_container)
        viewer_layout.setContentsMargins(0, 0, 0, 0)
        viewer_layout.setSpacing(0)

        self.image_viewer = ImageViewer()
        self.image_viewer.region_selected.connect(self._on_region_selected)
        viewer_layout.addWidget(self.image_viewer, 1)

        # OCR Controls bar below image
        ocr_bar = QFrame()
        ocr_bar.setFixedHeight(52)
        ocr_bar.setStyleSheet("""
            QFrame { background: #0a1628; border-top: 1px solid #1e3a5f; }
        """)
        ocr_bar_layout = QHBoxLayout(ocr_bar)
        ocr_bar_layout.setContentsMargins(10, 6, 10, 6)
        ocr_bar_layout.setSpacing(8)

        lbl_type = QLabel("Loại hồ sơ:")
        lbl_type.setStyleSheet("color: #94a3b8;")
        self.cb_doc_type = QComboBox()
        self.cb_doc_type.addItems(["GCN / Sổ đỏ", "Hợp đồng chuyển nhượng", "Khác"])
        self.cb_doc_type.setFixedWidth(180)
        self.cb_doc_type.currentIndexChanged.connect(self._on_doc_type_changed)
        self.cb_doc_type.setToolTip("Chọn loại hồ sơ trước khi nhận diện OCR")

        self.btn_ocr_full = QPushButton("🤖 OCR Toàn trang")
        self.btn_ocr_full.setObjectName("btn-primary")
        self.btn_ocr_full.clicked.connect(self._run_ocr_full)

        self.btn_ocr_region = QPushButton("✂️ OCR Vùng chọn")
        self.btn_ocr_region.clicked.connect(self._run_ocr_region)
        self.btn_ocr_region.setEnabled(False)

        self.btn_stop_ocr = QPushButton("⏹ Dừng")
        self.btn_stop_ocr.setObjectName("btn-danger")
        self.btn_stop_ocr.setEnabled(False)
        self.btn_stop_ocr.clicked.connect(self._stop_ocr)

        ocr_bar_layout.addWidget(lbl_type)
        ocr_bar_layout.addWidget(self.cb_doc_type)
        ocr_bar_layout.addWidget(self.btn_ocr_full)
        ocr_bar_layout.addWidget(self.btn_ocr_region)
        ocr_bar_layout.addWidget(self.btn_stop_ocr)
        ocr_bar_layout.addStretch()

        # Model indicator
        mode = cfg.get("ocr_mode", "gemini")
        self.lbl_model = QLabel(f"🤖 {mode.upper()}")
        self.lbl_model.setStyleSheet("color: #2563eb; font-size: 11px; font-weight: 700;")
        ocr_bar_layout.addWidget(self.lbl_model)

        viewer_layout.addWidget(ocr_bar)
        splitter.addWidget(viewer_container)

        # ─── Right: Form + OCR Output ───
        right_tabs = QTabWidget()
        right_tabs.setMinimumWidth(420)

        # Tab 1: Data Entry Form (switches between GCN / HopDong)
        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(0)

        # Form action bar
        form_bar = QFrame()
        form_bar.setFixedHeight(44)
        form_bar.setStyleSheet("QFrame { background: #0a1628; border-bottom: 1px solid #1e3a5f; }")
        form_bar_layout = QHBoxLayout(form_bar)
        form_bar_layout.setContentsMargins(10, 4, 10, 4)
        form_bar_layout.setSpacing(6)
        self.btn_save_record = QPushButton("💾 Lưu vào CSDL")
        self.btn_save_record.setObjectName("btn-success")
        self.btn_save_record.clicked.connect(self._save_record)
        self.btn_clear_form = QPushButton("🗑 Xóa form")
        self.btn_clear_form.clicked.connect(self._clear_form)
        form_bar_layout.addStretch()
        form_bar_layout.addWidget(self.btn_clear_form)
        form_bar_layout.addWidget(self.btn_save_record)

        # Stacked forms
        self.form_stack = QStackedWidget()
        self.gcn_form = GcnForm()
        self.hd_form = HopDongForm()
        self.form_stack.addWidget(self.gcn_form)
        self.form_stack.addWidget(self.hd_form)

        form_layout.addWidget(form_bar)
        form_layout.addWidget(self.form_stack, 1)
        right_tabs.addTab(form_container, "📋 Nhập liệu")

        # Tab 2: Raw OCR Output
        raw_container = QWidget()
        raw_layout = QVBoxLayout(raw_container)
        raw_layout.setContentsMargins(6, 6, 6, 6)
        self.ocr_raw_text = QTextEdit()
        self.ocr_raw_text.setObjectName("ocr-result-box")
        self.ocr_raw_text.setReadOnly(True)
        self.ocr_raw_text.setPlaceholderText("Kết quả OCR thô sẽ hiện ở đây sau khi nhận diện...")
        raw_layout.addWidget(self.ocr_raw_text)
        right_tabs.addTab(raw_container, "📄 Kết quả OCR")

        splitter.addWidget(right_tabs)
        splitter.setSizes([760, 460])

        layout.addWidget(splitter)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.hide()

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(page, 1)
        outer.addWidget(self.progress_bar)

        wrapper = QWidget()
        wrapper.setLayout(outer)
        return wrapper

    def _build_statusbar(self):
        sb = self.statusBar()
        self.sb_label = QLabel("")
        sb.addWidget(self.sb_label, 1)
        self.sb_model = QLabel("")
        self.sb_model.setStyleSheet("color: #2563eb; padding-right: 12px;")
        sb.addPermanentWidget(self.sb_model)
        self._update_model_indicator()

    def _update_model_indicator(self):
        mode = cfg.get("ocr_mode", "gemini")
        mode_info = {
            "gemini":   ("✨", "Gemini 3.5-flash",    "#2563eb"),
            "mistral":  ("🔥", "Mistral pixtral-12b",  "#d97706"),
            "lmstudio": ("💻", cfg.get("lmstudio_model", "local-model"), "#059669"),
        }
        icon, label, color = mode_info.get(mode, ("🤖", mode, "#2563eb"))
        self.sb_model.setText(f"{icon} {label}")
        self.sb_model.setStyleSheet(f"color: {color}; padding-right: 12px; font-weight: 600;")
        if hasattr(self, "lbl_model"):
            self.lbl_model.setText(f"{icon} {mode.upper()}")
            self.lbl_model.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 700;")

    # =========================================================================
    # NAVIGATION
    # =========================================================================

    def _switch_view(self, view: str):
        if view == "db":
            self.stack.setCurrentIndex(1)
            self.db_panel.refresh()
            self.btn_nav_ocr.setProperty("active", "false")
            self.btn_nav_db.setProperty("active", "true")
        else:
            self.stack.setCurrentIndex(0)
            self.btn_nav_ocr.setProperty("active", "true")
            self.btn_nav_db.setProperty("active", "false")
        # Refresh stylesheet
        for btn in (self.btn_nav_ocr, self.btn_nav_db):
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # =========================================================================
    # FILE HANDLING
    # =========================================================================

    def _open_file(self):
        last_dir = cfg.get("last_open_dir", "")
        path, _ = QFileDialog.getOpenFileName(
            self, "Mở hồ sơ đất đai", last_dir,
            "Hồ sơ đất đai (*.pdf *.png *.jpg *.jpeg *.webp);;Tất cả (*.*)"
        )
        if not path:
            return
        cfg.set("last_open_dir", os.path.dirname(path))
        cfg.save()
        self._load_document(path)

    def _load_document(self, path: str):
        self._current_doc_path = path
        self._current_pages.clear()
        self.pages_list.clear()
        self.image_viewer.canvas.clear_regions()

        try:
            if file_handler.is_pdf(path):
                count = file_handler.get_pdf_page_count(path)
                self._set_status(f"Đang render {count} trang PDF...")
                QApplication.processEvents()
                for i in range(count):
                    img_path = file_handler.render_pdf_page(path, i, dpi=200)
                    self._current_pages.append(img_path)
                    item = QListWidgetItem(f"📄 Trang {i+1}")
                    self.pages_list.addItem(item)
            else:
                self._current_pages.append(path)
                self.pages_list.addItem(QListWidgetItem(f"🖼 {os.path.basename(path)}"))

            if self._current_pages:
                self.pages_list.setCurrentRow(0)
                self._load_page(0)

            self._set_status(f"Đã mở: {os.path.basename(path)} ({len(self._current_pages)} trang)")

        except Exception as e:
            QMessageBox.critical(self, "Lỗi mở file", f"Không thể mở file:\n{e}")

    def _load_page(self, index: int):
        if 0 <= index < len(self._current_pages):
            self._current_page_index = index
            self.image_viewer.load_image(self._current_pages[index])
            self.image_viewer.canvas.clear_regions()
            self.btn_ocr_region.setEnabled(False)

    def _on_page_selected(self, row: int):
        if row >= 0:
            self._load_page(row)

    # =========================================================================
    # OCR
    # =========================================================================

    def _on_doc_type_changed(self, index: int):
        type_map = {0: "gcn", 1: "hop_dong", 2: "generic"}
        self._current_doc_type = type_map.get(index, "gcn")
        self.form_stack.setCurrentIndex(min(index, 1))

    def _on_region_selected(self, x1: float, y1: float, x2: float, y2: float):
        self._selected_region = (x1, y1, x2, y2)
        self.btn_ocr_region.setEnabled(True)
        self._set_status(f"Đã chọn vùng: ({x1:.2f}, {y1:.2f}) → ({x2:.2f}, {y2:.2f}). Nhấn OCR Vùng chọn.")

    def _run_ocr_full(self):
        if not self._current_pages:
            QMessageBox.warning(self, "Chưa mở file", "Hãy mở file hồ sơ trước.")
            return
        page_path = self._current_pages[self._current_page_index]
        self._start_ocr(page_path)

    def _run_ocr_region(self):
        if not self._current_pages:
            return
        region = getattr(self, "_selected_region", None)
        if not region:
            return
        page_path = self._current_pages[self._current_page_index]
        x1, y1, x2, y2 = region
        try:
            crop_path = file_handler.crop_image_region(page_path, x1, y1, x2, y2, normalized=True)
            self._start_ocr(crop_path)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể cắt vùng ảnh:\n{e}")

    def _start_ocr(self, image_path: str):
        if self._ocr_worker and self._ocr_worker.isRunning():
            return
        self._set_ocr_running(True)
        self.ocr_raw_text.setPlainText("🔄 Đang nhận diện OCR...")
        self._ocr_worker = OcrWorker(image_path, self._current_doc_type)
        self._ocr_worker.progress.connect(self._on_ocr_progress)
        self._ocr_worker.result_ready.connect(self._on_ocr_result)
        self._ocr_worker.error_occurred.connect(self._on_ocr_error)
        self._ocr_worker.start()

    def _stop_ocr(self):
        if self._ocr_worker:
            self._ocr_worker.cancel()
        self._set_ocr_running(False)
        self._set_status("OCR đã dừng.")

    @pyqtSlot(str)
    def _on_ocr_progress(self, msg: str):
        self._set_status(msg)

    @pyqtSlot(dict)
    def _on_ocr_result(self, data: dict):
        self._ocr_result = data
        self._set_ocr_running(False)
        # Show raw JSON
        self.ocr_raw_text.setPlainText(json.dumps(data, ensure_ascii=False, indent=2))
        # Fill form
        if self._current_doc_type == "gcn":
            self.gcn_form.fill_from_ocr(data)
        elif self._current_doc_type == "hop_dong":
            self.hd_form.fill_from_ocr(data)
        # Switch to form tab
        form_area = self.stack.currentWidget()
        # Find right_tabs
        self._set_status("✅ OCR hoàn thành! Kiểm tra và chỉnh sửa dữ liệu, sau đó nhấn Lưu.")

    @pyqtSlot(str)
    def _on_ocr_error(self, error: str):
        self._set_ocr_running(False)
        self.ocr_raw_text.setPlainText(f"❌ LỖI OCR:\n\n{error}")
        self._set_status(f"❌ OCR lỗi: {error[:80]}")
        QMessageBox.critical(self, "Lỗi OCR", error)

    def _set_ocr_running(self, running: bool):
        self.btn_ocr_full.setEnabled(not running)
        self.btn_ocr_region.setEnabled(not running)
        self.btn_stop_ocr.setEnabled(running)
        if running:
            self.progress_bar.show()
        else:
            self.progress_bar.hide()

    # =========================================================================
    # SAVE
    # =========================================================================

    def _save_record(self):
        source = os.path.basename(self._current_doc_path) if self._current_doc_path else ""
        image = self._current_pages[self._current_page_index] if self._current_pages else ""
        try:
            if self._current_doc_type == "gcn":
                data = self.gcn_form.get_data()
                data["_doc_type"] = "gcn"
                rec_id = database.save_gcn_record(data, source, self._current_page_index, image)
                QMessageBox.information(self, "Đã lưu", f"✅ Đã lưu GCN vào CSDL!\nID: {rec_id}")
            elif self._current_doc_type == "hop_dong":
                data = self.hd_form.get_data()
                data["_doc_type"] = "hop_dong"
                rec_id = database.save_hop_dong_record(data, source, self._current_page_index, image)
                QMessageBox.information(self, "Đã lưu", f"✅ Đã lưu Hợp đồng vào CSDL!\nID: {rec_id}")
            else:
                QMessageBox.warning(self, "Chú ý", "Loại hồ sơ 'Khác' chưa hỗ trợ lưu có cấu trúc.")
                return
            # Refresh DB panel if it's visible
            self.db_panel.refresh()
            self._set_status(f"✅ Đã lưu hồ sơ ID={rec_id} vào CSDL.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi lưu", f"Không thể lưu hồ sơ:\n{e}")

    def _clear_form(self):
        self.gcn_form.fill_from_ocr({})
        self.hd_form.fill_from_ocr({})
        self.ocr_raw_text.clear()
        self._ocr_result = {}

    # =========================================================================
    # SETTINGS
    # =========================================================================

    def _open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            self._update_model_indicator()

    def _open_batch_dialog(self):
        dlg = BatchDialog(self)
        dlg.exec()
        self.db_panel.refresh()

    # =========================================================================
    # ABOUT
    # =========================================================================

    def _show_about(self):
        QMessageBox.about(self, "Về ứng dụng",
            "<b>🏡 Số hóa Dữ liệu Đất đai Việt Nam</b><br><br>"
            "Ứng dụng desktop chuyên nghiệp để số hóa<br>"
            "hồ sơ địa chính: GCN/Sổ đỏ, Hợp đồng chuyển nhượng.<br><br>"
            "<b>Công nghệ:</b><br>"
            "• PyQt6 — Giao diện native<br>"
            "• Gemini API — OCR cloud (Google)<br>"
            "• Gemma via Ollama — OCR offline<br>"
            "• SQLite — CSDL địa phương<br>"
            "• OpenPyXL + ReportLab — Xuất báo cáo<br><br>"
            "© 2024 Dat Dai Desktop v1.0"
        )

    # =========================================================================
    # STATUS
    # =========================================================================

    def _set_status(self, msg: str):
        self.sb_label.setText(msg)
