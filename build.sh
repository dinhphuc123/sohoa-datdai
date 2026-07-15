#!/bin/bash
# build.sh — Đóng gói ứng dụng cho Linux / macOS sử dụng PyInstaller
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Tạo venv..."
    python3 -m venv "$VENV_DIR" --without-pip
    curl -sS https://bootstrap.pypa.io/get-pip.py | "$VENV_DIR/bin/python"
fi

source "$VENV_DIR/bin/activate"

echo "📦 Đang cài đặt thư viện đóng gói..."
pip install -q pyinstaller -r requirements.txt

echo ""
echo "🚀 Đang tiến hành đóng gói PyInstaller..."
pyinstaller --clean -y dat_dai_desktop.spec

echo ""
echo "=========================================================="
echo "✅ ĐÓNG GÓI THÀNH CÔNG!"
echo "📍 Sản phẩm nằm trong thư mục: $SCRIPT_DIR/dist/DatDaiDesktop/"
echo "=========================================================="
