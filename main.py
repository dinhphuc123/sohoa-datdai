# main.py
"""
Dat Dai Desktop — Entry point
Số hóa Dữ liệu Đất đai Việt Nam
"""
import sys
import os

# Add project root to path
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.main_window import MainWindow
from core import config_manager as cfg


def load_stylesheet(app: QApplication):
    qss_path = os.path.join(BASE_DIR, "assets", "style.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())


def main():
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Dat Dai Desktop")
    app.setApplicationDisplayName("🏡 Số hóa Đất đai VN")
    app.setOrganizationName("DatDaiVN")

    # Font
    font = QFont("Segoe UI", 10)
    font.setHintingPreference(QFont.HintingPreference.PreferDefaultHinting)
    app.setFont(font)

    # Load stylesheet
    load_stylesheet(app)

    # Init DB
    from core import database
    database.init_db()

    # Show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
