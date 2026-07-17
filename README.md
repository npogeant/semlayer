# semlayer

A declarative semantic layer for defining entities, dimensions, metrics, and
relationships over your data — as version-controlled YAML instead of logic
duplicated across dashboards, notebooks, and one-off queries. Define what an
"order" or "revenue" means once; describe it, trace how it's built, and
translate it into SQL from the same source of truth.

## Installation

Requires Python 3.10+. There's no published package yet, so install from a
clone:

```bash
git clone https://github.com/npogeant/semlayer.git
cd semlayer
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quickstart

The repo ships a small example model at
[`examples/ecommerce/semantic_model.yaml`](examples/ecommerce/semantic_model.yaml).
Point the CLI at it to see the whole workflow:

```bash
semlayer describe entities --path examples/ecommerce/semantic_model.yaml
```
```
orders — One row per order line (an order can have multiple lines).
customers — One row per customer.
products — One row per product in the catalog.
```

See [Example model](#example-model) below for the full walkthrough.

## The semantic model schema

A semantic model is a YAML file (or directory of them — the loader merges
multiple files into one model) with up to four top-level lists: `entities`,
`dimensions`, `metrics`, `relationships`. An entity maps to a table; a
dimension is an attribute you can group or filter by; a metric is an
aggregation; a relationship says how two entities join.

```yaml
entities:
  - name: orders
    description: One row per customer order.
    table: analytics.orders
    primary_key: order_id

dimensions:
  - name: order_status
    entity: orders
    type: categorical
    column: status

metrics:
  - name: total_revenue
    entity: orders
    expression: amount
    agg: sum

relationships:
  - name: orders_to_customers
    source_entity: orders
    target_entity: customers
    type: many_to_one
    join_type: inner
    source_key: customer_id
    target_key: customer_id
```

Full field-by-field reference, including every dimension type and
aggregation: [`docs/schema.md`](docs/schema.md). Once loaded
(`load_semantic_model`), a model can be checked for internal consistency
with `validate_semantic_model` — duplicate names, dangling references, and
circular relationships are all rejected with a specific error.

## CLI reference

Every command takes `--path <file-or-directory>` pointing at a semantic
model. `describe` and `lineage`/`graph` commands are shown here against the
example model.

**`describe entities`** — list every entity with a short summary.

```bash
semlayer describe entities --path examples/ecommerce/semantic_model.yaml
```
```
orders — One row per order line (an order can have multiple lines).
customers — One row per customer.
products — One row per product in the catalog.
```

**`describe entity <name>`** — one entity's table, primary key, dimensions,
and relationships.

```bash
semlayer describe entity orders --path examples/ecommerce/semantic_model.yaml
```
```
Entity: orders
Table: analytics.orders
Primary key: order_id
Description: One row per order line (an order can have multiple lines).

Dimensions:
  - order_status (categorical, column: status)
  - order_date (time, column: created_at)

Relationships:
  - orders_to_customers: orders (customer_id) -> customers (customer_id) [many_to_one, inner]
  - orders_to_products: orders (product_id) -> products (product_id) [many_to_one, inner]
```

**`describe metrics`** — list every metric with its aggregation and
expression.

```bash
semlayer describe metrics --path examples/ecommerce/semantic_model.yaml
```
```
total_revenue: sum(quantity * unit_price) — Total revenue across all order lines.
order_count: count_distinct(order_id) — Number of distinct orders.
avg_order_value: avg(quantity * unit_price) — Average revenue per order line.
```

**`describe metric <name>`** — one metric's full definition plus the
dimensions available on its entity.

```bash
semlayer describe metric total_revenue --path examples/ecommerce/semantic_model.yaml
```
```
Metric: total_revenue
Entity: orders
Expression: sum(quantity * unit_price)
Description: Total revenue across all order lines.

Source dimensions (from entity 'orders'):
  - order_status (categorical, column: status)
  - order_date (time, column: created_at)
```

**`lineage <metric>`** — every entity and dimension a metric depends on,
following relationships outward (multi-hop, not just its own entity).

```bash
semlayer lineage total_revenue --path examples/ecommerce/semantic_model.yaml
```
```
Metric: total_revenue
Entities: orders, customers, products
Dimensions:
  - order_status (entity: orders)
  - order_date (entity: orders)
  - customer_segment (entity: customers)
  - product_category (entity: products)
```

**`graph export`** — the full entity/dimension/metric dependency graph as
Graphviz DOT, pipeable into `dot` to render an image.

```bash
semlayer graph export --path examples/ecommerce/semantic_model.yaml
```
```
digraph semantic_model {
  "entity:orders" [shape=box];
  "entity:customers" [shape=box];
  "entity:products" [shape=box];
  "dimension:order_status" -> "entity:orders";
  "dimension:order_date" -> "entity:orders";
  "dimension:customer_segment" -> "entity:customers";
  "dimension:product_category" -> "entity:products";
  "metric:total_revenue" -> "entity:orders";
  "metric:order_count" -> "entity:orders";
  "metric:avg_order_value" -> "entity:orders";
  "entity:orders" -> "entity:customers";
  "entity:orders" -> "entity:products";
}
```

`describe` commands validate the model first, so a broken model fails with a
clear error instead of confusing output. `lineage`/`graph export`
deliberately don't — a circular relationship is still visible in the graph
(marked in red) rather than only ever producing a validation error.

## Querying metrics (SQL translation)

Turning a metric + dimension selection into runnable SQL isn't wired into
the CLI yet — it's a library call, `translate_metric_query`. Joins are
resolved automatically from the model's relationships, including multi-hop
paths:

```python
from semlayer import MetricRequest, load_semantic_model, translate_metric_query

model = load_semantic_model("examples/ecommerce/semantic_model.yaml")

query = translate_metric_query(
    model,
    MetricRequest(metric="total_revenue", dimensions=["order_status", "customer_segment"]),
)

print(query.sql)
```
```sql
SELECT
  orders.status AS order_status,
  customers.segment AS customer_segment,
  SUM(quantity * unit_price) AS total_revenue
FROM analytics.orders AS orders
INNER JOIN analytics.customers AS customers ON orders.customer_id = customers.customer_id
GROUP BY orders.status, customers.segment
```

`customer_segment` lives on `customers`, not `orders` — the join to
`customers` was resolved automatically from the `orders_to_customers`
relationship. Filter values come back as `?` placeholders in `query.params`,
not inlined into the SQL string, so run the result through a DB-API cursor
(`cursor.execute(query.sql, query.params)`) rather than executing the string
directly.

## Example model

[`examples/ecommerce`](examples/ecommerce) has the full model used above
(3 entities, 4 dimensions, 3 metrics, 2 relationships) plus a walkthrough of
every CLI command and the query example, with real captured output.

## Development

```bash
# Install with dev dependencies (pytest, ruff)
pip install -e ".[dev]"

# Lint and format
ruff check .
ruff format .

# Run tests
pytest
```
