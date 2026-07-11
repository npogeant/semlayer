from pathlib import Path

import pytest

from semlayer import (
    Dimension,
    Entity,
    Metric,
    Relationship,
    SemanticModel,
    SemanticModelValidationError,
    load_semantic_model,
    validate_semantic_model,
)

EXAMPLE_SCHEMA = (
    Path(__file__).resolve().parent.parent / "docs" / "examples" / "schema-example.yaml"
)

ORDERS = Entity(name="orders", table="analytics.orders", primary_key="order_id")
CUSTOMERS = Entity(name="customers", table="analytics.customers", primary_key="customer_id")


def test_valid_model_from_docs_example_passes():
    model = load_semantic_model(EXAMPLE_SCHEMA)
    validate_semantic_model(model)  # should not raise


def test_valid_hand_built_model_passes():
    model = SemanticModel(
        entities=[ORDERS, CUSTOMERS],
        dimensions=[
            Dimension(name="order_status", entity="orders", type="categorical", column="status")
        ],
        metrics=[
            Metric(name="total_revenue", entity="orders", expression="amount", agg="sum"),
        ],
        relationships=[
            Relationship(
                source_entity="orders",
                target_entity="customers",
                type="many_to_one",
                join_type="inner",
                source_key="customer_id",
                target_key="customer_id",
            )
        ],
    )

    validate_semantic_model(model)  # should not raise


def test_duplicate_entity_name_rejected():
    model = SemanticModel(entities=[ORDERS, ORDERS])

    with pytest.raises(SemanticModelValidationError, match="Duplicate entity name: 'orders'"):
        validate_semantic_model(model)


def test_duplicate_dimension_name_rejected():
    dimension = Dimension(name="order_status", entity="orders", type="categorical", column="status")
    model = SemanticModel(entities=[ORDERS], dimensions=[dimension, dimension])

    with pytest.raises(
        SemanticModelValidationError, match="Duplicate dimension name: 'order_status'"
    ):
        validate_semantic_model(model)


def test_duplicate_metric_name_rejected():
    metric = Metric(name="total_revenue", entity="orders", expression="amount", agg="sum")
    model = SemanticModel(entities=[ORDERS], metrics=[metric, metric])

    with pytest.raises(
        SemanticModelValidationError, match="Duplicate metric name: 'total_revenue'"
    ):
        validate_semantic_model(model)


def test_dimension_referencing_unknown_entity_rejected():
    model = SemanticModel(
        entities=[ORDERS],
        dimensions=[
            Dimension(
                name="order_status", entity="not_an_entity", type="categorical", column="status"
            )
        ],
    )

    with pytest.raises(SemanticModelValidationError, match="unknown entity 'not_an_entity'"):
        validate_semantic_model(model)


def test_metric_referencing_unknown_entity_rejected():
    model = SemanticModel(
        entities=[ORDERS],
        metrics=[
            Metric(name="total_revenue", entity="not_an_entity", expression="amount", agg="sum")
        ],
    )

    with pytest.raises(SemanticModelValidationError, match="unknown entity 'not_an_entity'"):
        validate_semantic_model(model)


def test_relationship_referencing_unknown_source_entity_rejected():
    model = SemanticModel(
        entities=[CUSTOMERS],
        relationships=[
            Relationship(
                source_entity="not_an_entity",
                target_entity="customers",
                type="many_to_one",
                join_type="inner",
                source_key="customer_id",
                target_key="customer_id",
            )
        ],
    )

    with pytest.raises(SemanticModelValidationError, match="unknown source entity 'not_an_entity'"):
        validate_semantic_model(model)


def test_relationship_referencing_unknown_target_entity_rejected():
    model = SemanticModel(
        entities=[ORDERS],
        relationships=[
            Relationship(
                source_entity="orders",
                target_entity="not_an_entity",
                type="many_to_one",
                join_type="inner",
                source_key="customer_id",
                target_key="customer_id",
            )
        ],
    )

    with pytest.raises(SemanticModelValidationError, match="unknown target entity 'not_an_entity'"):
        validate_semantic_model(model)


def test_self_relationship_detected_as_circular():
    model = SemanticModel(
        entities=[ORDERS],
        relationships=[
            Relationship(
                source_entity="orders",
                target_entity="orders",
                type="one_to_many",
                join_type="inner",
                source_key="parent_order_id",
                target_key="order_id",
            )
        ],
    )

    with pytest.raises(SemanticModelValidationError, match="Circular relationship detected"):
        validate_semantic_model(model)


def test_reciprocal_relationship_detected_as_circular():
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

    with pytest.raises(SemanticModelValidationError, match="Circular relationship detected"):
        validate_semantic_model(model)


def test_three_entity_cycle_detected_as_circular():
    payments = Entity(name="payments", table="analytics.payments", primary_key="payment_id")
    model = SemanticModel(
        entities=[ORDERS, CUSTOMERS, payments],
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
                target_entity="payments",
                type="one_to_many",
                join_type="inner",
                source_key="customer_id",
                target_key="customer_id",
            ),
            Relationship(
                source_entity="payments",
                target_entity="orders",
                type="many_to_one",
                join_type="inner",
                source_key="order_id",
                target_key="order_id",
            ),
        ],
    )

    with pytest.raises(SemanticModelValidationError, match="Circular relationship detected"):
        validate_semantic_model(model)
