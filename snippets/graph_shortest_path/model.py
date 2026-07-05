import networkx as nx


def shortest_path(edges: list, source, target) -> dict:
    graph = nx.Graph()
    graph.add_weighted_edges_from(edges)
    path = nx.shortest_path(graph, source, target, weight="weight")
    length = nx.shortest_path_length(graph, source, target, weight="weight")
    return {"path": path, "length": length}
