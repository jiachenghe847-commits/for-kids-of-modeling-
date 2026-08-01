from .model import knapsack_01, longest_increasing_subsequence, coin_change


def test_knapsack_known_optimum():
    # 容量 10，物品(重,值)：(2,3)(3,4)(4,5)(5,6) -> 最优取重3+重4+... 经典解 max=13 (取 2,3,5? )
    # 标准算例：weights=[1,3,4,5], values=[1,4,5,7], cap=7 -> 最优 9（取重3值4 + 重4值5）
    result = knapsack_01(weights=[1, 3, 4, 5], values=[1, 4, 5, 7], capacity=7)
    assert result["max_value"] == 9.0
    assert set(result["chosen"]) == {1, 2}   # 下标 1(重3) 和 2(重4)


def test_knapsack_empty_capacity():
    result = knapsack_01(weights=[2, 3], values=[5, 6], capacity=0)
    assert result["max_value"] == 0.0
    assert result["chosen"] == []


def test_lis_length_and_subsequence():
    result = longest_increasing_subsequence([10, 9, 2, 5, 3, 7, 101, 18])
    assert result["length"] == 4       # 如 [2,3,7,18] 或 [2,5,7,101]
    sub = result["subsequence"]
    assert all(sub[i] < sub[i + 1] for i in range(len(sub) - 1))


def test_coin_change_basic():
    assert coin_change([1, 2, 5], 11)["min_coins"] == 3   # 5+5+1
    assert coin_change([2], 3)["min_coins"] == -1          # 凑不出
