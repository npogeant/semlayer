# Semantic model schema

This document defines the YAML schema used to describe a semantic model: the
entities, dimensions, metrics, and relationships that make up the data model.
It is the reference for anyone hand-writing a semantic model file, and the
target that the loader (see issue #3) will eventually parse into typed
Python objects.

A semantic model file is a YAML mapping with up to four top-level keys, each
a list:

```yaml
entities: [...]
dimensions: [...]
metrics: [...]
relationships: [...]
```

All four are flat, top-level lists rather than nested under one another.
See [ADR 0001](decisions/0001-semantic-model-schema.md) for why.

## Entity

An entity represents a table or view in the underlying data — the thing
dimensions and metrics are defined against.

| Field         | Type   | Required | Description                                                              |
|---------------|--------|----------|----------------------------------------------------------------------------|
| `name`        | string | yes      | Unique identifier for the entity. `snake_case`, referenced by dimensions, metrics, and relationships. |
| `description` | string | no       | Human-readable explanation of what a row represents.                     |
| `table`       | string | yes      | Fully-qualified reference to the underlying table or view (e.g. `analytics.orders`). |
| `primary_key` | string | yes      | Column that uniquely identifies each row. Used as the default join anchor for relationships. |

```yaml
entities:
  - name: orders
    description: One row per customer order.
    table: analytics.orders
    primary_key: order_id
```

## Dimension

A dimension is an attribute of an entity that can be used to group, filter,
or slice metrics.

| Field         | Type   | Required | Description                                                              |
|---------------|--------|----------|----------------------------------------------------------------------------|
| `name`        | string | yes      | Unique identifier for the dimension.                                     |
| `entity`      | string | yes      | Name of the entity this dimension belongs to.                            |
| `type`        | string | yes      | One of `categorical`, `time`, `boolean`, `numeric` (see below).          |
| `column`      | string | yes      | Source column or expression the dimension is read from.                  |
| `description` | string | no       | Human-readable explanation.                                              |

Supported `type` values:

- `categorical` — a discrete label (e.g. status, region)
- `time` — a date or timestamp, usable for time-based grouping
- `boolean` — a true/false flag
- `numeric` — a number that is grouped on, not aggregated (e.g. a rating)

```yaml
dimensions:
  - name: order_status
    entity: orders
    type: categorical
    column: status

  - name: order_date
    entity: orders
    type: time
    column: created_at
```

## Metric

A metric is a numeric measure computed by aggregating a column or
expression on an entity.

| Field         | Type   | Required | Description                                                              |
|---------------|--------|----------|----------------------------------------------------------------------------|
| `name`        | string | yes      | Unique identifier for the metric.                                        |
| `entity`      | string | yes      | Name of the entity the metric is computed against.                       |
| `expression`  | string | yes      | Column or SQL expression the aggregation is applied to.                  |
| `agg`         | string | yes      | Aggregation function: `sum`, `count`, `count_distinct`, `avg`, `min`, `max`. |
| `description` | string | no       | Human-readable explanation.                                              |

```yaml
metrics:
  - name: total_revenue
    entity: orders
    description: Sum of order amounts.
    expression: amount
    agg: sum

  - name: order_count
    entity: orders
    expression: order_id
    agg: count_distinct
```

## Relationship

A relationship describes how two entities join together.

| Field         | Type   | Required | Description                                                              |
|---------------|--------|----------|----------------------------------------------------------------------------|
| `name`        | string | no       | Optional identifier for the relationship, useful in error messages.      |
| `source_entity` | string | yes    | Name of the entity the join starts from.                                 |
| `target_entity` | string | yes    | Name of the entity being joined to.                                      |
| `type`        | string | yes      | Cardinality: `one_to_one`, `one_to_many`, `many_to_one`, `many_to_many`.  |
| `join_type`   | string | yes      | SQL join type: `inner`, `left`, `right`, `full`.                         |
| `source_key`  | string | yes      | Column on `source_entity` used in the join condition.                    |
| `target_key`  | string | yes      | Column on `target_entity` used in the join condition.                    |

```yaml
relationships:
  - name: orders_to_customers
    source_entity: orders
    target_entity: customers
    type: many_to_one
    join_type: inner
    source_key: customer_id
    target_key: customer_id
```

## Full example

See [`docs/examples/schema-example.yaml`](examples/schema-example.yaml) for a
minimal file exercising every construct above. A fuller, realistic example
project is tracked separately (issue #9).

## Naming conventions

- All `name` fields use `snake_case` and must be unique within their kind
  (two entities can't share a name, two metrics can't share a name, etc.).
- Names are the join key between sections: dimensions and metrics reference
  their `entity` by name, relationships reference `source_entity` /
  `target_entity` by name. Validating that these references resolve is the
  job of the loader and validator (issues #3 and #4), not this schema.
