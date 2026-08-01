from .model import shortest_path, minimum_spanning_tree, max_flow, min_cost_max_flow


def test_shortest_path_on_simple_graph():
    edges = [("A", "B", 1), ("B", "C", 1), ("A", "C", 5)]
    result = shortest_path(edges, "A", "C")
    assert result["path"] == ["A", "B", "C"]
    assert result["length"] == 2


def test_shortest_path_negative_weight_uses_bellman_ford():
    edges = [("A", "B", 4), ("A", "C", 5), ("C", "B", -3)]
    result = shortest_path(edges, "A", "B", directed=True)
    assert result["method"] == "bellman-ford"
    assert result["length"] == 2          # A->C->B = 5 + (-3)
    assert result["path"] == ["A", "C", "B"]


def test_minimum_spanning_tree_total_weight():
    # 四点环，去掉最重的边即为 MST
    edges = [("A", "B", 1), ("B", "C", 2), ("C", "D", 3), ("D", "A", 10)]
    result = minimum_spanning_tree(edges)
    assert result["total_weight"] == 6    # 1+2+3，弃掉权重 10 的边
    assert len(result["edges"]) == 3      # n 个节点的树有 n-1 条边


def test_max_flow_bottleneck():
    # A->B 容量 3，B->C 容量 2 -> 瓶颈为 2
    edges = [("A", "B", 3), ("B", "C", 2)]
    result = max_flow(edges, "A", "C")
    assert result["max_flow"] == 2.0


def test_min_cost_max_flow():
    # 两条并行路径，容量各 1，费用分别 1 和 5：满流 2，最小费用 6
    edges = [("S", "A", 1, 1), ("A", "T", 1, 0),
             ("S", "B", 1, 5), ("B", "T", 1, 0)]
    result = min_cost_max_flow(edges, "S", "T")
    assert result["max_flow"] == 2.0
    assert result["min_cost"] == 6.0
