from dataclasses import dataclass, field
from typing import Any

from semlayer.models import Dimension, Metric, Relationship, SemanticModel

_PLURAL = {"metric": "metrics", "dimension": "dimensions"}

_OPERATORS = {"=", "!=", ">", ">=", "<", "<=", "in"}

# COUNT DISTINCT isn't spelled COUNT_DISTINCT(x) in SQL, so each agg needs its
# own template rather than a plain f"{agg.upper()}({expr})".
_AGG_SQL = {
    "sum": "SUM({expr})",
    "count": "COUNT({expr})",
    "count_distinct": "COUNT(DISTINCT {expr})",
    "avg": "AVG({expr})",
    "min": "MIN({expr})",
    "max": "MAX({expr})",
}


class QueryError(Exception):
    pass


@dataclass
class Filter:
    dimension: str
    operator: str
    value: Any


@dataclass
class MetricRequest:
    metric: str
    dimensions: list[str] = field(default_factory=list)
    filters: list[Filter] = field(default_factory=list)


@dataclass
class GeneratedQuery:
    sql: str
    params: list[Any]


def translate_metric_query(model: SemanticModel, request: MetricRequest) -> GeneratedQuery:
    """Translate a metric + dimension/filter selection into a runnable SQL query.

    Joins are resolved automatically by walking the model's relationships
    (as directed `source_entity -> target_entity` edges, same direction used
    by validation and lineage) from the metric's own entity out to whichever
    entities own the requested dimensions. Filter values are passed back as
    `?` placeholders + params rather than interpolated into the SQL string,
    so callers execute this safely against a DB-API cursor.

    A metric's `expression` is emitted as-is, unqualified, since it may be an
    arbitrary SQL fragment (not just a bare column) that can't be reliably
    rewritten. If it references a column name that also exists on a joined
    entity, qualify it yourself in the YAML (e.g. `orders.amount`).
    """
    metric = _find(model.metrics, request.metric, kind="metric")
    group_dimensions = [
        _find(model.dimensions, name, kind="dimension") for name in request.dimensions
    ]
    filter_dimensions = []
    for f in request.filters:
        if f.operator not in _OPERATORS:
            raise QueryError(
                f"Unsupported filter operator '{f.operator}'. "
                f"Supported operators: {', '.join(sorted(_OPERATORS))}"
            )
        if f.operator == "in" and not isinstance(f.value, list | tuple):
            raise QueryError(f"Filter on '{f.dimension}' with operator 'in' needs a list value")
        filter_dimensions.append(_find(model.dimensions, f.dimension, kind="dimension"))

    entities_by_name = {entity.name: entity for entity in model.entities}
    needed_entities = {d.entity for d in group_dimensions + filter_dimensions}
    joins = _resolve_joins(model, base=metric.entity, needed=needed_entities)

    base_entity = entities_by_name[metric.entity]
    select_parts = [f"{d.entity}.{d.column} AS {d.name}" for d in group_dimensions]
    select_parts.append(f"{_render_aggregation(metric)} AS {metric.name}")

    sql_lines = [
        "SELECT",
        "  " + ",\n  ".join(select_parts),
        f"FROM {base_entity.table} AS {base_entity.name}",
    ]
    for source, target, relationship in joins:
        target_entity = entities_by_name[target]
        sql_lines.append(
            f"{relationship.join_type.upper()} JOIN {target_entity.table} AS {target_entity.name} "
            f"ON {source}.{relationship.source_key} = {target}.{relationship.target_key}"
        )

    params: list[Any] = []
    conditions = []
    for f, dimension in zip(request.filters, filter_dimensions, strict=True):
        column = f"{dimension.entity}.{dimension.column}"
        if f.operator == "in":
            conditions.append(f"{column} IN ({', '.join('?' for _ in f.value)})")
            params.extend(f.value)
        else:
            conditions.append(f"{column} {f.operator} ?")
            params.append(f.value)
    if conditions:
        sql_lines.append("WHERE " + " AND ".join(conditions))

    if group_dimensions:
        group_by = ", ".join(f"{d.entity}.{d.column}" for d in group_dimensions)
        sql_lines.append(f"GROUP BY {group_by}")

    return GeneratedQuery(sql="\n".join(sql_lines), params=params)


def _render_aggregation(metric: Metric) -> str:
    try:
        template = _AGG_SQL[metric.agg]
    except KeyError:
        raise QueryError(
            f"Unsupported aggregation '{metric.agg}' for metric '{metric.name}'. "
            f"Supported: {', '.join(sorted(_AGG_SQL))}"
        ) from None
    return template.format(expr=metric.expression)


def _resolve_joins(
    model: SemanticModel, base: str, needed: set[str]
) -> list[tuple[str, str, Relationship]]:
    relationship_by_edge = {(r.source_entity, r.target_entity): r for r in model.relationships}
    adjacency: dict[str, list[str]] = {}
    for r in model.relationships:
        adjacency.setdefault(r.source_entity, []).append(r.target_entity)

    parent: dict[str, str | None] = {base: None}
    discovery_order = [base]
    queue = [base]
    while queue:
        current = queue.pop(0)
        for neighbor in adjacency.get(current, []):
            if neighbor not in parent:
                parent[neighbor] = current
                discovery_order.append(neighbor)
                queue.append(neighbor)

    join_edges: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for entity_name in needed:
        if entity_name == base:
            continue
        if entity_name not in parent:
            raise QueryError(f"No relationship path from entity '{base}' to entity '{entity_name}'")
        node = entity_name
        path: list[tuple[str, str]] = []
        while parent[node] is not None:
            path.append((parent[node], node))
            node = parent[node]
        for edge in reversed(path):
            if edge not in seen:
                seen.add(edge)
                join_edges.append(edge)

    # Ordered by BFS discovery so a join's source entity is always already
    # in the FROM clause or an earlier JOIN by the time it's emitted.
    order_index = {name: i for i, name in enumerate(discovery_order)}
    join_edges.sort(key=lambda edge: order_index[edge[1]])

    return [
        (source, target, relationship_by_edge[(source, target)]) for source, target in join_edges
    ]


def _find(items: list[Dimension] | list[Metric], name: str, kind: str):
    for item in items:
        if item.name == name:
            return item
    known = ", ".join(sorted(item.name for item in items)) or "none"
    raise QueryError(f"Unknown {kind} '{name}'. Known {_PLURAL[kind]}: {known}")
