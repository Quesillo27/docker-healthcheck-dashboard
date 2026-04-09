.PHONY: install run test build clean

install:
	pip install -r requirements.txt

run:
	python3 app.py

test:
	python3 tests/test_smoke.py

build:
	docker build -t docker-healthcheck-dashboard .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
