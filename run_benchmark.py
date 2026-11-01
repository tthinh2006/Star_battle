"""Compare DFS and heuristic search on the Star Battle test files."""

import argparse
import importlib
from pathlib import Path
import sys
import types


BASE_DIR = Path(__file__).resolve().parent

# The solvers use relative imports (.core). Give this folder a package name
# when this file is executed directly, even if it has no __init__.py.
if __package__:
    PACKAGE = __package__
else:
    PACKAGE = "_star_battle_benchmark"
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(BASE_DIR)]
    sys.modules[PACKAGE] = package

measure = importlib.import_module(f"{PACKAGE}.utils").measure
star_battle_dfs_solver = importlib.import_module(
    f"{PACKAGE}.blind_search"
).star_battle_dfs_solver
star_battle_heuristic_solver = importlib.import_module(
    f"{PACKAGE}.heuristic_search"
).star_battle_heuristic_solver


STAR_BATTLE_TEST_FILES = [
    "test/star_battle/5x5_1star.txt",
    "test/star_battle/6x6_1star.txt",
    "test/star_battle/7x7_1star.txt",
    "test/star_battle/8x8_1star.txt",
    "test/star_battle/10x10_1star.txt",
    "test/star_battle/10x10_2stars.txt",
]


def read_puzzle(path):
    """Read an n-by-n region grid preceded by 'n stars_per_unit'."""
    lines = [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines()
             if line.strip()]
    if not lines:
        raise ValueError("Empty puzzle file.")
    size, stars = map(int, lines[0].split())
    puzzle = [list(map(int, line.split())) for line in lines[1:]]
    if size <= 0 or len(puzzle) != size or any(len(row) != size for row in puzzle):
        raise ValueError(f"Expected a {size}x{size} region grid.")
    return puzzle, stars


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "files", nargs="*",
        help="Optional puzzle files; relative paths are resolved from this script's folder.",
    )
    args = parser.parse_args()
    print("================ STAR BATTLE BENCHMARK ================", flush=True)
    print(f"{'Test':18} {'DFS(ms)':>12} {'DFS(KB)':>12} "
          f"{'Heu(ms)':>12} {'Heu(KB)':>12}", flush=True)
    print("-" * 72, flush=True)

    for filename in args.files or STAR_BATTLE_TEST_FILES:
        path = Path(filename)
        if not path.is_absolute():
            path = BASE_DIR / path
        try:
            puzzle, stars = read_puzzle(path)
        except (OSError, ValueError) as error:
            print(f"{path.stem}: ERROR: {error}", flush=True)
            continue

        print(f"Running {path.stem}...", flush=True)
        dfs_result, dfs_ms, dfs_kb = measure(star_battle_dfs_solver, puzzle, stars)
        heu_result, heu_ms, heu_kb = measure(star_battle_heuristic_solver, puzzle, stars)
        print(f"{path.stem:18} {dfs_ms:>12.2f} {dfs_kb:>12.2f} "
              f"{heu_ms:>12.2f} {heu_kb:>12.2f}", flush=True)
        for name, result in (("DFS", dfs_result), ("Heuristic", heu_result)):
            if result is None:
                print(f"  {name}: no solution returned (unsatisfiable, error, or timeout).",
                      flush=True)


if __name__ == "__main__":
    main()
