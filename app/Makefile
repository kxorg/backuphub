.PHONY: help test test-cov test-html test-parallel test-api test-web test-ci

help:
	@echo "Доступные команды:"
	@echo "  make test          - Запуск всех тестов"
	@echo "  make test-cov      - Запуск с покрытием"
	@echo "  make test-html     - Запуск с HTML отчетом"
	@echo "  make test-parallel - Параллельный запуск"
	@echo "  make test-api      - Только API тесты"
	@echo "  make test-web      - Только Web тесты"
	@echo "  make test-ci       - Запуск как в CI"

test:
	cd app && pytest --nomigrations -v

test-cov:
	cd app && pytest --cov=core --cov-report=term-missing --nomigrations

test-html:
	cd app && pytest --cov=core --cov-report=html --nomigrations
	@echo "Отчет открыт в htmlcov/index.html"

test-parallel:
	cd app && pytest -n auto --dist=loadscope --nomigrations

test-api:
	cd app && pytest -m api --nomigrations -v

test-web:
	cd app && pytest -m web --nomigrations -v

test-ci:
	cd app && pytest --cov=core --cov-report=xml --cov-fail-under=80 --nomigrations -v