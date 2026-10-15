# iTop MCP Server - Development Makefile

.PHONY: help install install-dev test test-unit test-live test-nodejs lint lint-fix format clean build publish

# Default target
help:
	@echo "🧪 iTop MCP Server Development Commands"
	@echo "====================================="
	@echo ""
	@echo "📦 Installation:"
	@echo "  install      - Install package dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  test         - Run all tests"
	@echo "  test-unit    - Run unit tests only"
	@echo "  test-live    - Run live tests only (requires iTop instance)"
	@echo "  test-nodejs  - Run Node.js tests only"
	@echo ""
	@echo "🔧 Code Quality:"
	@echo "  lint         - Run linting checks"
	@echo "  lint-fix     - Auto-fix linting issues"
	@echo "  format       - Format code with Black and isort"
	@echo ""
	@echo "🚀 Build & Publish:"
	@echo "  build        - Build package"
	@echo "  publish      - Publish to PyPI"
	@echo "  clean        - Clean build artifacts"
	@echo ""
	@echo "💡 Environment variables needed for live tests:"
	@echo "  ITOP_BASE_URL, ITOP_USER, ITOP_PASSWORD"

# Installation
install:
	@echo "📦 Installing dependencies..."
	pip install -e .

install-dev:
	@echo "📦 Installing development dependencies..."
	pip install -e .[dev]

# Testing
test:
	@echo "🧪 Running all tests..."
	python tests/run_tests.py

test-unit:
	@echo "🧪 Running unit tests..."
	python tests/run_tests.py --unit

test-live:
	@echo "🧪 Running live tests..."
	@if [ -z "$$ITOP_BASE_URL" ] || [ -z "$$ITOP_USER" ] || [ -z "$$ITOP_PASSWORD" ]; then \
		echo "⚠️  Missing environment variables. Set ITOP_BASE_URL, ITOP_USER, and ITOP_PASSWORD"; \
		exit 1; \
	fi
	python tests/run_tests.py --live

test-nodejs:
	@echo "🧪 Running Node.js tests..."
	python tests/run_tests.py --nodejs

# Code Quality
lint:
	@echo "🔍 Running linting checks..."
	python tests/run_tests.py --lint

lint-fix:
	@echo "🔧 Auto-fixing linting issues..."
	python tests/run_tests.py --fix

format:
	@echo "🎨 Formatting code..."
	black .
	isort .

# Build & Publish
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf dist/ build/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

build: clean
	@echo "🏗️  Building package..."
	python -m build

publish: build
	@echo "🚀 Publishing to PyPI..."
	@read -p "Are you sure you want to publish? (y/N) " confirm && [ "$$confirm" = "y" ]
	python -m twine upload dist/*

# Development shortcuts
dev-setup: install-dev
	@echo "🔧 Setting up development environment..."
	@echo "✅ Development environment ready!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Set environment variables:"
	@echo "   export ITOP_BASE_URL='https://your-itop-instance.com'"
	@echo "   export ITOP_USER='your-username'"
	@echo "   export ITOP_PASSWORD='your-password'"
	@echo "2. Run tests: make test"

# Node.js specific targets
nodejs-install:
	@echo "📦 Installing Node.js dependencies..."
	cd nodejs && npm install

nodejs-build:
	@echo "🏗️  Building Node.js implementation..."
	cd nodejs && npm run build

nodejs-lint:
	@echo "🔍 Linting Node.js code..."
	cd nodejs && npm run lint

nodejs-lint-fix:
	@echo "🔧 Auto-fixing Node.js linting issues..."
	cd nodejs && npm run lint:fix

# Combined targets
all-install: install-dev nodejs-install
	@echo "✅ All dependencies installed!"

all-lint: lint nodejs-lint
	@echo "✅ All linting checks completed!"

all-build: build nodejs-build
	@echo "✅ All builds completed!"

# Quick development cycle
quick-check: format lint test-unit
	@echo "✅ Quick development check completed!"

# Pre-commit checks
pre-commit: format lint test-unit
	@echo "✅ Pre-commit checks passed!"

# Full CI pipeline
ci: install-dev format lint test-unit test-nodejs build
	@echo "✅ CI pipeline completed!"
