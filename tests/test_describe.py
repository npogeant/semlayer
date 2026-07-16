from pathlib import Path

import pytest

from semlayer import (
    DescribeError,
    Entity,
    SemanticModel,
    describe_entities,
    describe_entity,
    describe_metric,
    describe_metrics,
    load_semantic_model,
)

EXAMPLE_SCHEMA = (
    Path(__file__).resolve().parent.parent / "docs" / "examples" / "schema-example.yaml"
)


@pytest.fixture
def model():
    return load_semantic_model(EXAMPLE_SCHEMA)


def test_describe_entities_lists_every_entity_with_a_summary(model):
    output = describe_entities(model)

    assert "orders — One row per customer order." in output
    assert "customers — One row per customer." in output


def test_describe_entity_shows_dimensions_and_relationships(model):
    output = describe_entity(model, "orders")

    assert "Entity: orders" in output
    assert "Table: analytics.orders" in output
    assert "Primary key: order_id" in output
    assert "Dimensions:" in output
    assert "order_status (categorical, column: status)" in output
    assert "order_date (time, column: created_at)" in output
    assert "Relationships:" in output
    assert "orders (customer_id) -> customers (customer_id)" in output


def test_describe_entities_with_no_entities_says_none_defined():
    assert describe_entities(SemanticModel()) == "No entities defined."


def test_describe_metrics_with_no_metrics_says_none_defined():
    assert describe_metrics(SemanticModel()) == "No metrics defined."


def test_describe_entity_with_no_dimensions_or_relationships_says_none():
    model = SemanticModel(entities=[Entity(name="lonely", table="t", primary_key="id")])

    output = describe_entity(model, "lonely")

    assert output.count("(none)") == 2


def test_describe_entity_unknown_name_raises_clear_error(model):
    with pytest.raises(
        DescribeError, match="Unknown entity 'nope'. Known entities: customers, orders"
    ):
        describe_entity(model, "nope")


def test_describe_metrics_lists_every_metric_with_its_expression(model):
    output = describe_metrics(model)

    assert "total_revenue: sum(amount) — Sum of order amounts." in output
    assert "order_count: count_distinct(order_id)" in output


def test_describe_metric_shows_full_definition_and_source_dimensions(model):
    output = describe_metric(model, "total_revenue")

    assert "Metric: total_revenue" in output
    assert "Entity: orders" in output
    assert "Expression: sum(amount)" in output
    assert "Description: Sum of order amounts." in output
    assert "Source dimensions (from entity 'orders'):" in output
    assert "order_status (categorical, column: status)" in output


def test_describe_metric_unknown_name_raises_clear_error(model):
    with pytest.raises(
        DescribeError, match="Unknown metric 'nope'. Known metrics: order_count, total_revenue"
    ):
        describe_metric(model, "nope")
