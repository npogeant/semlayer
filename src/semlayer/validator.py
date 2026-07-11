from semlayer.models import Relationship, SemanticModel


class SemanticModelValidationError(Exception):
    pass


def validate_semantic_model(model: SemanticModel) -> None:
    """Check that a loaded semantic model is internally consistent.

    Raises `SemanticModelValidationError` on the first problem found:
    duplicate entity/dimension/metric names, a dimension/metric/relationship
    referencing an entity that doesn't exist, or a circular chain of
    relationships. Does not touch a database — everything is checked
    against the model's own declarations.
    """
    _check_unique_names(model.entities, kind="entity")
    _check_unique_names(model.dimensions, kind="dimension")
    _check_unique_names(model.metrics, kind="metric")

    entity_names = {entity.name for entity in model.entities}

    for dimension in model.dimensions:
        if dimension.entity not in entity_names:
            raise SemanticModelValidationError(
                f"Dimension '{dimension.name}' references unknown entity '{dimension.entity}'"
            )

    for metric in model.metrics:
        if metric.entity not in entity_names:
            raise SemanticModelValidationError(
                f"Metric '{metric.name}' references unknown entity '{metric.entity}'"
            )

    for relationship in model.relationships:
        label = relationship.name or f"{relationship.source_entity}->{relationship.target_entity}"
        if relationship.source_entity not in entity_names:
            raise SemanticModelValidationError(
                f"Relationship '{label}' references unknown source entity "
                f"'{relationship.source_entity}'"
            )
        if relationship.target_entity not in entity_names:
            raise SemanticModelValidationError(
                f"Relationship '{label}' references unknown target entity "
                f"'{relationship.target_entity}'"
            )

    _check_no_circular_relationships(model.relationships)


def _check_unique_names(items, kind: str) -> None:
    seen = set()
    for item in items:
        if item.name in seen:
            raise SemanticModelValidationError(f"Duplicate {kind} name: '{item.name}'")
        seen.add(item.name)


def _check_no_circular_relationships(relationships: list[Relationship]) -> None:
    # Relationships are directed edges (source_entity -> target_entity). A
    # relationship only needs to be declared once per direction of travel,
    # so a cycle back to an entity already on the current path — including
    # a self-relationship or two relationships declared in opposite
    # directions between the same pair of entities — is treated as circular.
    graph: dict[str, list[str]] = {}
    for relationship in relationships:
        graph.setdefault(relationship.source_entity, []).append(relationship.target_entity)
        graph.setdefault(relationship.target_entity, [])

    WHITE, GRAY, BLACK = 0, 1, 2
    color = dict.fromkeys(graph, WHITE)
    path: list[str] = []

    def visit(node: str) -> None:
        color[node] = GRAY
        path.append(node)
        for neighbor in graph[node]:
            if color[neighbor] == GRAY:
                cycle = path[path.index(neighbor) :] + [neighbor]
                raise SemanticModelValidationError(
                    f"Circular relationship detected: {' -> '.join(cycle)}"
                )
            if color[neighbor] == WHITE:
                visit(neighbor)
        path.pop()
        color[node] = BLACK

    for node in list(graph):
        if color[node] == WHITE:
            visit(node)
