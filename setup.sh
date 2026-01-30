#!/bin/bash
set -e

echo "========================================="
echo "  Japan ETF Analyzer - 本番環境セットアップ"
echo "========================================="

PROJECT_ROOT=$(cd "$(dirname "$0")" && pwd)
cd "$PROJECT_ROOT"

# Pythonパス確認（pyenv優先、なければシステムPython）
if [ -f "$HOME/.pyenv/versions/3.9.18/bin/python3" ]; then
    PYTHON_PATH="$HOME/.pyenv/versions/3.9.18/bin/python3"
elif [ -x "/usr/local/bin/python3" ]; then
    PYTHON_PATH="/usr/local/bin/python3"
else
    echo "Error: Python3 not found"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_PATH --version)
echo "Python: $PYTHON_VERSION"

# venv作成
echo ""
echo "[1/5] Creating virtual environment..."
if [ ! -d "backend/venv" ]; then
    $PYTHON_PATH -m venv backend/venv
    echo "  ✓ venv created at backend/venv"
else
    echo "  ✓ venv already exists"
fi

# 依存関係インストール
echo ""
echo "[2/5] Installing backend dependencies..."
source backend/venv/bin/activate
pip install --upgrade pip
# TMPDIR設定（/tmp, /var/tmpがnoexecの場合の対策）
export TMPDIR="$HOME/tmp"
mkdir -p "$TMPDIR"
pip install -r backend/requirements.txt
echo "  ✓ Dependencies installed"

# .env確認
echo ""
echo "[3/5] Checking .env file..."
if [ ! -f ".env" ]; then
    echo "  Warning: .env file not found!"
    echo "  Please create .env from .env.example:"
    echo "    cp .env.example .env"
    echo "    vi .env  # Edit SECRET_KEY and other settings"
    echo ""
    echo "  Required variables:"
    echo "    - SECRET_KEY (generate with: python3 -c 'import secrets; print(secrets.token_hex(32))')"
    echo "    - DATABASE_URL (default: sqlite:///data/etf.db)"
    echo "    - USE_MOCK_DATA (true for testing, false for production)"
else
    echo "  ✓ .env file exists"
fi

# dataディレクトリ作成
echo ""
echo "[4/5] Creating data directory..."
mkdir -p data
echo "  ✓ data directory created"

# 権限設定
echo ""
echo "[5/5] Setting permissions..."
chmod 755 api/index.cgi
chmod 755 setup.sh
chmod 644 .htaccess
echo "  ✓ Permissions set"

echo ""
echo "========================================="
echo "  Setup completed!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Create .env file (if not exists): cp .env.example .env"
echo "  2. Edit .env to set SECRET_KEY and other configs"
echo "  3. Initialize database:"
echo "       source backend/venv/bin/activate"
echo "       cd backend"
echo "       python scripts/init_db.py"
echo "       python scripts/seed_data.py"
echo "       python scripts/sync_etf_master.py"
echo "  4. Verify CGI execution:"
echo "       curl http://your-domain/japan-etf-analyzer/api/v1/health"
echo ""
