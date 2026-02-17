# Makefile for Agora project

.PHONY: help setup start stop status test clean backend-dev frontend-dev logs health upload

help:
	@echo "Agora Makefile Commands:"
	@echo ""
	@echo "  make setup        - Complete project setup"
	@echo "  make start        - Start all services (quick-start.sh)"
	@echo "  make stop         - Stop all services (stop-all.sh)"
	@echo "  make status       - Check status of all services"
	@echo "  make backend-dev  - Start backend in development mode"
	@echo "  make frontend-dev - Start frontend in development mode"
	@echo "  make logs         - Tail all logs"
	@echo "  make health       - Check backend health"
	@echo "  make upload       - Test file upload"
	@echo "  make test         - Run all tests"
	@echo "  make clean        - Clean up temporary files"
	@echo ""

setup:
	@echo "Running setup..."
	@bash setup.sh

start:
	@echo "Starting all services..."
	@bash quick-start.sh

stop:
	@echo "Stopping all services..."
	@bash stop-all.sh

status:
	@echo "Checking service status..."
	@echo ""
	@echo "Backend:"
	@curl -s http://localhost:8000/health | jq . || echo "❌ Not running"
	@echo ""
	@echo "Frontend:"
	@curl -s -I http://localhost:3000 2>/dev/null | head -1 || echo "❌ Not running"
	@echo ""
	@echo "Qdrant:"
	@curl -s http://localhost:6333 | jq -r .title || echo "❌ Not running"

backend-dev:
	@echo "Starting backend development server..."
	@cd backend && /Users/AshishR_T/miniconda3/envs/agora/bin/python -m app.main

frontend-dev:
	@echo "Starting frontend development server..."
	@cd frontendOther && pnpm dev

logs:
	@echo "Tailing logs (Ctrl+C to stop)..."
	@tail -f /tmp/agora_backend.log /tmp/agora_frontend.log 2>/dev/null || echo "No logs found"

health:
	@curl -s http://localhost:8000/health | jq .

upload:
	@echo "Testing upload endpoint..."
	@echo "Test content for upload" > /tmp/test_upload.txt
	@curl -X POST http://localhost:8000/api/materials/upload \
		-F "file=@/tmp/test_upload.txt" \
		-F "user_id=test-user" \
		-F "course_id=test-course" | jq .

test:
	@echo "Running tests..."
	@cd backend && conda run -n agora pytest

clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@rm -f /tmp/test_upload.txt
	@echo "Cleanup complete"
