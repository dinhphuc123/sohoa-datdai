#!/bin/bash
# run.sh — Khởi chạy Số hóa Đất đai Desktop
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/venv"

# Create venv if not exists
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Tạo môi trường Python..."
    python3 -m venv "$VENV_DIR" --without-pip
    curl -sS https://bootstrap.pypa.io/get-pip.py | "$VENV_DIR/bin/python"
fi

source "$VENV_DIR/bin/activate"

# Check if packages installed
if ! python -c "import PyQt6" 2>/dev/null; then
    echo "📦 Cài thư viện lần đầu (mất vài phút)..."
    pip install -q -r requirements.txt
    echo "✅ Cài thư viện thành công!"
fi

echo ""
echo "═══════════════════════════════════════"
echo "  🏡 Số hóa Dữ liệu Đất đai Việt Nam"
echo "═══════════════════════════════════════"
echo ""
python main.py
