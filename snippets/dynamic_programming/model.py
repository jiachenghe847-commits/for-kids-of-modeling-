import numpy as np


def knapsack_01(weights, values, capacity: int) -> dict:
    """0-1 背包：每个物品选或不选，总重不超 capacity，最大化总价值。

    weights/values: 各物品重量/价值（重量须为非负整数）。capacity: 背包容量（整数）。
    返回最大价值与被选中物品下标。
    """
    w = list(weights)
    v = list(values)
    n = len(w)
    dp = np.zeros((n + 1, capacity + 1))
    for i in range(1, n + 1):
        for c in range(capacity + 1):
            dp[i][c] = dp[i - 1][c]
            if w[i - 1] <= c:
                dp[i][c] = max(dp[i][c], dp[i - 1][c - w[i - 1]] + v[i - 1])
    # 回溯选中的物品
    chosen = []
    c = capacity
    for i in range(n, 0, -1):
        if dp[i][c] != dp[i - 1][c]:
            chosen.append(i - 1)
            c -= w[i - 1]
    chosen.reverse()
    return {"max_value": float(dp[n][capacity]), "chosen": chosen}


def longest_increasing_subsequence(seq) -> dict:
    """最长严格递增子序列（LIS）的长度与一个具体子序列。O(n^2) 版，题目规模小时够用。"""
    a = list(seq)
    n = len(a)
    if n == 0:
        return {"length": 0, "subsequence": []}
    dp = [1] * n
    prev = [-1] * n
    for i in range(n):
        for j in range(i):
            if a[j] < a[i] and dp[j] + 1 > dp[i]:
                dp[i] = dp[j] + 1
                prev[i] = j
    end = int(np.argmax(dp))
    sub = []
    while end != -1:
        sub.append(a[end])
        end = prev[end]
    sub.reverse()
    return {"length": int(max(dp)), "subsequence": sub}


def coin_change(coins, amount: int) -> dict:
    """凑成 amount 所需的最少硬币数（每种硬币无限个）。凑不出返回 -1。"""
    INF = float("inf")
    dp = [0] + [INF] * amount
    for c in range(1, amount + 1):
        for coin in coins:
            if coin <= c and dp[c - coin] + 1 < dp[c]:
                dp[c] = dp[c - coin] + 1
    return {"min_coins": int(dp[amount]) if dp[amount] != INF else -1}
