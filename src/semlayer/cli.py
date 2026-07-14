import argparse
import sys
from pathlib import Path

from semlayer.describe import (
    DescribeError,
    describe_entities,
    describe_entity,
    describe_metric,
    describe_metrics,
)
from semlayer.lineage import (
    LineageError,
    export_dependency_graph,
    format_metric_lineage,
    metric_lineage,
)
from semlayer.loader import SemanticModelLoadError, load_semantic_model
from semlayer.validator import SemanticModelValidationError, validate_semantic_model


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        model = load_semantic_model(args.path)

        if args.command == "describe":
            # Description is meant to be trusted, so validate first: a
            # broken model should surface as a clear validation error here,
            # not confusing/partial describe output.
            validate_semantic_model(model)
            output = _dispatch_describe(model, args)
        else:
            # Lineage/graph commands intentionally skip validation — a model
            # with a circular relationship would otherwise never reach the
            # graph output, and seeing *where* the cycle is is the point.
            output = _dispatch_lineage(model, args)
    except (
        SemanticModelLoadError,
        SemanticModelValidationError,
        DescribeError,
        LineageError,
    ) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(output)
    return 0


def _dispatch_describe(model, args) -> str:
    if args.describe_command == "entities":
        return describe_entities(model)
    if args.describe_command == "entity":
        return describe_entity(model, args.name)
    if args.describe_command == "metrics":
        return describe_metrics(model)
    return describe_metric(model, args.name)


def _dispatch_lineage(model, args) -> str:
    if args.command == "lineage":
        return format_metric_lineage(metric_lineage(model, args.name))
    return export_dependency_graph(model)


def _build_parser() -> argparse.ArgumentParser:
    # Shared by every leaf command so --path reads naturally after the
    # command name, e.g. `semlayer describe entity orders --path model.yaml`.
    path_parent = argparse.ArgumentParser(add_help=False)
    path_parent.add_argument(
        "--path",
        required=True,
        type=Path,
        help="Path to a semantic model YAML file or a directory of them",
    )

    parser = argparse.ArgumentParser(prog="semlayer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    describe = subparsers.add_parser("describe", help="Describe parts of the semantic model")
    describe_subparsers = describe.add_subparsers(dest="describe_command", required=True)

    describe_subparsers.add_parser("entities", parents=[path_parent], help="List all entities")

    entity_parser = describe_subparsers.add_parser(
        "entity", parents=[path_parent], help="Describe a single entity"
    )
    entity_parser.add_argument("name")

    describe_subparsers.add_parser("metrics", parents=[path_parent], help="List all metrics")

    metric_parser = describe_subparsers.add_parser(
        "metric", parents=[path_parent], help="Describe a single metric"
    )
    metric_parser.add_argument("name")

    lineage = subparsers.add_parser(
        "lineage", parents=[path_parent], help="Print a metric's lineage"
    )
    lineage.add_argument("name")

    graph = subparsers.add_parser("graph", help="Work with the full dependency graph")
    graph_subparsers = graph.add_subparsers(dest="graph_command", required=True)
    graph_subparsers.add_parser(
        "export", parents=[path_parent], help="Export the full dependency graph as DOT"
    )

    return parser


if __name__ == "__main__":
    sys.exit(main())
