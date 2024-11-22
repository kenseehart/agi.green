# Contributing to AGI.green

Thank you for your interest in contributing to AGI.green! This document provides guidelines and information for contributors.

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/kenseehart/agi.green.git
cd agi.green
```

2. Create and activate a Conda environment:
```bash
conda env create -f environment.yaml
conda activate agi-green
```

3. Install development dependencies:
```bash
pip install -e ".[dev]"
```

## Development Guidelines

### Code Style
- We use [Black](https://black.readthedocs.io/) for code formatting
- We use [isort](https://pycqa.github.io/isort/) for import sorting
- Run formatters before committing:
```bash
black .
isort .
