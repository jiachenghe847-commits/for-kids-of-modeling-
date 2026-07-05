from model import shortest_path


def test_shortest_path_on_simple_graph():
    edges = [("A", "B", 1), ("B", "C", 1), ("A", "C", 5)]
    result = shortest_path(edges, "A", "C")
    assert result["path"] == ["A", "B", "C"]
    assert result["length"] == 2
