# 🏡 Số hóa Dữ liệu Đất đai Việt Nam — Desktop App (PyQt6)

Ứng dụng Desktop chuyên nghiệp để số hóa hồ sơ địa chính (GCN / Sổ đỏ, Hợp đồng chuyển nhượng) sử dụng AI (Gemini 3.5 Flash, Mistral API, LM Studio).

## 🚀 Tính năng chính
- OCR & phân tích dữ liệu đất đai chính xác với Gemini 3.5 Flash / Mistral / Local LM Studio.
- Quản lý CSDL SQLite tích hợp Full-Text Search (FTS5).
- Giao diện Dark Theme hiện đại, xem & cắt vùng ảnh tương tác.
- Xuất báo cáo Excel và PDF theo mẫu.

## 🛠 Hướng dẫn Đóng gói Đa nền tảng với GitHub Actions

Ứng dụng đã được tích hợp sẵn luồng tự động đóng gói đa nền tảng **GitHub Actions** tại file `.github/workflows/build.yml`.

### Các bước thực hiện:

1. **Tạo Repository mới trên GitHub** (ví dụ `dat-dai-desktop`).

2. **Kết nối mã nguồn local với GitHub:**
   ```bash
   cd /home/phuc/Downloads/dat_dai_desktop
   git remote add origin https://github.com/USERNAME/dat-dai-desktop.git
   git push -u origin main
   ```

3. **Xem kết quả Tự động Biên dịch:**
   - Truy cập tab **Actions** trên GitHub repository của bạn.
   - Luồng `Build Cross-Platform Desktop Apps` sẽ tự động chạy song song trên 3 hệ điều hành:
     - 🪟 **Windows**: Tạo file `DatDaiDesktop-Windows.zip` (chứa `DatDaiDesktop.exe`)
     - 🍏 **macOS**: Tạo file `DatDaiDesktop-macOS.zip` (chứa `DatDaiDesktop.app`)
     - 🐧 **Linux**: Tạo file `DatDaiDesktop-Linux.tar.gz` (chứa binary thực thi)

4. **Tạo bản phát hành chính thức (Release):**
   Mỗi khi muốn phát hành phiên bản mới cho người dùng:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
   GitHub Actions sẽ tự động thu gom cả 3 bản build và đính kèm vào mục **Releases** trên GitHub để người dùng tải về trực tiếp.
