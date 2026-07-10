from dataclasses import MISSING, fields
from pathlib import Path

import yaml

from semlayer.models import Dimension, Entity, Metric, Relationship, SemanticModel

SECTIONS = {
    "entities": Entity,
    "dimensions": Dimension,
    "metrics": Metric,
    "relationships": Relationship,
}


class SemanticModelLoadError(Exception):
    pass


def load_semantic_model(path: str | Path) -> SemanticModel:
    """Load a semantic model from a YAML file or a directory of YAML files.

    When `path` is a directory, every `*.yaml` / `*.yml` file directly in it
    is loaded and merged: each section (entities, dimensions, metrics,
    relationships) is the concatenation of that section across all files.
    """
    path = Path(path)
    if path.is_dir():
        # Sorted for a deterministic merge order regardless of filesystem.
        files = sorted(p for p in path.iterdir() if p.suffix in (".yaml", ".yml"))
        if not files:
            raise SemanticModelLoadError(f"No YAML files found in {path}")
    elif path.is_file():
        files = [path]
    else:
        raise SemanticModelLoadError(f"{path} does not exist")

    model = SemanticModel()
    for file in files:
        raw = _read_yaml(file)
        parsed = _parse_document(raw, source=file)
        model.entities.extend(parsed["entities"])
        model.dimensions.extend(parsed["dimensions"])
        model.metrics.extend(parsed["metrics"])
        model.relationships.extend(parsed["relationships"])
    return model


def _read_yaml(path: Path):
    try:
        with path.open() as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise SemanticModelLoadError(f"Failed to parse YAML in {path}: {exc}") from exc
    except OSError as exc:
        raise SemanticModelLoadError(f"Could not read {path}: {exc}") from exc


def _parse_document(raw, source: Path) -> dict[str, list]:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise SemanticModelLoadError(
            f"{source} must contain a mapping at the top level, got {type(raw).__name__}"
        )

    unknown_sections = raw.keys() - SECTIONS.keys()
    if unknown_sections:
        raise SemanticModelLoadError(
            f"{source} has unknown top-level section(s): {', '.join(sorted(unknown_sections))}"
        )

    result: dict[str, list] = {}
    for section, model_cls in SECTIONS.items():
        items = raw.get(section, [])
        if not isinstance(items, list):
            raise SemanticModelLoadError(
                f"'{section}' in {source} must be a list, got {type(items).__name__}"
            )
        result[section] = [
            _construct(model_cls, item, kind=model_cls.__name__, source=source) for item in items
        ]
    return result


def _construct(model_cls, raw, kind: str, source: Path):
    if not isinstance(raw, dict):
        raise SemanticModelLoadError(
            f"{kind} in {source} must be a mapping, got {type(raw).__name__}"
        )

    model_fields = fields(model_cls)
    known = {f.name for f in model_fields}
    required = {
        f.name for f in model_fields if f.default is MISSING and f.default_factory is MISSING
    }

    missing = required - raw.keys()
    if missing:
        raise SemanticModelLoadError(
            f"{kind} in {source} is missing required field(s): {', '.join(sorted(missing))}"
        )

    unknown = raw.keys() - known
    if unknown:
        raise SemanticModelLoadError(
            f"{kind} in {source} has unknown field(s): {', '.join(sorted(unknown))}"
        )

    return model_cls(**raw)
