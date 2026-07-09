# semlayer

A declarative semantic layer for defining entities, dimensions, metrics, and relationships over your data.

See [`docs/schema.md`](docs/schema.md) for the semantic model YAML schema reference.

## Local development setup

Requires Python 3.10+.

```bash
# Clone the repo and enter it
git clone https://github.com/npogeant/semlayer.git
cd semlayer

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install the package in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Linting and formatting

```bash
ruff check .
ruff format .
```

### Running tests

```bash
pytest
```
