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
from semlayer.loader import SemanticModelLoadError, load_semantic_model
from semlayer.validator import SemanticModelValidationError, validate_semantic_model


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        model = load_semantic_model(args.path)
        validate_semantic_model(model)

        if args.describe_command == "entities":
            output = describe_entities(model)
        elif args.describe_command == "entity":
            output = describe_entity(model, args.name)
        elif args.describe_command == "metrics":
            output = describe_metrics(model)
        else:
            output = describe_metric(model, args.name)
    except (SemanticModelLoadError, SemanticModelValidationError, DescribeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(output)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    # Shared by the leaf "describe" commands so --path reads naturally after
    # the command name, e.g. `semlayer describe entity orders --path model.yaml`.
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

    return parser


if __name__ == "__main__":
    sys.exit(main())
