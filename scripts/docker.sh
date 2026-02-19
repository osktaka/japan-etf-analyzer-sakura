#!/bin/bash

set -e

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ヘルプ表示
show_help() {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  up          - Start all services"
    echo "  down        - Stop all services"
    echo "  logs        - Show logs (optional: service name)"
    echo "  rebuild     - Rebuild and start all services"
    echo "  backend     - Enter the backend container"
    echo "  frontend    - Enter the frontend container"
    echo "  scheduler   - Enter the scheduler container"
    echo "  status      - Show container status"
    echo "  check       - Verify scheduler mount"
    echo "  lint        - Run linter"
    echo "  format      - Run formatter"
    echo "  test        - Run tests"
    echo ""
}

# schedulerコンテナのマウント検証
verify_scheduler_mount() {
    echo -e "${GREEN}Verifying scheduler mount...${NC}"
    local file_count
    file_count=$(docker compose exec scheduler sh -c 'ls /app/scripts/ 2>/dev/null | wc -l' 2>/dev/null || echo "0")
    # 余分な空白を除去
    file_count=$(echo "$file_count" | tr -d '[:space:]')

    if [ "$file_count" = "0" ]; then
        echo -e "${YELLOW}Warning: /app/scripts/ is empty in scheduler container.${NC}"
        echo -e "${YELLOW}Attempting to recover by restarting scheduler...${NC}"
        docker compose restart scheduler || true
        sleep 3
        file_count=$(docker compose exec scheduler sh -c 'ls /app/scripts/ 2>/dev/null | wc -l' 2>/dev/null || echo "0")
        file_count=$(echo "$file_count" | tr -d '[:space:]')
        if [ "$file_count" = "0" ]; then
            echo -e "${RED}Recovery failed: /app/scripts/ is still empty.${NC}"
            return 1
        else
            echo -e "${GREEN}Recovery succeeded: $file_count file(s) found in /app/scripts/.${NC}"
        fi
    else
        echo -e "${GREEN}Scheduler mount OK: $file_count file(s) found in /app/scripts/.${NC}"
    fi
}

case "$1" in
    up)
        echo -e "${GREEN}Starting services...${NC}"
        docker compose up -d
        echo -e "${GREEN}Services started.${NC}"
        sleep 3
        # frontendパッケージ検証: ホスト側のpackage.jsonが更新されている場合に同期
        echo -e "${GREEN}Verifying frontend packages...${NC}"
        npm_output=$(docker compose exec frontend npm install --prefer-offline 2>&1 || true)
        if echo "$npm_output" | grep -q "added"; then
            echo -e "${YELLOW}New packages detected. Restarting frontend...${NC}"
            docker compose restart frontend
        else
            echo -e "${GREEN}Frontend packages OK.${NC}"
        fi
        verify_scheduler_mount || true
        ;;
    down)
        echo -e "${YELLOW}Stopping services...${NC}"
        docker compose down
        echo -e "${YELLOW}Services stopped.${NC}"
        ;;
    logs)
        docker compose logs -f "${@:2}"
        ;;
    rebuild)
        echo -e "${YELLOW}Rebuilding services...${NC}"
        docker compose down
        docker compose build --no-cache
        docker compose up -d
        echo -e "${GREEN}Services rebuilt and started.${NC}"
        sleep 3
        verify_scheduler_mount || true
        ;;
    backend)
        echo -e "${GREEN}Entering backend container...${NC}"
        docker compose exec backend sh
        ;;
    frontend)
        echo -e "${GREEN}Entering frontend container...${NC}"
        docker compose exec frontend sh
        ;;
    scheduler)
        echo -e "${GREEN}Entering scheduler container...${NC}"
        docker compose exec scheduler bash
        ;;
    status)
        docker compose ps
        ;;
    check)
        verify_scheduler_mount
        ;;
    lint)
        echo -e "${GREEN}Running linter...${NC}"
        docker compose exec backend ruff check src/
        docker compose exec frontend npm run lint
        ;;
    format)
        echo -e "${GREEN}Running formatter...${NC}"
        docker compose exec backend ruff format src/
        docker compose exec backend ruff check --fix src/
        docker compose exec frontend npm run format
        ;;
    test)
        echo -e "${GREEN}Running tests...${NC}"
        docker compose exec backend pytest -v
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac
