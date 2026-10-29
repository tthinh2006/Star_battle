# Star Battle Puzzle

A Python 3 implementation of the **Star Battle** logic puzzle using **Depth-First Search (DFS)** with backtracking and constraint checking.

The solver explores the board **row by row in a fixed order**. It generates valid star-placement patterns for each row, filters out patterns that violate existing constraints, and backtracks when a branch cannot be completed. It uses integer bit masks to represent candidate sets efficiently.

A standalone HTML page is also available for replaying **recorded DFS search steps**. The HTML page and Python solver run independently: the page does not execute Python or solve a new puzzle in the browser.

This README documents the **DFS implementation only**.

## Requirements and run on Windows


## Star Battle rules

For an `N x N` board divided into `N` regions, place exactly `k` stars in each:

- **Row**
- **Column**
- **Region**

No two stars may touch **horizontally, vertically, or diagonally**. Regions consist of orthogonally connected cells and are identified by integer labels in the input matrix.

## Puzzle input and validation

A puzzle is represented by a square list of lists. Each integer identifies the **region** containing that cell; it is **not** a star or an empty-cell value.

Example (`5 x 5`, one star per row, column, and region):

```python
puzzle = [
    [0, 0, 1, 1, 1],
    [1, 1, 1, 1, 1],
    [1, 1, 2, 4, 4],
    [3, 3, 2, 4, 4],
    [3, 3, 2, 4, 4],
]
stars = 1
```

`validate_puzzle(puzzle, stars)` checks:

- The board is a nonempty square matrix.
- `stars` is a positive integer.
- Every region label is an integer.
- The board contains exactly `N` distinct regions.
- Every region is orthogonally connected.

Invalid input raises `ValueError`. Passing validation does **not** guarantee that a puzzle has a solution or that its solution is unique.

## Using the DFS solver

The public entry point is `star_battle_dfs_solver(puzzle, stars, visualizer=None, *, stats=None)` in `blind_search.py`.

Paste this example into the Python interpreter, or save it as a separate `.py` file in the repository directory:

```python
from blind_search import SearchStats, star_battle_dfs_solver

puzzle = [
    [0, 0, 1, 1, 1],
    [1, 1, 1, 1, 1],
    [1, 1, 2, 4, 4],
    [3, 3, 2, 4, 4],
    [3, 3, 2, 4, 4],
]

stats = SearchStats()
solution = star_battle_dfs_solver(puzzle, stars=1, stats=stats)

print(sorted(solution) if solution is not None else None)
print("Nodes:", stats.nodes)
print("Decisions:", stats.decisions)
print("Backtracks:", stats.backtracks)
```

For this example, the solver returns:

```text
[(0, 1), (1, 4), (2, 2), (3, 0), (4, 3)]
Nodes: 14
Decisions: 13
Backtracks: 8
```

The output is a `set` of `(row, column)` positions with **zero-based indices**; the example sorts the set for display. The solver returns `None` if it finds no solution. It stops at the **first valid solution**, rather than enumerating all solutions.

## DFS model and traversal

The solver is implemented in `blind_search.py` using `RowModel` and `Search`.

1. **Build a row model.** `RowModel` generates every possible arrangement of `k` horizontally nonadjacent stars within one row. Each pattern is a tuple of column indices. The number of possible row patterns, before considering regions, is `C(N - k + 1, k)` when such placements are possible.
2. **Precompute constraint masks.** `col_support` tracks which patterns occupy each column. `compatible` encodes star placements that do not touch across adjacent rows. `region_allowed` helps exclude patterns that would exceed a region's star quota.
3. **Start at row 0.** `Search.dfs(row=0)` always processes rows from top to bottom. It does not dynamically choose the next row.
4. **Filter candidates.** `Search.legal_domain()` removes row patterns that would touch stars in an already assigned adjacent row or exceed the allowed star count in a column or region.
5. **Try a pattern and recurse.** `Search.assign()` updates the chosen row pattern and the column/region counters. DFS then recursively processes the next row.
6. **Backtrack on failure.** If deeper recursion returns no solution, the same assignment is undone, the backtrack counter is incremented, and the next candidate is tried.
7. **Check the goal.** After all rows have been assigned, `Search.goal()` verifies that **every column and region** has exactly `k` stars. Each row already has exactly `k` stars by construction. A complete valid placement is returned.

Candidate patterns are processed in a **deterministic order**. This is **uninformed DFS with constraint checking and pruning**: the row order is fixed, and the solver does not perform a separate look-ahead search over future rows. Constraint checks prevent exploring placements that are already known to be invalid.

## Search statistics

`SearchStats` records:

| Field | Meaning |
| --- | --- |
| `nodes` | Number of calls to the recursive `dfs()` function, including the initial and terminal calls. |
| `decisions` | Number of row-pattern assignments attempted. |
| `backtracks` | Number of assignments undone after unsuccessful recursive searches. |
| `max_depth` | Deepest recursion depth reached, measured by the row index passed to `dfs()`. |

`domain_values_removed` and `bound_failures` also exist in the shared statistics structure, but **this DFS implementation does not update them**. A value of zero for either field must not be interpreted as evidence that no constraint-based pruning occurred.

Create a fresh `SearchStats()` object for each independent run; the solver does not reset an existing statistics object automatically.

## DFS visualization

`index.html` provides an interactive **playback of previously recorded search events**. It contains six example configurations:

| Board size | Stars per row, column, and region |
| --- | --- |
| `5 x 5` | 1 |
| `6 x 6` | 1 |
| `7 x 7` | 1 |
| `8 x 8` | 1 |
| `10 x 10` | 1 |
| `10 x 10` | 2 |

To inspect DFS, select a sample board, switch to the **DFS** tab, and use the playback controls to go to the first or last step, move backward or forward, play/pause, or adjust the playback speed.

The visualization shows the placed stars, the current row, and recorded search counters. It can illustrate assignments, backtracking, and the completed solution. It does **not** call `star_battle_dfs_solver()` or accept arbitrary puzzles for live solving. Any recorded timings refer to the original trace-generation runs, not the time taken by browser playback.

## Repository structure

```text
Star_battle/
|-- README.md         # Project documentation
|-- blind_search.py   # DFS solver, row model, validation, statistics
`-- index.html        # Browser visualization of recorded search steps
```

## Scope and limitations

- The Python solver finds **one** solution, if one exists; it does not count or enumerate all solutions.
- Puzzle validation checks structural requirements but does not prove solvability or uniqueness.
- The search can require substantial backtracking on more difficult puzzles; the implementation does not guarantee a particular execution time or memory usage.
- The HTML interface replays embedded examples rather than computing new solutions in the browser.

