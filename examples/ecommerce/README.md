# Example: ecommerce semantic model

A small, realistic semantic model over an orders/customers/products schema —
3 entities, 4 dimensions, 3 metrics, and 2 relationships — used as the
starting point referenced from the main [README](../../README.md).

`semantic_model.yaml` follows the schema defined in
[`docs/schema.md`](../../docs/schema.md).

## Try it with the CLI

From the repo root, with the package installed (`pip install -e ".[dev]"`):

```bash
# List every entity
semlayer describe entities --path examples/ecommerce/semantic_model.yaml
```
```
orders — One row per order line (an order can have multiple lines).
customers — One row per customer.
products — One row per product in the catalog.
```

```bash
# Look at one entity in detail — its dimensions and relationships
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

```bash
# List every metric
semlayer describe metrics --path examples/ecommerce/semantic_model.yaml

# Look at one metric in detail — its definition and the dimensions you can group it by
semlayer describe metric total_revenue --path examples/ecommerce/semantic_model.yaml

# See every entity and dimension a metric depends on, following relationships
semlayer lineage total_revenue --path examples/ecommerce/semantic_model.yaml

# Export the full dependency graph as Graphviz DOT
semlayer graph export --path examples/ecommerce/semantic_model.yaml
```

## Querying a metric grouped by a dimension

Translating a metric + dimension selection into SQL isn't wired into the CLI
(see the query translator, `src/semlayer/query.py`) — it's a library call:

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

`customer_segment` lives on `customers`, not `orders` — the join is resolved
automatically from the `orders_to_customers` relationship. `query.params` is
`[]` here since there's no filter; run `query.sql` with `query.params`
through any DB-API cursor (e.g. `cursor.execute(query.sql, query.params)`)
against a warehouse with matching tables to get real rows back.
