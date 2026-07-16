from pathlib import Path

import pytest

from semlayer import SemanticModelLoadError, load_semantic_model

EXAMPLE_SCHEMA = (
    Path(__file__).resolve().parent.parent / "docs" / "examples" / "schema-example.yaml"
)

ENTITY_YAML = """
entities:
  - name: orders
    table: analytics.orders
    primary_key: order_id
"""

DIMENSION_YAML = """
dimensions:
  - name: order_status
    entity: orders
    type: categorical
    column: status
"""


def test_loads_the_docs_schema_example():
    model = load_semantic_model(EXAMPLE_SCHEMA)

    assert [e.name for e in model.entities] == ["orders", "customers"]
    assert [d.name for d in model.dimensions] == ["order_status", "order_date"]
    assert [m.name for m in model.metrics] == ["total_revenue", "order_count"]
    assert [r.name for r in model.relationships] == ["orders_to_customers"]

    orders = model.entities[0]
    assert orders.table == "analytics.orders"
    assert orders.primary_key == "order_id"


def test_merges_a_semantic_model_split_across_multiple_files(tmp_path):
    (tmp_path / "entities.yaml").write_text(ENTITY_YAML)
    (tmp_path / "dimensions.yaml").write_text(DIMENSION_YAML)

    model = load_semantic_model(tmp_path)

    assert [e.name for e in model.entities] == ["orders"]
    assert [d.name for d in model.dimensions] == ["order_status"]
    assert model.metrics == []
    assert model.relationships == []


def test_missing_path_raises_a_clear_error(tmp_path):
    with pytest.raises(SemanticModelLoadError, match="does not exist"):
        load_semantic_model(tmp_path / "nope.yaml")


def test_empty_directory_raises_a_clear_error(tmp_path):
    with pytest.raises(SemanticModelLoadError, match="No YAML files found"):
        load_semantic_model(tmp_path)


def test_malformed_yaml_raises_a_clear_error(tmp_path):
    bad_file = tmp_path / "broken.yaml"
    bad_file.write_text("entities: [name: orders, table: analytics.orders\n")

    with pytest.raises(SemanticModelLoadError, match="Failed to parse YAML"):
        load_semantic_model(bad_file)


def test_missing_required_field_raises_a_clear_error(tmp_path):
    yaml_file = tmp_path / "model.yaml"
    yaml_file.write_text(
        """
        entities:
          - name: orders
            table: analytics.orders
        """
    )

    with pytest.raises(SemanticModelLoadError, match="missing required field.*primary_key"):
        load_semantic_model(yaml_file)


def test_unknown_field_raises_a_clear_error(tmp_path):
    yaml_file = tmp_path / "model.yaml"
    yaml_file.write_text(
        """
        entities:
          - name: orders
            table: analytics.orders
            primary_key: order_id
            not_a_real_field: oops
        """
    )

    with pytest.raises(SemanticModelLoadError, match="unknown field.*not_a_real_field"):
        load_semantic_model(yaml_file)


def test_unknown_top_level_section_raises_a_clear_error(tmp_path):
    yaml_file = tmp_path / "model.yaml"
    yaml_file.write_text("widgets:\n  - name: not_a_section\n")

    with pytest.raises(SemanticModelLoadError, match="unknown top-level section.*widgets"):
        load_semantic_model(yaml_file)


def test_non_mapping_top_level_raises_a_clear_error(tmp_path):
    yaml_file = tmp_path / "model.yaml"
    yaml_file.write_text("- just\n- a\n- list\n")

    with pytest.raises(SemanticModelLoadError, match="must contain a mapping at the top level"):
        load_semantic_model(yaml_file)


def test_non_list_section_raises_a_clear_error(tmp_path):
    yaml_file = tmp_path / "model.yaml"
    yaml_file.write_text("entities: not_a_list\n")

    with pytest.raises(SemanticModelLoadError, match="'entities'.*must be a list"):
        load_semantic_model(yaml_file)


def test_non_mapping_item_raises_a_clear_error(tmp_path):
    yaml_file = tmp_path / "model.yaml"
    yaml_file.write_text("entities:\n  - just_a_string\n")

    with pytest.raises(SemanticModelLoadError, match="Entity in .* must be a mapping"):
        load_semantic_model(yaml_file)


def test_empty_yaml_file_loads_as_an_empty_model(tmp_path):
    yaml_file = tmp_path / "model.yaml"
    yaml_file.write_text("")

    model = load_semantic_model(yaml_file)

    assert model.entities == []
    assert model.dimensions == []
    assert model.metrics == []
    assert model.relationships == []


def test_yml_extension_is_loaded_too(tmp_path):
    (tmp_path / "model.yml").write_text(ENTITY_YAML)

    model = load_semantic_model(tmp_path)

    assert [e.name for e in model.entities] == ["orders"]


def test_non_yaml_files_in_a_directory_are_ignored(tmp_path):
    (tmp_path / "entities.yaml").write_text(ENTITY_YAML)
    (tmp_path / "README.md").write_text("not a semantic model file")

    model = load_semantic_model(tmp_path)

    assert [e.name for e in model.entities] == ["orders"]


def test_unreadable_file_raises_a_clear_error(tmp_path):
    yaml_file = tmp_path / "model.yaml"
    yaml_file.write_text(ENTITY_YAML)
    yaml_file.chmod(0o000)
    try:
        with pytest.raises(SemanticModelLoadError, match="Could not read"):
            load_semantic_model(yaml_file)
    finally:
        yaml_file.chmod(0o644)
