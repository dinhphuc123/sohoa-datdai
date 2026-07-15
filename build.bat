@echo off
REM build.bat — Đóng gói ứng dụng cho Windows sử dụng PyInstaller
echo 📦 Đang kiểm tra môi trường Python...

python -m venv venv
call venv\Scripts\activate.bat

echo 📦 Cài đặt thư viện phụ thuộc...
pip install -q pyinstaller -r requirements.txt

echo 🚀 Tiến hành đóng gói ứng dụng Windows (.exe)...
pyinstaller --clean -y dat_dai_desktop.spec

echo.
echo ==========================================================
echo ✅ ĐÓNG GÓI THÀNH CÔNG!
echo 📍 File ứng dụng nằm tại: dist\DatDaiDesktop\DatDaiDesktop.exe
echo ==========================================================
pause
