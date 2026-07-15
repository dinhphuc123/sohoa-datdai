# ui/land_form.py
"""
Land data entry form for GCN and Hop Dong records.
Displays OCR results in editable form fields.
"""
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QPushButton,
    QGroupBox, QScrollArea, QFrame, QTabWidget, QDateEdit,
    QDoubleSpinBox, QSizePolicy, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QFont


class OwnerEntry(QGroupBox):
    """Single owner/party sub-form."""
    def __init__(self, title: str = "Chủ sở hữu", parent=None):
        super().__init__(title, parent)
        layout = QFormLayout(self)
        layout.setSpacing(6)
        self.f_ho_ten = QLineEdit()
        self.f_ngay_sinh = QLineEdit()
        self.f_cmnd = QLineEdit()
        self.f_dia_chi = QLineEdit()
        layout.addRow("Họ và tên:", self.f_ho_ten)
        layout.addRow("Ngày sinh:", self.f_ngay_sinh)
        layout.addRow("CMND/CCCD:", self.f_cmnd)
        layout.addRow("Địa chỉ:", self.f_dia_chi)

    def set_data(self, d: dict):
        self.f_ho_ten.setText(d.get("ho_ten", ""))
        self.f_ngay_sinh.setText(d.get("ngay_sinh", ""))
        self.f_cmnd.setText(d.get("cmnd_cccd", ""))
        self.f_dia_chi.setText(d.get("dia_chi", ""))

    def get_data(self) -> dict:
        return {
            "ho_ten": self.f_ho_ten.text().strip(),
            "ngay_sinh": self.f_ngay_sinh.text().strip(),
            "cmnd_cccd": self.f_cmnd.text().strip(),
            "dia_chi": self.f_dia_chi.text().strip(),
        }


class GcnForm(QWidget):
    """Form for Giấy Chứng Nhận (GCN / Sổ đỏ)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # ── I. Thông tin GCN ──
        g1 = QGroupBox("I. THÔNG TIN GIẤY CHỨNG NHẬN")
        f1 = QFormLayout(g1)
        f1.setSpacing(6)
        self.f_so_gcn = QLineEdit(); self.f_so_gcn.setPlaceholderText("Số hiệu GCN...")
        self.f_ngay_cap = QLineEdit(); self.f_ngay_cap.setPlaceholderText("dd/mm/yyyy")
        self.f_co_quan_cap = QLineEdit(); self.f_co_quan_cap.setPlaceholderText("UBND tỉnh/huyện...")
        f1.addRow("Số GCN:", self.f_so_gcn)
        f1.addRow("Ngày cấp:", self.f_ngay_cap)
        f1.addRow("Cơ quan cấp:", self.f_co_quan_cap)
        layout.addWidget(g1)

        # ── II. Chủ sở hữu ──
        g2 = QGroupBox("II. CHỦ SỞ HỮU")
        g2_layout = QVBoxLayout(g2)
        self.owner_form = OwnerEntry("Chủ sở hữu")
        g2_layout.addWidget(self.owner_form)
        layout.addWidget(g2)

        # ── III. Thông tin thửa đất ──
        g3 = QGroupBox("III. THỬA ĐẤT")
        f3 = QFormLayout(g3)
        f3.setSpacing(6)
        self.f_so_to = QLineEdit(); self.f_so_to.setPlaceholderText("Số tờ bản đồ")
        self.f_so_thua = QLineEdit(); self.f_so_thua.setPlaceholderText("Số thửa")
        self.f_dien_tich = QLineEdit(); self.f_dien_tich.setPlaceholderText("125.5")
        self.f_don_vi = QComboBox()
        self.f_don_vi.addItems(["m²", "ha"])
        self.f_muc_dich = QComboBox()
        self.f_muc_dich.setEditable(True)
        self.f_muc_dich.addItems([
            "", "Đất ở tại nông thôn (ONT)", "Đất ở tại đô thị (ODT)",
            "Đất trồng lúa (LUC)", "Đất trồng cây lâu năm (CLN)",
            "Đất rừng sản xuất (RSX)", "Đất rừng phòng hộ (RPH)",
            "Đất nuôi trồng thủy sản (NTS)", "Đất thương mại dịch vụ (TMD)",
            "Đất cơ sở sản xuất phi nông nghiệp (SKC)", "Đất khác"
        ])
        self.f_thoi_han = QLineEdit(); self.f_thoi_han.setPlaceholderText("Lâu dài / 50 năm...")
        self.f_nguon_goc = QLineEdit(); self.f_nguon_goc.setPlaceholderText("Nhà nước giao / Được chuyển nhượng...")
        f3.addRow("Số tờ bản đồ:", self.f_so_to)
        f3.addRow("Số thửa:", self.f_so_thua)
        f3.addRow("Diện tích:", self.f_dien_tich)
        f3.addRow("Đơn vị:", self.f_don_vi)
        f3.addRow("Mục đích sử dụng:", self.f_muc_dich)
        f3.addRow("Thời hạn sử dụng:", self.f_thoi_han)
        f3.addRow("Nguồn gốc:", self.f_nguon_goc)
        layout.addWidget(g3)

        # ── IV. Địa chỉ thửa đất ──
        g4 = QGroupBox("IV. ĐỊA CHỈ THỬA ĐẤT")
        f4 = QFormLayout(g4)
        f4.setSpacing(6)
        self.f_so_nha = QLineEdit(); self.f_so_nha.setPlaceholderText("Số nhà")
        self.f_duong = QLineEdit(); self.f_duong.setPlaceholderText("Tên đường/phố")
        self.f_phuong = QLineEdit(); self.f_phuong.setPlaceholderText("Phường/Xã")
        self.f_huyen = QLineEdit(); self.f_huyen.setPlaceholderText("Quận/Huyện")
        self.f_tinh = QLineEdit(); self.f_tinh.setPlaceholderText("Tỉnh/Thành phố")
        f4.addRow("Số nhà:", self.f_so_nha)
        f4.addRow("Đường/Phố:", self.f_duong)
        f4.addRow("Phường/Xã:", self.f_phuong)
        f4.addRow("Quận/Huyện:", self.f_huyen)
        f4.addRow("Tỉnh/Thành:", self.f_tinh)
        layout.addWidget(g4)

        # ── V. Ghi chú ──
        g5 = QGroupBox("V. GHI CHÚ")
        f5 = QVBoxLayout(g5)
        self.f_ghi_chu = QTextEdit()
        self.f_ghi_chu.setFixedHeight(70)
        self.f_ghi_chu.setPlaceholderText("Ghi chú thêm...")
        f5.addWidget(self.f_ghi_chu)
        layout.addWidget(g5)

        layout.addStretch()
        scroll.setWidget(container)
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.addWidget(scroll)

    def fill_from_ocr(self, data: dict):
        self.f_so_gcn.setText(data.get("so_gcn", ""))
        self.f_ngay_cap.setText(data.get("ngay_cap", ""))
        self.f_co_quan_cap.setText(data.get("co_quan_cap", ""))
        self.f_so_to.setText(data.get("so_to_ban_do", ""))
        self.f_so_thua.setText(data.get("so_thua_dat", ""))
        self.f_dien_tich.setText(str(data.get("dien_tich", "")))
        don_vi = data.get("dien_tich_don_vi", "m²")
        idx = self.f_don_vi.findText(don_vi)
        if idx >= 0:
            self.f_don_vi.setCurrentIndex(idx)
        muc_dich = data.get("muc_dich_su_dung", "")
        idx2 = self.f_muc_dich.findText(muc_dich)
        if idx2 >= 0:
            self.f_muc_dich.setCurrentIndex(idx2)
        else:
            self.f_muc_dich.setCurrentText(muc_dich)
        self.f_thoi_han.setText(data.get("thoi_han_su_dung", ""))
        self.f_nguon_goc.setText(data.get("nguon_goc_su_dung", ""))
        self.f_so_nha.setText(data.get("so_nha", ""))
        self.f_duong.setText(data.get("duong_pho", ""))
        self.f_phuong.setText(data.get("phuong_xa", ""))
        self.f_huyen.setText(data.get("quan_huyen", ""))
        self.f_tinh.setText(data.get("tinh_thanh", ""))
        self.f_ghi_chu.setPlainText(data.get("ghi_chu", ""))
        owners = data.get("chu_so_huu", [])
        if owners and isinstance(owners[0], dict):
            self.owner_form.set_data(owners[0])

    def get_data(self) -> dict:
        return {
            "so_gcn": self.f_so_gcn.text().strip(),
            "ngay_cap": self.f_ngay_cap.text().strip(),
            "co_quan_cap": self.f_co_quan_cap.text().strip(),
            "so_to_ban_do": self.f_so_to.text().strip(),
            "so_thua_dat": self.f_so_thua.text().strip(),
            "dien_tich": self.f_dien_tich.text().strip(),
            "dien_tich_don_vi": self.f_don_vi.currentText(),
            "muc_dich_su_dung": self.f_muc_dich.currentText(),
            "thoi_han_su_dung": self.f_thoi_han.text().strip(),
            "nguon_goc_su_dung": self.f_nguon_goc.text().strip(),
            "so_nha": self.f_so_nha.text().strip(),
            "duong_pho": self.f_duong.text().strip(),
            "phuong_xa": self.f_phuong.text().strip(),
            "quan_huyen": self.f_huyen.text().strip(),
            "tinh_thanh": self.f_tinh.text().strip(),
            "ghi_chu": self.f_ghi_chu.toPlainText().strip(),
            "chu_so_huu": [self.owner_form.get_data()],
        }


class HopDongForm(QWidget):
    """Form for Hợp đồng chuyển nhượng."""
    def __init__(self, parent=None):
        super().__init__(parent)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # ── I. Thông tin hợp đồng ──
        g1 = QGroupBox("I. THÔNG TIN HỢP ĐỒNG")
        f1 = QFormLayout(g1)
        f1.setSpacing(6)
        self.f_so_hd = QLineEdit(); self.f_so_hd.setPlaceholderText("Số hợp đồng...")
        self.f_ngay_ky = QLineEdit(); self.f_ngay_ky.setPlaceholderText("dd/mm/yyyy")
        self.f_noi_ky = QLineEdit(); self.f_noi_ky.setPlaceholderText("Tỉnh/Thành phố nơi ký")
        self.f_gia = QLineEdit(); self.f_gia.setPlaceholderText("Giá bằng số (VNĐ)")
        self.f_don_vi_tien = QComboBox()
        self.f_don_vi_tien.addItems(["VND", "USD"])
        self.f_phuong_thuc = QComboBox()
        self.f_phuong_thuc.setEditable(True)
        self.f_phuong_thuc.addItems([
            "", "Tiền mặt", "Chuyển khoản", "Hỗn hợp", "Trả góp"
        ])
        self.f_thoi_gian_ban_giao = QLineEdit(); self.f_thoi_gian_ban_giao.setPlaceholderText("dd/mm/yyyy hoặc mô tả")
        f1.addRow("Số hợp đồng:", self.f_so_hd)
        f1.addRow("Ngày ký:", self.f_ngay_ky)
        f1.addRow("Nơi ký:", self.f_noi_ky)
        f1.addRow("Giá chuyển nhượng:", self.f_gia)
        f1.addRow("Đơn vị tiền:", self.f_don_vi_tien)
        f1.addRow("Phương thức TT:", self.f_phuong_thuc)
        f1.addRow("Thời gian bàn giao:", self.f_thoi_gian_ban_giao)
        layout.addWidget(g1)

        # ── II. Bên chuyển nhượng ──
        self.form_chuyen = OwnerEntry("II. BÊN CHUYỂN NHƯỢNG")
        layout.addWidget(self.form_chuyen)

        # ── III. Bên nhận chuyển nhượng ──
        self.form_nhan = OwnerEntry("III. BÊN NHẬN CHUYỂN NHƯỢNG")
        layout.addWidget(self.form_nhan)

        # ── IV. Thông tin thửa đất ──
        g4 = QGroupBox("IV. THÔNG TIN THỬA ĐẤT")
        f4 = QFormLayout(g4)
        f4.setSpacing(6)
        self.f_so_to = QLineEdit(); self.f_so_to.setPlaceholderText("Số tờ bản đồ")
        self.f_so_thua = QLineEdit(); self.f_so_thua.setPlaceholderText("Số thửa")
        self.f_dien_tich = QLineEdit(); self.f_dien_tich.setPlaceholderText("m²")
        self.f_dia_chi_thua = QLineEdit(); self.f_dia_chi_thua.setPlaceholderText("Địa chỉ thửa đất")
        self.f_so_gcn_lq = QLineEdit(); self.f_so_gcn_lq.setPlaceholderText("Số GCN liên quan")
        f4.addRow("Số tờ bản đồ:", self.f_so_to)
        f4.addRow("Số thửa:", self.f_so_thua)
        f4.addRow("Diện tích (m²):", self.f_dien_tich)
        f4.addRow("Địa chỉ thửa:", self.f_dia_chi_thua)
        f4.addRow("Số GCN liên quan:", self.f_so_gcn_lq)
        layout.addWidget(g4)

        # ── V. Công chứng ──
        g5 = QGroupBox("V. CÔNG CHỨNG")
        f5 = QFormLayout(g5)
        f5.setSpacing(6)
        self.f_ccv = QLineEdit(); self.f_ccv.setPlaceholderText("Họ tên công chứng viên")
        self.f_vpcc = QLineEdit(); self.f_vpcc.setPlaceholderText("Tên văn phòng công chứng")
        self.f_so_cc = QLineEdit(); self.f_so_cc.setPlaceholderText("Số công chứng")
        self.f_ngay_cc = QLineEdit(); self.f_ngay_cc.setPlaceholderText("dd/mm/yyyy")
        f5.addRow("Công chứng viên:", self.f_ccv)
        f5.addRow("VP Công chứng:", self.f_vpcc)
        f5.addRow("Số công chứng:", self.f_so_cc)
        f5.addRow("Ngày công chứng:", self.f_ngay_cc)
        layout.addWidget(g5)

        g6 = QGroupBox("VI. GHI CHÚ")
        f6l = QVBoxLayout(g6)
        self.f_ghi_chu = QTextEdit()
        self.f_ghi_chu.setFixedHeight(70)
        f6l.addWidget(self.f_ghi_chu)
        layout.addWidget(g6)

        layout.addStretch()
        scroll.setWidget(container)
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.addWidget(scroll)

    def fill_from_ocr(self, data: dict):
        self.f_so_hd.setText(data.get("so_hop_dong", ""))
        self.f_ngay_ky.setText(data.get("ngay_ky", ""))
        self.f_noi_ky.setText(data.get("noi_ky", ""))
        self.f_gia.setText(str(data.get("gia_chuyen_nhuong", "")))
        self.f_phuong_thuc.setCurrentText(data.get("phuong_thuc_thanh_toan", ""))
        self.f_thoi_gian_ban_giao.setText(data.get("thoi_gian_ban_giao", ""))
        thua = data.get("thong_tin_thua_dat") or {}
        self.f_so_to.setText(thua.get("so_to_ban_do", ""))
        self.f_so_thua.setText(thua.get("so_thua_dat", ""))
        self.f_dien_tich.setText(str(thua.get("dien_tich", "")))
        self.f_dia_chi_thua.setText(thua.get("dia_chi", ""))
        self.f_so_gcn_lq.setText(thua.get("so_gcn", ""))
        self.f_ccv.setText(data.get("cong_chung_vien", ""))
        self.f_vpcc.setText(data.get("van_phong_cong_chung", ""))
        self.f_so_cc.setText(data.get("so_cong_chung", ""))
        self.f_ngay_cc.setText(data.get("ngay_cong_chung", ""))
        self.f_ghi_chu.setPlainText(data.get("ghi_chu", ""))
        ben_chuyen = data.get("ben_chuyen_nhuong", [])
        if ben_chuyen and isinstance(ben_chuyen[0], dict):
            self.form_chuyen.set_data(ben_chuyen[0])
        ben_nhan = data.get("ben_nhan_chuyen_nhuong", [])
        if ben_nhan and isinstance(ben_nhan[0], dict):
            self.form_nhan.set_data(ben_nhan[0])

    def get_data(self) -> dict:
        return {
            "so_hop_dong": self.f_so_hd.text().strip(),
            "ngay_ky": self.f_ngay_ky.text().strip(),
            "noi_ky": self.f_noi_ky.text().strip(),
            "gia_chuyen_nhuong": self.f_gia.text().strip(),
            "don_vi_tien": self.f_don_vi_tien.currentText(),
            "phuong_thuc_thanh_toan": self.f_phuong_thuc.currentText(),
            "thoi_gian_ban_giao": self.f_thoi_gian_ban_giao.text().strip(),
            "ben_chuyen_nhuong": [self.form_chuyen.get_data()],
            "ben_nhan_chuyen_nhuong": [self.form_nhan.get_data()],
            "thong_tin_thua_dat": {
                "so_to_ban_do": self.f_so_to.text().strip(),
                "so_thua_dat": self.f_so_thua.text().strip(),
                "dien_tich": self.f_dien_tich.text().strip(),
                "dia_chi": self.f_dia_chi_thua.text().strip(),
                "so_gcn": self.f_so_gcn_lq.text().strip(),
            },
            "cong_chung_vien": self.f_ccv.text().strip(),
            "van_phong_cong_chung": self.f_vpcc.text().strip(),
            "so_cong_chung": self.f_so_cc.text().strip(),
            "ngay_cong_chung": self.f_ngay_cc.text().strip(),
            "ghi_chu": self.f_ghi_chu.toPlainText().strip(),
        }
