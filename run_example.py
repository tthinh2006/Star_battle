"""Run a small Star Battle DFS example (no dependencies required)."""

from blind_search import SearchStats, star_battle_dfs_solver

PUZZLE = [
    [0, 0, 1, 1, 1],
    [1, 1, 1, 1, 1],
    [1, 1, 2, 4, 4],
    [3, 3, 2, 4, 4],
    [3, 3, 2, 4, 4],
]


def main():
    stats = SearchStats()
    solution = star_battle_dfs_solver(PUZZLE, stars=1, stats=stats)
    if solution is None:
        print("No solution found.")
        return

    print("Star Battle (5x5, one star per row/column/region):")
    for row in range(len(PUZZLE)):
        print(" ".join("*" if (row, col) in solution else "." for col in range(len(PUZZLE))))
    print("\nStar positions (zero-based):", sorted(solution))
    print("Nodes:", stats.nodes)
    print("Decisions:", stats.decisions)
    print("Backtracks:", stats.backtracks)


if __name__ == "__main__":
    main()
