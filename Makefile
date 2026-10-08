# ==============================================================================
# SecureFlow DevSecOps Automation Makefile
# ==============================================================================

.PHONY: setup test run docker k8s scan clean

setup:
	pip install -r requirements.txt
	python -m scripts.seed

test:
	python -m pytest tests/ --cov=src/secureflow --cov-report=term-missing --cov-report=html:evidence/htmlcov

run:
	python -m uvicorn secureflow.main:app --host 127.0.0.1 --port 8000 --reload

sim:
	python simulator/sensor_sim.py

docker:
	docker compose up --build

k8s:
	bash scripts/minikube_deploy.sh

scan:
	ruff check src/ tests/
	bandit -r src/ -c pyproject.toml

clean:
	rm -rf .pytest_cache .coverage htmlcov/ evidence/htmlcov *.db
