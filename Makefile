.PHONY: install run test

PORT ?= 5050

install:
	pip install -r requirements.txt

run:
	PORT=$(PORT) python3 app.py

test:
	python3 tests/test_smoke.py
