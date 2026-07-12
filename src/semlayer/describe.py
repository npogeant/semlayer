from semlayer.models import Dimension, Entity, Metric, Relationship, SemanticModel


class DescribeError(Exception):
    pass


def describe_entities(model: SemanticModel) -> str:
    if not model.entities:
        return "No entities defined."
    return "\n".join(_summarize_entity(entity) for entity in model.entities)


def describe_entity(model: SemanticModel, name: str) -> str:
    entity = _find(model.entities, name, kind="entity")

    lines = [
        f"Entity: {entity.name}",
        f"Table: {entity.table}",
        f"Primary key: {entity.primary_key}",
    ]
    if entity.description:
        lines.append(f"Description: {entity.description}")

    dimensions = [d for d in model.dimensions if d.entity == entity.name]
    lines += ["", "Dimensions:"]
    lines += [f"  - {_summarize_dimension(d)}" for d in dimensions] if dimensions else ["  (none)"]

    relationships = [
        r for r in model.relationships if entity.name in (r.source_entity, r.target_entity)
    ]
    lines += ["", "Relationships:"]
    lines += (
        [f"  - {_summarize_relationship(r)}" for r in relationships]
        if relationships
        else ["  (none)"]
    )

    return "\n".join(lines)


def describe_metrics(model: SemanticModel) -> str:
    if not model.metrics:
        return "No metrics defined."
    return "\n".join(_summarize_metric(metric) for metric in model.metrics)


def describe_metric(model: SemanticModel, name: str) -> str:
    metric = _find(model.metrics, name, kind="metric")

    lines = [
        f"Metric: {metric.name}",
        f"Entity: {metric.entity}",
        f"Expression: {metric.agg}({metric.expression})",
    ]
    if metric.description:
        lines.append(f"Description: {metric.description}")

    dimensions = [d for d in model.dimensions if d.entity == metric.entity]
    lines += ["", f"Source dimensions (from entity '{metric.entity}'):"]
    lines += [f"  - {_summarize_dimension(d)}" for d in dimensions] if dimensions else ["  (none)"]

    return "\n".join(lines)


_PLURAL = {"entity": "entities", "metric": "metrics"}


def _find(items: list, name: str, kind: str):
    for item in items:
        if item.name == name:
            return item
    known = ", ".join(sorted(item.name for item in items)) or "none"
    raise DescribeError(f"Unknown {kind} '{name}'. Known {_PLURAL[kind]}: {known}")


def _summarize_entity(entity: Entity) -> str:
    summary = entity.description or f"table: {entity.table}"
    return f"{entity.name} — {summary}"


def _summarize_dimension(dimension: Dimension) -> str:
    return f"{dimension.name} ({dimension.type}, column: {dimension.column})"


def _summarize_metric(metric: Metric) -> str:
    summary = f"{metric.name}: {metric.agg}({metric.expression})"
    if metric.description:
        summary += f" — {metric.description}"
    return summary


def _summarize_relationship(relationship: Relationship) -> str:
    label = relationship.name or f"{relationship.source_entity}_to_{relationship.target_entity}"
    return (
        f"{label}: {relationship.source_entity} ({relationship.source_key}) -> "
        f"{relationship.target_entity} ({relationship.target_key}) "
        f"[{relationship.type}, {relationship.join_type}]"
    )
