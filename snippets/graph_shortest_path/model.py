import networkx as nx


def shortest_path(edges: list, source, target, directed: bool = False) -> dict:
    """最短路。edges 为 (u, v, weight) 列表；有向图传 directed=True。

    含负权边时自动改用 Bellman-Ford（Dijkstra 对负权不适用）。
    """
    graph = nx.DiGraph() if directed else nx.Graph()
    graph.add_weighted_edges_from(edges)
    method = "bellman-ford" if any(w < 0 for *_, w in edges) else "dijkstra"
    path = nx.shortest_path(graph, source, target, weight="weight", method=method)
    length = nx.shortest_path_length(graph, source, target, weight="weight", method=method)
    return {"path": path, "length": length, "method": method}


def minimum_spanning_tree(edges: list) -> dict:
    """最小生成树（Kruskal）：用最小总代价把所有节点连通。

    典型场景：铺设管道/电缆/道路把若干点全连上，求最省方案。仅适用于无向图。
    """
    graph = nx.Graph()
    graph.add_weighted_edges_from(edges)
    mst = nx.minimum_spanning_tree(graph, weight="weight")
    tree_edges = [(u, v, d["weight"]) for u, v, d in mst.edges(data=True)]
    total = sum(w for *_, w in tree_edges)
    return {"edges": tree_edges, "total_weight": float(total), "graph": mst}


def max_flow(edges: list, source, sink) -> dict:
    """最大流：有向网络中从源点到汇点的最大通过量。

    edges 为 (u, v, capacity) 列表，capacity 是容量而非距离。
    典型场景：管网输送、交通通行能力、供需匹配上限。
    """
    graph = nx.DiGraph()
    for u, v, c in edges:
        graph.add_edge(u, v, capacity=c)
    value, flow_dict = nx.maximum_flow(graph, source, sink)
    return {"max_flow": float(value), "flow": flow_dict}


def min_cost_max_flow(edges: list, source, sink) -> dict:
    """最小费用最大流。edges 为 (u, v, capacity, weight) 列表，weight 是单位流量费用。"""
    graph = nx.DiGraph()
    for u, v, c, w in edges:
        graph.add_edge(u, v, capacity=c, weight=w)
    flow_dict = nx.max_flow_min_cost(graph, source, sink)
    cost = nx.cost_of_flow(graph, flow_dict)
    value = sum(flow_dict[source].values())
    return {"max_flow": float(value), "min_cost": float(cost), "flow": flow_dict}
