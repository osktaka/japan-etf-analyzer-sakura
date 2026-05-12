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
    echo "  status      - Show container status"
    echo "  lint        - Run linter"
    echo "  format      - Run formatter"
    echo "  test        - Run tests"
    echo ""
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
        ;;
    backend)
        echo -e "${GREEN}Entering backend container...${NC}"
        docker compose exec backend sh
        ;;
    frontend)
        echo -e "${GREEN}Entering frontend container...${NC}"
        docker compose exec frontend sh
        ;;
    status)
        docker compose ps
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
