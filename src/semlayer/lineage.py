from dataclasses import dataclass

from semlayer._graph import build_adjacency, find_cyclic_edges
from semlayer.models import Dimension, Entity, Metric, SemanticModel

# Deliberately does not require a validated model. `validate_semantic_model`
# rejects any model with a circular relationship, so a lineage/graph command
# that ran validation first could never actually show one — defeating the
# "circular dependencies surface clearly" requirement. These functions work
# on whatever was loaded, cycles included, so a broken model can still be
# inspected instead of just rejected.


class LineageError(Exception):
    pass


@dataclass
class MetricLineage:
    metric: Metric
    entities: list[Entity]
    dimensions: list[Dimension]


def metric_lineage(model: SemanticModel, name: str) -> MetricLineage:
    """Every entity and dimension a metric depends on, following relationships
    from the metric's own entity outward (breadth-first, cycle-safe)."""
    metric = _find_metric(model, name)
    entities_by_name = {entity.name: entity for entity in model.entities}
    adjacency = build_adjacency([(r.source_entity, r.target_entity) for r in model.relationships])

    visited = [metric.entity]
    queue = [metric.entity]
    while queue:
        current = queue.pop(0)
        for neighbor in adjacency.get(current, []):
            if neighbor not in visited:
                visited.append(neighbor)
                queue.append(neighbor)

    entities = [entities_by_name[name] for name in visited if name in entities_by_name]
    dimensions = [d for d in model.dimensions if d.entity in visited]
    return MetricLineage(metric=metric, entities=entities, dimensions=dimensions)


def format_metric_lineage(lineage: MetricLineage) -> str:
    lines = [
        f"Metric: {lineage.metric.name}",
        "Entities: " + ", ".join(e.name for e in lineage.entities),
        "Dimensions:",
    ]
    if lineage.dimensions:
        lines += [f"  - {d.name} (entity: {d.entity})" for d in lineage.dimensions]
    else:
        lines.append("  (none)")
    return "\n".join(lines)


def export_dependency_graph(model: SemanticModel) -> str:
    """Render the full entity/dimension/metric dependency graph as Graphviz DOT.

    Edges that close a cycle among entity relationships are drawn in red and
    labeled "cycle" so a broken model's problem is visible in the output
    rather than hidden by a raised exception.
    """
    relationship_edges = [(r.source_entity, r.target_entity) for r in model.relationships]
    cyclic_edges = find_cyclic_edges(build_adjacency(relationship_edges))

    lines = ["digraph semantic_model {"]
    for entity in model.entities:
        lines.append(f'  "entity:{entity.name}" [shape=box];')
    for dimension in model.dimensions:
        lines.append(f'  "dimension:{dimension.name}" -> "entity:{dimension.entity}";')
    for metric in model.metrics:
        lines.append(f'  "metric:{metric.name}" -> "entity:{metric.entity}";')
    for source, target in relationship_edges:
        style = ' [color=red, label="cycle"]' if (source, target) in cyclic_edges else ""
        lines.append(f'  "entity:{source}" -> "entity:{target}"{style};')
    lines.append("}")
    return "\n".join(lines)


def _find_metric(model: SemanticModel, name: str) -> Metric:
    for metric in model.metrics:
        if metric.name == name:
            return metric
    known = ", ".join(sorted(m.name for m in model.metrics)) or "none"
    raise LineageError(f"Unknown metric '{name}'. Known metrics: {known}")
