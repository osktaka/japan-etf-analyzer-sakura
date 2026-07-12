#!/bin/bash
# Git hooks installer: 統合 pre-commit フック（静的解析 + frontend自動ビルド）を導入する。
# 注意: `pre-commit install`（フレームワークの直接インストール）は使わない。
#       それは .git/hooks/pre-commit を上書きし、frontend自動ビルドを無効化するため。
#       静的解析は本フック内から `pre-commit run` 経由で実行される。

set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
GIT_HOOKS_DIR="$PROJECT_ROOT/.git/hooks"

echo "Installing Git hooks..."

# Copy pre-commit hook
cp "$SCRIPT_DIR/pre-commit" "$GIT_HOOKS_DIR/pre-commit"
chmod +x "$GIT_HOOKS_DIR/pre-commit"

echo "✓ pre-commit hook installed"
echo ""
echo "Hook installed successfully!"
echo "コミット時に静的解析（ruff/eslint/prettier）が実行され、"
echo "frontend/src 変更時は自動ビルド＋dist ステージングが行われます。"
