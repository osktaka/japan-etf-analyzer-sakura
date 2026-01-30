#!/bin/bash
# Git hooks installer for automatic frontend build

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
echo "Frontend will be automatically built and staged when frontend/src files are changed."
