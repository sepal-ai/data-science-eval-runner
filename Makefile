# Data Science Agent Evaluation System Makefile

PYTHON = python3
VENV = venv
VENV_BIN = $(VENV)/bin
VENV_PYTHON = $(VENV_BIN)/python
VENV_PIP = $(VENV_BIN)/pip

.PHONY: help
help:
	@echo "Data Science Agent Evaluation System"
	@echo "====================================="
	@echo ""
	@echo "Commands:"
	@echo "  setup     - Create virtual environment and install dependencies"
	@echo "  clean     - Remove virtual environment and data files"
	@echo "  test      - Run basic validation"

.PHONY: setup
setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -e .
	@echo ""
	@echo "✅ Setup complete!"
	@echo "To activate: source $(VENV)/bin/activate"
	@echo "To validate: $(VENV_PYTHON) -m ds_runner validate-setup"
	@echo "To setup data: $(VENV_PYTHON) -m ds_runner setup-data"

.PHONY: clean
clean:
	rm -rf $(VENV)
	rm -f data.db
	rm -rf __pycache__ src/__pycache__ ds_runner/__pycache__ *.egg-info

.PHONY: test
test:
	$(VENV_PYTHON) -m ds_runner validate-setup
	$(VENV_PYTHON) -m ds_runner list-problems 