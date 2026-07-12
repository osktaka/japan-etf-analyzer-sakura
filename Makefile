.PHONY: help up down logs rebuild lint format test clean setup-hooks

help: ## ヘルプを表示
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ===================
# Docker操作
# ===================
up: ## Docker環境を起動
	docker compose up -d

down: ## Docker環境を停止
	docker compose down

logs: ## ログを表示
	docker compose logs -f

rebuild: ## 再ビルドして起動
	docker compose down
	docker compose build --no-cache
	docker compose up -d

# ===================
# 品質チェック
# ===================
lint: ## リントを実行
	@echo "Linting backend..."
	docker compose exec backend ruff check src/
	@echo "Linting frontend..."
	docker compose exec frontend npm run lint

format: ## フォーマットを実行
	@echo "Formatting backend..."
	docker compose exec backend ruff format src/
	docker compose exec backend ruff check --fix src/
	@echo "Formatting frontend..."
	docker compose exec frontend npm run format

test: ## テストを実行
	@echo "Running backend tests..."
	docker compose exec backend pytest -v

# ===================
# セットアップ
# ===================
setup-hooks: ## pre-commitフック（静的解析+frontend自動ビルド統合）をインストール
	@# 注意: `pre-commit install` は使わない。frontend自動ビルドを上書きで無効化するため。
	@# 統合フック(scripts/pre-commit)が内部で `pre-commit run` を呼ぶ。
	@./scripts/install-hooks.sh

# ===================
# クリーンアップ
# ===================
clean: ## 一時ファイルを削除
	docker compose down -v
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned!"
