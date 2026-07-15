# ui/settings_dialog.py
"""
Settings dialog — API keys + model configuration
Supports: Gemini API · Mistral API · LM Studio (local)
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QGroupBox,
    QComboBox, QDialogButtonBox, QMessageBox,
    QTabWidget, QWidget, QScrollArea, QFrame,
    QListWidget, QListWidgetItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from core import config_manager as cfg


# ---------------------------------------------------------------------------
# Worker thread for model list fetch (non-blocking)
# ---------------------------------------------------------------------------

class ModelFetchWorker(QThread):
    models_ready = pyqtSignal(list)

    def run(self):
        from core.ocr_service import get_lmstudio_models
        models = get_lmstudio_models()
        self.models_ready.emit(models)


# ---------------------------------------------------------------------------
# Key field row with show/hide toggle
# ---------------------------------------------------------------------------

def _secret_field(placeholder: str) -> tuple[QLineEdit, QPushButton]:
    """Returns (field, toggle_button)."""
    field = QLineEdit()
    field.setEchoMode(QLineEdit.EchoMode.Password)
    field.setPlaceholderText(placeholder)
    btn = QPushButton("👁")
    btn.setFixedSize(30, 28)
    btn.setToolTip("Hiện/ẩn")

    def _toggle():
        if field.echoMode() == QLineEdit.EchoMode.Password:
            field.setEchoMode(QLineEdit.EchoMode.Normal)
            btn.setText("🙈")
        else:
            field.setEchoMode(QLineEdit.EchoMode.Password)
            btn.setText("👁")

    btn.clicked.connect(_toggle)
    return field, btn


def _key_row(field: QLineEdit, btn: QPushButton) -> QHBoxLayout:
    row = QHBoxLayout()
    row.addWidget(field)
    row.addWidget(btn)
    return row


# ---------------------------------------------------------------------------
# Settings Dialog
# ---------------------------------------------------------------------------

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Cài đặt")
        self.setMinimumSize(560, 540)
        self.setModal(True)
        self._fetch_worker: ModelFetchWorker | None = None
        self._init_ui()
        self._load_values()

    # =========================================================================
    # BUILD UI
    # =========================================================================

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        tabs = QTabWidget()

        # ── Tab 1: Chế độ OCR ──
        tabs.addTab(self._build_mode_tab(), "🤖 Chế độ OCR")

        # ── Tab 2: Gemini API ──
        tabs.addTab(self._build_gemini_tab(), "✨ Gemini API")

        # ── Tab 3: Mistral API ──
        tabs.addTab(self._build_mistral_tab(), "🔥 Mistral API")

        # ── Tab 4: LM Studio ──
        tabs.addTab(self._build_lmstudio_tab(), "💻 LM Studio")

        # ── Tab 5: Giao diện ──
        tabs.addTab(self._build_ui_tab(), "🎨 Giao diện")

        main_layout.addWidget(tabs)

        # Dialog buttons
        bbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        bbox.accepted.connect(self._save)
        bbox.rejected.connect(self.reject)
        bbox.button(QDialogButtonBox.StandardButton.Save).setText("💾 Lưu cài đặt")
        main_layout.addWidget(bbox)

    # ── Mode tab ──────────────────────────────────────────────────────────────

    def _build_mode_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        g = QGroupBox("Chọn nguồn AI để nhận diện văn bản (OCR)")
        fl = QFormLayout(g)
        fl.setSpacing(10)

        self.cb_mode = QComboBox()
        self.cb_mode.addItems(["gemini", "mistral", "lmstudio"])
        self.cb_mode.setFixedHeight(32)
        self.cb_mode.currentTextChanged.connect(self._on_mode_change)
        fl.addRow("Nguồn AI:", self.cb_mode)

        # Status indicator
        self.lbl_mode_status = QLabel("")
        self.lbl_mode_status.setWordWrap(True)
        self.lbl_mode_status.setStyleSheet("color: #64748b; font-size: 12px;")
        fl.addRow("Trạng thái:", self.lbl_mode_status)

        layout.addWidget(g)

        # Info cards
        info_frame = QFrame()
        info_frame.setStyleSheet("QFrame { background: #0f2447; border: 1px solid #1e3a5f; border-radius: 8px; padding: 8px; }")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(8)

        self._add_info_card(info_layout, "✨ Gemini API",
            "Cloud · Google · Nhanh · Cần API key + internet\n"
            "Model: gemini-1.5-flash (hỗ trợ ảnh rõ ràng)")
        self._add_info_card(info_layout, "🔥 Mistral API",
            "Cloud · Mistral AI · Cần API key + internet\n"
            "Model: pixtral-12b-2409 (vision model chuyên OCR)")
        self._add_info_card(info_layout, "💻 LM Studio",
            "Local · Chạy offline · Riêng tư hoàn toàn\n"
            "Cần cài LM Studio + load vision model (LLaVA, Phi-3-vision, v.v.)")

        layout.addWidget(info_frame)
        layout.addStretch()
        return tab

    def _add_info_card(self, parent_layout, title: str, desc: str):
        card = QFrame()
        card.setStyleSheet("""
            QFrame { background: #132238; border: 1px solid #1e3a5f;
                     border-radius: 6px; padding: 6px 10px; }
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(2)
        lbl_title = QLabel(f"<b>{title}</b>")
        lbl_title.setStyleSheet("color: #e2e8f0; font-size: 12px; background: transparent; border: none;")
        lbl_desc = QLabel(desc)
        lbl_desc.setStyleSheet("color: #64748b; font-size: 11px; background: transparent; border: none;")
        lbl_desc.setWordWrap(True)
        cl.addWidget(lbl_title)
        cl.addWidget(lbl_desc)
        parent_layout.addWidget(card)

    # ── Gemini tab ────────────────────────────────────────────────────────────

    def _build_gemini_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        g = QGroupBox("Gemini API — Google AI Studio")
        fl = QFormLayout(g)
        fl.setSpacing(8)

        self.f_gemini_key, self.btn_gemini_show = _secret_field("AIzaSy...")
        fl.addRow("API Key:", _key_row(self.f_gemini_key, self.btn_gemini_show))

        btn_row = QHBoxLayout()
        self.btn_test_gemini = QPushButton("🔗 Kiểm tra kết nối")
        self.btn_test_gemini.clicked.connect(self._test_gemini)
        btn_get_key = QPushButton("🌐 Lấy API Key...")
        btn_get_key.setToolTip("https://aistudio.google.com/app/apikey")
        btn_get_key.clicked.connect(lambda: __import__("webbrowser").open("https://aistudio.google.com/app/apikey"))
        btn_row.addWidget(self.btn_test_gemini)
        btn_row.addWidget(btn_get_key)
        fl.addRow("", btn_row)

        self.lbl_gemini_status = QLabel("")
        self.lbl_gemini_status.setWordWrap(True)
        fl.addRow("Kết quả:", self.lbl_gemini_status)

        layout.addWidget(g)

        # Help
        help_box = self._help_box(
            "💡 Hướng dẫn lấy Gemini API Key:\n"
            "1. Truy cập: https://aistudio.google.com/app/apikey\n"
            "2. Đăng nhập tài khoản Google\n"
            "3. Nhấn 'Create API key' → Copy key\n"
            "4. Dán vào ô API Key ở trên\n\n"
            "📌 Model sử dụng: gemini-3.5-flash\n"
            "   • 10 request/phút (gói miễn phí)\n"
            "   • Thinking model — độ chính xác cao nhất\n"
            "   • Hỗ trợ ảnh PNG/JPG/WebP"
        )
        layout.addWidget(help_box)
        layout.addStretch()
        return tab

    # ── Mistral tab ───────────────────────────────────────────────────────────

    def _build_mistral_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        g = QGroupBox("Mistral API — Mistral AI")
        fl = QFormLayout(g)
        fl.setSpacing(8)

        self.f_mistral_key, self.btn_mistral_show = _secret_field("...")
        fl.addRow("API Key:", _key_row(self.f_mistral_key, self.btn_mistral_show))

        btn_row = QHBoxLayout()
        self.btn_test_mistral = QPushButton("🔗 Kiểm tra kết nối")
        self.btn_test_mistral.clicked.connect(self._test_mistral)
        btn_get_mistral = QPushButton("🌐 Lấy API Key...")
        btn_get_mistral.clicked.connect(lambda: __import__("webbrowser").open("https://console.mistral.ai/api-keys/"))
        btn_row.addWidget(self.btn_test_mistral)
        btn_row.addWidget(btn_get_mistral)
        fl.addRow("", btn_row)

        self.lbl_mistral_status = QLabel("")
        self.lbl_mistral_status.setWordWrap(True)
        fl.addRow("Kết quả:", self.lbl_mistral_status)

        layout.addWidget(g)

        help_box = self._help_box(
            "💡 Hướng dẫn lấy Mistral API Key:\n"
            "1. Truy cập: https://console.mistral.ai\n"
            "2. Đăng ký/đăng nhập tài khoản\n"
            "3. Vào 'API Keys' → 'Create new key'\n"
            "4. Copy key và dán vào ô trên\n\n"
            "📌 Model sử dụng: pixtral-12b-2409\n"
            "   • Model vision chuyên biệt của Mistral AI\n"
            "   • Hỗ trợ ảnh trực tiếp qua base64\n"
            "   • Tốt cho văn bản scan chất lượng cao"
        )
        layout.addWidget(help_box)
        layout.addStretch()
        return tab

    # ── LM Studio tab ─────────────────────────────────────────────────────────

    def _build_lmstudio_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        g = QGroupBox("LM Studio — Local AI Server")
        fl = QFormLayout(g)
        fl.setSpacing(8)

        self.f_lmstudio_url = QLineEdit()
        self.f_lmstudio_url.setPlaceholderText("http://localhost:1234")
        fl.addRow("Server URL:", self.f_lmstudio_url)

        # Model selector + refresh
        model_row = QHBoxLayout()
        self.cb_lmstudio_model = QComboBox()
        self.cb_lmstudio_model.setEditable(True)
        self.cb_lmstudio_model.setPlaceholderText("Tên model (tự động fetch khi kết nối)...")
        self.cb_lmstudio_model.addItems([
            "local-model",
            "llava-v1.6-mistral-7b",
            "phi-3-vision-128k-instruct",
            "qwen2-vl-7b-instruct",
            "moondream2",
            "llava-1.5-7b-hf",
        ])
        self.btn_fetch_models = QPushButton("🔄")
        self.btn_fetch_models.setFixedSize(32, 28)
        self.btn_fetch_models.setToolTip("Lấy danh sách model từ LM Studio")
        self.btn_fetch_models.clicked.connect(self._fetch_models)
        model_row.addWidget(self.cb_lmstudio_model)
        model_row.addWidget(self.btn_fetch_models)
        fl.addRow("Model:", model_row)

        btn_row = QHBoxLayout()
        self.btn_test_lmstudio = QPushButton("🔗 Kiểm tra LM Studio")
        self.btn_test_lmstudio.clicked.connect(self._test_lmstudio)
        btn_row.addWidget(self.btn_test_lmstudio)
        fl.addRow("", btn_row)

        self.lbl_lmstudio_status = QLabel("")
        self.lbl_lmstudio_status.setWordWrap(True)
        fl.addRow("Kết quả:", self.lbl_lmstudio_status)

        layout.addWidget(g)

        help_box = self._help_box(
            "💡 Hướng dẫn dùng LM Studio:\n"
            "1. Tải LM Studio tại: https://lmstudio.ai\n"
            "2. Tải vision model (khuyến nghị):\n"
            "   • LLaVA-1.6-Mistral-7B  (~4GB)\n"
            "   • Phi-3-Vision-128K      (~8GB)\n"
            "   • Qwen2-VL-7B-Instruct   (~8GB)\n"
            "3. Mở tab 'Local Server' trong LM Studio\n"
            "4. Chọn model → nhấn 'Start Server'\n"
            "5. Quay lại đây → nhấn 🔄 để load model\n\n"
            "⚠️ Cần GPU/RAM đủ mạnh để chạy local model.\n"
            "   Thấp nhất: 8GB RAM + 4GB VRAM"
        )
        layout.addWidget(help_box)
        layout.addStretch()
        return tab

    # ── UI tab ────────────────────────────────────────────────────────────────

    def _build_ui_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        g = QGroupBox("Giao diện ứng dụng")
        fl = QFormLayout(g)
        self.cb_theme = QComboBox()
        self.cb_theme.addItems(["dark", "light"])
        fl.addRow("Theme:", self.cb_theme)
        layout.addWidget(g)
        layout.addStretch()
        return tab

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _help_box(self, text: str) -> QFrame:
        box = QFrame()
        box.setStyleSheet("""
            QFrame { background: #080f1d; border: 1px solid #1e3a5f;
                     border-radius: 6px; padding: 8px; }
        """)
        bl = QVBoxLayout(box)
        bl.setContentsMargins(8, 6, 8, 6)
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #64748b; font-size: 11px; background: transparent; border: none;")
        lbl.setWordWrap(True)
        lbl.setOpenExternalLinks(True)
        bl.addWidget(lbl)
        return box

    # =========================================================================
    # LOAD / SAVE
    # =========================================================================

    def _load_values(self):
        mode = cfg.get("ocr_mode", "gemini")
        idx = self.cb_mode.findText(mode)
        if idx >= 0:
            self.cb_mode.setCurrentIndex(idx)
        self._on_mode_change(mode)

        self.f_gemini_key.setText(cfg.get("gemini_api_key", ""))
        self.f_mistral_key.setText(cfg.get("mistral_api_key", ""))
        self.f_lmstudio_url.setText(cfg.get("lmstudio_url", "http://localhost:1234"))
        model = cfg.get("lmstudio_model", "local-model")
        idx2 = self.cb_lmstudio_model.findText(model)
        if idx2 >= 0:
            self.cb_lmstudio_model.setCurrentIndex(idx2)
        else:
            self.cb_lmstudio_model.setCurrentText(model)
        self.cb_theme.setCurrentText(cfg.get("app_theme", "dark"))

    def _on_mode_change(self, mode: str):
        labels = {
            "gemini": "✨ Đang dùng: Gemini API (cloud, Google)",
            "mistral": "🔥 Đang dùng: Mistral API — pixtral-12b (cloud)",
            "lmstudio": "💻 Đang dùng: LM Studio (local, offline)",
        }
        self.lbl_mode_status.setText(labels.get(mode, ""))

    def _save(self):
        cfg.set("ocr_mode", self.cb_mode.currentText())
        cfg.set("gemini_api_key", self.f_gemini_key.text().strip())
        cfg.set("mistral_api_key", self.f_mistral_key.text().strip())
        cfg.set("lmstudio_url", self.f_lmstudio_url.text().strip())
        cfg.set("lmstudio_model", self.cb_lmstudio_model.currentText().strip())
        cfg.set("app_theme", self.cb_theme.currentText())
        cfg.save()
        self.accept()

    # =========================================================================
    # CONNECTIVITY TESTS
    # =========================================================================

    def _test_gemini(self):
        # Temp-save key so check_gemini_connection sees it
        cfg.set("gemini_api_key", self.f_gemini_key.text().strip())
        self.btn_test_gemini.setEnabled(False)
        self.lbl_gemini_status.setText("⏳ Đang kiểm tra...")
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        from core.ocr_service import check_gemini_connection
        ok, msg = check_gemini_connection()
        self.btn_test_gemini.setEnabled(True)
        if ok:
            self.lbl_gemini_status.setText(f"<span style='color:#34d399'>✅ {msg}</span>")
        else:
            self.lbl_gemini_status.setText(f"<span style='color:#f87171'>❌ {msg}</span>")
        self.lbl_gemini_status.setTextFormat(Qt.TextFormat.RichText)

    def _test_mistral(self):
        cfg.set("mistral_api_key", self.f_mistral_key.text().strip())
        self.btn_test_mistral.setEnabled(False)
        self.lbl_mistral_status.setText("⏳ Đang kiểm tra...")
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        from core.ocr_service import check_mistral_connection
        ok, msg = check_mistral_connection()
        self.btn_test_mistral.setEnabled(True)
        if ok:
            self.lbl_mistral_status.setText(f"<span style='color:#34d399'>✅ {msg}</span>")
        else:
            self.lbl_mistral_status.setText(f"<span style='color:#f87171'>❌ {msg}</span>")
        self.lbl_mistral_status.setTextFormat(Qt.TextFormat.RichText)

    def _test_lmstudio(self):
        cfg.set("lmstudio_url", self.f_lmstudio_url.text().strip())
        self.btn_test_lmstudio.setEnabled(False)
        self.lbl_lmstudio_status.setText("⏳ Đang kiểm tra...")
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        from core.ocr_service import check_lmstudio_connection
        ok, msg = check_lmstudio_connection()
        self.btn_test_lmstudio.setEnabled(True)
        if ok:
            self.lbl_lmstudio_status.setText(f"<span style='color:#34d399'>✅ {msg}</span>")
            # Auto-fetch models on success
            self._fetch_models()
        else:
            self.lbl_lmstudio_status.setText(f"<span style='color:#f87171'>❌ {msg}</span>")
        self.lbl_lmstudio_status.setTextFormat(Qt.TextFormat.RichText)

    def _fetch_models(self):
        """Fetch available models from LM Studio in background."""
        cfg.set("lmstudio_url", self.f_lmstudio_url.text().strip())
        self.btn_fetch_models.setEnabled(False)
        self.btn_fetch_models.setText("⏳")
        self._fetch_worker = ModelFetchWorker()
        self._fetch_worker.models_ready.connect(self._on_models_fetched)
        self._fetch_worker.start()

    def _on_models_fetched(self, models: list):
        self.btn_fetch_models.setEnabled(True)
        self.btn_fetch_models.setText("🔄")
        if models:
            current = self.cb_lmstudio_model.currentText()
            self.cb_lmstudio_model.clear()
            self.cb_lmstudio_model.addItems(models)
            # Restore previous selection if still available
            idx = self.cb_lmstudio_model.findText(current)
            if idx >= 0:
                self.cb_lmstudio_model.setCurrentIndex(idx)
            self.lbl_lmstudio_status.setText(
                f"<span style='color:#34d399'>✅ Tìm thấy {len(models)} model</span>"
            )
            self.lbl_lmstudio_status.setTextFormat(Qt.TextFormat.RichText)
        else:
            self.lbl_lmstudio_status.setText(
                "<span style='color:#fbbf24'>⚠️ Không tìm thấy model nào. LM Studio đang chạy?</span>"
            )
            self.lbl_lmstudio_status.setTextFormat(Qt.TextFormat.RichText)
