"""Directed-graph cycle detection shared by the validator and the lineage graph."""

_WHITE, _GRAY, _BLACK = 0, 1, 2


def build_adjacency(edges: list[tuple[str, str]]) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {}
    for source, target in edges:
        graph.setdefault(source, []).append(target)
        graph.setdefault(target, [])
    return graph


def find_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    """Return one cycle, as a list of nodes, or None if the graph is acyclic."""
    color = dict.fromkeys(graph, _WHITE)
    path: list[str] = []
    cycle: list[str] | None = None

    def visit(node: str) -> bool:
        nonlocal cycle
        color[node] = _GRAY
        path.append(node)
        for neighbor in graph[node]:
            if color[neighbor] == _GRAY:
                cycle = path[path.index(neighbor) :] + [neighbor]
                return True
            if color[neighbor] == _WHITE and visit(neighbor):
                return True
        path.pop()
        color[node] = _BLACK
        return False

    for node in list(graph):
        if color[node] == _WHITE and visit(node):
            break
    return cycle


def find_cyclic_edges(graph: dict[str, list[str]]) -> set[tuple[str, str]]:
    """Return every edge that closes some cycle in the graph (back edges)."""
    color = dict.fromkeys(graph, _WHITE)
    edges: set[tuple[str, str]] = set()

    def visit(node: str) -> None:
        color[node] = _GRAY
        for neighbor in graph[node]:
            if color[neighbor] == _GRAY:
                edges.add((node, neighbor))
            elif color[neighbor] == _WHITE:
                visit(neighbor)
        color[node] = _BLACK

    for node in list(graph):
        if color[node] == _WHITE:
            visit(node)
    return edges
