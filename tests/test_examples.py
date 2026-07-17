from pathlib import Path

from semlayer import (
    MetricRequest,
    load_semantic_model,
    translate_metric_query,
    validate_semantic_model,
)

ECOMMERCE_MODEL = (
    Path(__file__).resolve().parent.parent / "examples" / "ecommerce" / "semantic_model.yaml"
)


def test_ecommerce_example_loads_and_validates():
    model = load_semantic_model(ECOMMERCE_MODEL)

    validate_semantic_model(model)  # should not raise

    assert {e.name for e in model.entities} == {"orders", "customers", "products"}
    assert len(model.dimensions) == 4
    assert len(model.metrics) == 3
    assert len(model.relationships) == 2


def test_ecommerce_example_query_from_the_readme_matches_documented_sql():
    model = load_semantic_model(ECOMMERCE_MODEL)

    query = translate_metric_query(
        model,
        MetricRequest(metric="total_revenue", dimensions=["order_status", "customer_segment"]),
    )

    assert query.sql == (
        "SELECT\n"
        "  orders.status AS order_status,\n"
        "  customers.segment AS customer_segment,\n"
        "  SUM(quantity * unit_price) AS total_revenue\n"
        "FROM analytics.orders AS orders\n"
        "INNER JOIN analytics.customers AS customers "
        "ON orders.customer_id = customers.customer_id\n"
        "GROUP BY orders.status, customers.segment"
    )
    assert query.params == []
