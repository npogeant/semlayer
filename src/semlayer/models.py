from dataclasses import dataclass, field


@dataclass
class Entity:
    name: str
    table: str
    primary_key: str
    description: str | None = None


@dataclass
class Dimension:
    name: str
    entity: str
    type: str
    column: str
    description: str | None = None


@dataclass
class Metric:
    name: str
    entity: str
    expression: str
    agg: str
    description: str | None = None


@dataclass
class Relationship:
    source_entity: str
    target_entity: str
    type: str
    join_type: str
    source_key: str
    target_key: str
    name: str | None = None


@dataclass
class SemanticModel:
    entities: list[Entity] = field(default_factory=list)
    dimensions: list[Dimension] = field(default_factory=list)
    metrics: list[Metric] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
