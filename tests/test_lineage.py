from pathlib import Path

import pytest

from semlayer import (
    Dimension,
    Entity,
    LineageError,
    Metric,
    Relationship,
    SemanticModel,
    export_dependency_graph,
    format_metric_lineage,
    load_semantic_model,
    metric_lineage,
)

EXAMPLE_SCHEMA = (
    Path(__file__).resolve().parent.parent / "docs" / "examples" / "schema-example.yaml"
)

ORDERS = Entity(name="orders", table="analytics.orders", primary_key="order_id")
CUSTOMERS = Entity(name="customers", table="analytics.customers", primary_key="customer_id")
REGIONS = Entity(name="regions", table="analytics.regions", primary_key="region_id")


def test_metric_lineage_from_docs_example():
    model = load_semantic_model(EXAMPLE_SCHEMA)

    lineage = metric_lineage(model, "total_revenue")

    assert [e.name for e in lineage.entities] == ["orders", "customers"]
    assert {d.name for d in lineage.dimensions} == {"order_status", "order_date"}


def test_metric_lineage_follows_relationships_multiple_hops():
    model = SemanticModel(
        entities=[ORDERS, CUSTOMERS, REGIONS],
        dimensions=[
            Dimension(name="order_status", entity="orders", type="categorical", column="status"),
            Dimension(name="customer_tier", entity="customers", type="categorical", column="tier"),
            Dimension(name="region_name", entity="regions", type="categorical", column="name"),
        ],
        metrics=[Metric(name="total_revenue", entity="orders", expression="amount", agg="sum")],
        relationships=[
            Relationship(
                source_entity="orders",
                target_entity="customers",
                type="many_to_one",
                join_type="inner",
                source_key="customer_id",
                target_key="customer_id",
            ),
            Relationship(
                source_entity="customers",
                target_entity="regions",
                type="many_to_one",
                join_type="inner",
                source_key="region_id",
                target_key="region_id",
            ),
        ],
    )

    lineage = metric_lineage(model, "total_revenue")

    assert [e.name for e in lineage.entities] == ["orders", "customers", "regions"]
    assert {d.name for d in lineage.dimensions} == {"order_status", "customer_tier", "region_name"}


def test_metric_lineage_unrelated_entity_not_included():
    model = SemanticModel(
        entities=[ORDERS, REGIONS],
        dimensions=[
            Dimension(name="region_name", entity="regions", type="categorical", column="name")
        ],
        metrics=[Metric(name="total_revenue", entity="orders", expression="amount", agg="sum")],
    )

    lineage = metric_lineage(model, "total_revenue")

    assert [e.name for e in lineage.entities] == ["orders"]
    assert lineage.dimensions == []


def test_metric_lineage_unknown_metric_raises_clear_error():
    model = SemanticModel(entities=[ORDERS])

    with pytest.raises(LineageError, match="Unknown metric 'nope'. Known metrics: none"):
        metric_lineage(model, "nope")


def test_metric_lineage_safe_against_relationship_cycles():
    # A cyclic model would be rejected by validate_semantic_model, but
    # lineage is meant to work on unvalidated models too, so it must not
    # infinite-loop when the relationship graph has a cycle.
    model = SemanticModel(
        entities=[ORDERS, CUSTOMERS],
        metrics=[Metric(name="total_revenue", entity="orders", expression="amount", agg="sum")],
        relationships=[
            Relationship(
                source_entity="orders",
                target_entity="customers",
                type="many_to_one",
                join_type="inner",
                source_key="customer_id",
                target_key="customer_id",
            ),
            Relationship(
                source_entity="customers",
                target_entity="orders",
                type="one_to_many",
                join_type="inner",
                source_key="customer_id",
                target_key="customer_id",
            ),
        ],
    )

    lineage = metric_lineage(model, "total_revenue")

    assert [e.name for e in lineage.entities] == ["orders", "customers"]


def test_format_metric_lineage_with_no_dimensions_says_none():
    model = SemanticModel(
        entities=[ORDERS],
        metrics=[Metric(name="total_revenue", entity="orders", expression="amount", agg="sum")],
    )

    output = format_metric_lineage(metric_lineage(model, "total_revenue"))

    assert "  (none)" in output


def test_format_metric_lineage_reports_entities_and_dimensions():
    model = load_semantic_model(EXAMPLE_SCHEMA)
    lineage = metric_lineage(model, "total_revenue")

    output = format_metric_lineage(lineage)

    assert "Metric: total_revenue" in output
    assert "Entities: orders, customers" in output
    assert "order_status (entity: orders)" in output


def test_export_dependency_graph_contains_every_node_and_edge():
    model = load_semantic_model(EXAMPLE_SCHEMA)

    dot = export_dependency_graph(model)

    assert dot.startswith("digraph semantic_model {")
    assert dot.endswith("}")
    assert '"entity:orders" [shape=box];' in dot
    assert '"dimension:order_status" -> "entity:orders";' in dot
    assert '"metric:total_revenue" -> "entity:orders";' in dot
    assert '"entity:orders" -> "entity:customers";' in dot


def test_export_dependency_graph_marks_cyclic_edges():
    model = SemanticModel(
        entities=[ORDERS, CUSTOMERS],
        relationships=[
            Relationship(
                source_entity="orders",
                target_entity="customers",
                type="many_to_one",
                join_type="inner",
                source_key="customer_id",
                target_key="customer_id",
            ),
            Relationship(
                source_entity="customers",
                target_entity="orders",
                type="one_to_many",
                join_type="inner",
                source_key="customer_id",
                target_key="customer_id",
            ),
        ],
    )

    dot = export_dependency_graph(model)

    assert 'color=red, label="cycle"' in dot
