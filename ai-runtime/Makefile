.PHONY: server client install test clean

install:
	pip install -e .

server:
	uvicorn server.app.main:app --host 0.0.0.0 --port 8000 --reload

client:
	python -m client.cli.submit_job --prompt "Test prompt"

test:
	pytest

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +

