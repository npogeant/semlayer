from pathlib import Path

from semlayer.cli import main

EXAMPLE_SCHEMA = (
    Path(__file__).resolve().parent.parent / "docs" / "examples" / "schema-example.yaml"
)


def test_describe_entities_exits_zero_and_prints_entities(capsys):
    exit_code = main(["describe", "entities", "--path", str(EXAMPLE_SCHEMA)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "orders —" in out
    assert "customers —" in out


def test_describe_entity_exits_zero_and_prints_detail(capsys):
    exit_code = main(["describe", "entity", "orders", "--path", str(EXAMPLE_SCHEMA)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Entity: orders" in out
    assert "Dimensions:" in out


def test_describe_metrics_exits_zero_and_prints_metrics(capsys):
    exit_code = main(["describe", "metrics", "--path", str(EXAMPLE_SCHEMA)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "total_revenue: sum(amount)" in out


def test_describe_metric_exits_zero_and_prints_detail(capsys):
    exit_code = main(["describe", "metric", "total_revenue", "--path", str(EXAMPLE_SCHEMA)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Metric: total_revenue" in out
    assert "Source dimensions" in out


def test_unknown_entity_exits_one_with_readable_error(capsys):
    exit_code = main(["describe", "entity", "nope", "--path", str(EXAMPLE_SCHEMA)])

    assert exit_code == 1
    err = capsys.readouterr().err
    assert "Error: Unknown entity 'nope'" in err


def test_missing_semantic_model_path_exits_one_with_readable_error(capsys, tmp_path):
    exit_code = main(["describe", "entities", "--path", str(tmp_path / "nope.yaml")])

    assert exit_code == 1
    err = capsys.readouterr().err
    assert "Error:" in err
    assert "does not exist" in err


def test_invalid_semantic_model_exits_one_with_readable_error(capsys, tmp_path):
    bad_model = tmp_path / "model.yaml"
    bad_model.write_text(
        """
        entities:
          - name: orders
            table: analytics.orders
            primary_key: order_id
        dimensions:
          - name: order_status
            entity: not_an_entity
            type: categorical
            column: status
        """
    )

    exit_code = main(["describe", "entities", "--path", str(bad_model)])

    assert exit_code == 1
    err = capsys.readouterr().err
    assert "Error:" in err
    assert "unknown entity 'not_an_entity'" in err


def test_lineage_exits_zero_and_prints_metric_lineage(capsys):
    exit_code = main(["lineage", "total_revenue", "--path", str(EXAMPLE_SCHEMA)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Metric: total_revenue" in out
    assert "Entities: orders, customers" in out


def test_lineage_unknown_metric_exits_one_with_readable_error(capsys):
    exit_code = main(["lineage", "nope", "--path", str(EXAMPLE_SCHEMA)])

    assert exit_code == 1
    err = capsys.readouterr().err
    assert "Error: Unknown metric 'nope'" in err


def test_graph_export_exits_zero_and_prints_dot(capsys):
    exit_code = main(["graph", "export", "--path", str(EXAMPLE_SCHEMA)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert out.startswith("digraph semantic_model {")


def test_graph_export_does_not_reject_a_model_with_a_relationship_cycle(capsys, tmp_path):
    cyclic_model = tmp_path / "model.yaml"
    cyclic_model.write_text(
        """
        entities:
          - name: orders
            table: analytics.orders
            primary_key: order_id
          - name: customers
            table: analytics.customers
            primary_key: customer_id
        relationships:
          - source_entity: orders
            target_entity: customers
            type: many_to_one
            join_type: inner
            source_key: customer_id
            target_key: customer_id
          - source_entity: customers
            target_entity: orders
            type: one_to_many
            join_type: inner
            source_key: customer_id
            target_key: customer_id
        """
    )

    exit_code = main(["graph", "export", "--path", str(cyclic_model)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert 'color=red, label="cycle"' in out
