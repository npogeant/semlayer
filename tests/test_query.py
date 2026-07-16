import sqlite3

import pytest

from semlayer import (
    Dimension,
    Entity,
    Filter,
    Metric,
    MetricRequest,
    QueryError,
    Relationship,
    SemanticModel,
    translate_metric_query,
)

ORDERS = Entity(name="orders", table="orders", primary_key="order_id")
CUSTOMERS = Entity(name="customers", table="customers", primary_key="customer_id")
REGIONS = Entity(name="regions", table="regions", primary_key="region_id")

ORDER_STATUS = Dimension(name="order_status", entity="orders", type="categorical", column="status")
ORDER_AMOUNT = Dimension(name="order_amount", entity="orders", type="numeric", column="amount")
CUSTOMER_TIER = Dimension(
    name="customer_tier", entity="customers", type="categorical", column="tier"
)
REGION_NAME = Dimension(name="region_name", entity="regions", type="categorical", column="name")

TOTAL_REVENUE = Metric(name="total_revenue", entity="orders", expression="amount", agg="sum")
ORDER_COUNT = Metric(
    name="order_count", entity="orders", expression="order_id", agg="count_distinct"
)

ORDERS_TO_CUSTOMERS = Relationship(
    source_entity="orders",
    target_entity="customers",
    type="many_to_one",
    join_type="inner",
    source_key="customer_id",
    target_key="customer_id",
)
CUSTOMERS_TO_REGIONS = Relationship(
    source_entity="customers",
    target_entity="regions",
    type="many_to_one",
    join_type="inner",
    source_key="region_id",
    target_key="region_id",
)

MODEL = SemanticModel(
    entities=[ORDERS, CUSTOMERS, REGIONS],
    dimensions=[ORDER_STATUS, ORDER_AMOUNT, CUSTOMER_TIER, REGION_NAME],
    metrics=[TOTAL_REVENUE, ORDER_COUNT],
    relationships=[ORDERS_TO_CUSTOMERS, CUSTOMERS_TO_REGIONS],
)


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE regions (region_id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, region_id INTEGER, tier TEXT);
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY, customer_id INTEGER, status TEXT, amount REAL
        );

        INSERT INTO regions VALUES (1, 'US'), (2, 'EU');
        INSERT INTO customers VALUES (1, 1, 'gold'), (2, 2, 'silver'), (3, 1, 'gold');
        INSERT INTO orders VALUES
            (1, 1, 'shipped', 100),
            (2, 1, 'shipped', 50),
            (3, 2, 'cancelled', 30),
            (4, 3, 'shipped', 200),
            (5, 2, 'shipped', 20);
        """
    )
    yield conn
    conn.close()


def run(db, query):
    return db.execute(query.sql, query.params).fetchall()


def test_metric_with_no_dimensions_produces_a_single_value_query(db):
    query = translate_metric_query(MODEL, MetricRequest(metric="total_revenue"))

    assert "GROUP BY" not in query.sql
    rows = run(db, query)
    assert rows == [(400,)]


def test_metric_grouped_by_a_dimension_on_its_own_entity_needs_no_join(db):
    query = translate_metric_query(
        MODEL, MetricRequest(metric="total_revenue", dimensions=["order_status"])
    )

    assert "JOIN" not in query.sql
    rows = dict(run(db, query))
    assert rows == {"shipped": 370, "cancelled": 30}


def test_metric_grouped_by_a_dimension_on_a_related_entity_joins_automatically(db):
    query = translate_metric_query(
        MODEL, MetricRequest(metric="total_revenue", dimensions=["customer_tier"])
    )

    assert "JOIN customers AS customers ON orders.customer_id = customers.customer_id" in query.sql
    rows = dict(run(db, query))
    assert rows == {"gold": 350, "silver": 50}


def test_metric_grouped_by_a_dimension_two_hops_away_joins_through_the_middle_entity(db):
    query = translate_metric_query(
        MODEL, MetricRequest(metric="total_revenue", dimensions=["region_name"])
    )

    assert query.sql.index("customers") < query.sql.index("regions", query.sql.index("JOIN"))
    rows = dict(run(db, query))
    assert rows == {"US": 350, "EU": 50}


def test_filter_is_applied_in_the_generated_sql(db):
    query = translate_metric_query(
        MODEL,
        MetricRequest(
            metric="total_revenue",
            filters=[Filter(dimension="order_status", operator="=", value="shipped")],
        ),
    )

    assert "WHERE orders.status = ?" in query.sql
    assert query.params == ["shipped"]
    rows = run(db, query)
    assert rows == [(370,)]


def test_in_filter_expands_to_one_placeholder_per_value(db):
    query = translate_metric_query(
        MODEL,
        MetricRequest(
            metric="total_revenue",
            filters=[
                Filter(dimension="order_status", operator="in", value=["shipped", "cancelled"])
            ],
        ),
    )

    assert "IN (?, ?)" in query.sql
    rows = run(db, query)
    assert rows == [(400,)]


def test_grouping_by_multiple_dimensions_across_a_join(db):
    query = translate_metric_query(
        MODEL,
        MetricRequest(metric="total_revenue", dimensions=["order_status", "customer_tier"]),
    )

    rows = {(status, tier): total for status, tier, total in run(db, query)}
    assert rows == {
        ("shipped", "gold"): 350,
        ("shipped", "silver"): 20,
        ("cancelled", "silver"): 30,
    }


def test_multiple_filters_are_combined_with_and(db):
    query = translate_metric_query(
        MODEL,
        MetricRequest(
            metric="total_revenue",
            filters=[
                Filter(dimension="order_status", operator="=", value="shipped"),
                Filter(dimension="customer_tier", operator="=", value="gold"),
            ],
        ),
    )

    assert "WHERE orders.status = ? AND customers.tier = ?" in query.sql
    assert query.params == ["shipped", "gold"]
    rows = run(db, query)
    assert rows == [(350,)]


def test_comparison_operator_filter(db):
    query = translate_metric_query(
        MODEL,
        MetricRequest(
            metric="total_revenue",
            filters=[Filter(dimension="order_amount", operator=">", value=50)],
        ),
    )

    assert "WHERE orders.amount > ?" in query.sql
    rows = run(db, query)
    assert rows == [(300,)]


def test_unsupported_aggregation_raises_clear_error():
    model = SemanticModel(
        entities=[ORDERS],
        metrics=[Metric(name="weird_metric", entity="orders", expression="amount", agg="median")],
    )

    with pytest.raises(QueryError, match="Unsupported aggregation 'median'"):
        translate_metric_query(model, MetricRequest(metric="weird_metric"))


def test_count_distinct_metric_translates_to_count_distinct_sql(db):
    query = translate_metric_query(MODEL, MetricRequest(metric="order_count"))

    assert "COUNT(DISTINCT order_id)" in query.sql
    rows = run(db, query)
    assert rows == [(5,)]


def test_unknown_metric_raises_clear_error():
    with pytest.raises(QueryError, match="Unknown metric 'nope'"):
        translate_metric_query(MODEL, MetricRequest(metric="nope"))


def test_unknown_dimension_raises_clear_error():
    with pytest.raises(QueryError, match="Unknown dimension 'nope'"):
        translate_metric_query(MODEL, MetricRequest(metric="total_revenue", dimensions=["nope"]))


def test_unsupported_filter_operator_raises_clear_error():
    request = MetricRequest(
        metric="total_revenue",
        filters=[Filter(dimension="order_status", operator="LIKE", value="%x%")],
    )
    with pytest.raises(QueryError, match="Unsupported filter operator 'LIKE'"):
        translate_metric_query(MODEL, request)


def test_in_filter_with_non_list_value_raises_clear_error():
    request = MetricRequest(
        metric="total_revenue",
        filters=[Filter(dimension="order_status", operator="in", value="shipped")],
    )
    with pytest.raises(QueryError, match="needs a list value"):
        translate_metric_query(MODEL, request)


def test_no_relationship_path_raises_clear_error():
    isolated = Entity(name="warehouses", table="warehouses", primary_key="warehouse_id")
    isolated_dim = Dimension(
        name="warehouse_zone", entity="warehouses", type="categorical", column="zone"
    )
    model = SemanticModel(
        entities=[*MODEL.entities, isolated],
        dimensions=[*MODEL.dimensions, isolated_dim],
        metrics=MODEL.metrics,
        relationships=MODEL.relationships,
    )

    request = MetricRequest(metric="total_revenue", dimensions=["warehouse_zone"])
    with pytest.raises(
        QueryError, match="No relationship path from entity 'orders' to entity 'warehouses'"
    ):
        translate_metric_query(model, request)
