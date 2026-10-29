"""Basic regression tests using only Python's standard library."""

import unittest
from blind_search import SearchStats, star_battle_dfs_solver, validate_puzzle

PUZZLE_5X5 = [
    [0, 0, 1, 1, 1],
    [1, 1, 1, 1, 1],
    [1, 1, 2, 4, 4],
    [3, 3, 2, 4, 4],
    [3, 3, 2, 4, 4],
]

PUZZLE_6X6 = [
    [0, 1, 1, 2, 2, 2],
    [0, 0, 0, 2, 2, 2],
    [0, 3, 3, 3, 5, 5],
    [4, 4, 3, 3, 5, 5],
    [4, 4, 4, 5, 5, 5],
    [4, 4, 4, 5, 5, 5],
]


def check_solution(test_case, puzzle, stars, solution):
    n = len(puzzle)
    test_case.assertIsNotNone(solution)
    test_case.assertEqual(len(solution), n * stars)
    for row in range(n):
        test_case.assertEqual(sum(r == row for r, c in solution), stars)
    for col in range(n):
        test_case.assertEqual(sum(c == col for r, c in solution), stars)
    for region in set(v for row in puzzle for v in row):
        test_case.assertEqual(sum(puzzle[r][c] == region for r, c in solution), stars)
    for r, c in solution:
        for rr, cc in solution:
            if (r, c) != (rr, cc):
                test_case.assertFalse(abs(r - rr) <= 1 and abs(c - cc) <= 1)


class StarBattleSolverTests(unittest.TestCase):
    def test_5x5_solution(self):
        stats = SearchStats()
        solution = star_battle_dfs_solver(PUZZLE_5X5, 1, stats=stats)
        check_solution(self, PUZZLE_5X5, 1, solution)
        self.assertEqual(solution, {(0, 1), (1, 4), (2, 2), (3, 0), (4, 3)})
        self.assertEqual(stats.nodes, 14)

    def test_6x6_solution(self):
        solution = star_battle_dfs_solver(PUZZLE_6X6, 1)
        check_solution(self, PUZZLE_6X6, 1, solution)

    def test_invalid_non_square(self):
        with self.assertRaises(ValueError):
            validate_puzzle([[0, 1], [0]], 1)

    def test_invalid_stars_count(self):
        with self.assertRaises(ValueError):
            validate_puzzle(PUZZLE_5X5, 0)


if __name__ == "__main__":
    unittest.main()
