from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations



def get_region_cell(puzzle):
    regions = defaultdict(list)
    for r, row in enumerate(puzzle):
        for c, region in enumerate(row):
            regions[region].append((r, c))
    return regions


def validate_puzzle(puzzle, stars):
    n = len(puzzle)
    if n == 0 or any(len(row) != n for row in puzzle):
        raise ValueError("The board must be a nonempty square matrix.")
    if type(stars) is not int or stars < 1:
        raise ValueError("Stars per row/column/region must be a positive integer.")
    if any(type(v) is not int for row in puzzle for v in row):
        raise ValueError("Region IDs must be integers.")
    regions = get_region_cell(puzzle)
    if len(regions) != n:
        raise ValueError(f"A standard {n}x{n} board must contain exactly {n} regions.")
    for label, cells in regions.items():
        unseen = set(cells)
        stack = [unseen.pop()]
        while stack:
            r, c = stack.pop()
            for cell in ((r-1, c), (r+1, c), (r, c-1), (r, c+1)):
                if cell in unseen:
                    unseen.remove(cell)
                    stack.append(cell)
        if unseen:
            raise ValueError(f"Region {label} is not orthogonally connected.")
    return n, regions



@dataclass
class SearchStats:
    nodes: int = 0       
    decisions: int = 0         
    backtracks: int = 0       
    domain_values_removed: int = 0  
    bound_failures: int = 0
    max_depth: int = 0



class RowModel:
    def __init__(self, puzzle, k):
        self.n, regions = validate_puzzle(puzzle, k)
        self.k = k
        labels = {g: i for i, g in enumerate(sorted(regions))}
        self.board = [[labels[g] for g in row] for row in puzzle]
        n = self.n
        self.patterns = tuple(tuple(y + i for i, y in enumerate(xs))
                              for xs in combinations(range(max(0, n-k+1)), k))
        p = len(self.patterns)
        self.full = (1 << p) - 1
        self.col_support = [0] * n
        for i, columns in enumerate(self.patterns):
            for c in columns:
                self.col_support[c] |= 1 << i
        self.compatible = []
        for columns in self.patterns:
            blocked = 0
            for c in columns:
                for other in range(max(0, c-1), min(n, c+2)):
                    blocked |= self.col_support[other]
            self.compatible.append(self.full & ~blocked)
        self.contributions = []
        self.region_allowed = []
        self.region_exact = []
        for row in self.board:
            contributions = []
            exact = {g: [0] * (k+1) for g in set(row)}
            for i, columns in enumerate(self.patterns):
                counts = {}
                for c in columns:
                    g = row[c]
                    counts[g] = counts.get(g, 0) + 1
                contributions.append(tuple(counts.items()))
                for g in exact:
                    exact[g][counts.get(g, 0)] |= 1 << i
            allowed = {}
            for g, buckets in exact.items():
                cumulative = 0
                allowed[g] = []
                for mask in buckets:
                    cumulative |= mask
                    allowed[g].append(cumulative)
            self.contributions.append(contributions)
            self.region_allowed.append(allowed)
            self.region_exact.append(exact)



class Search:
    def __init__(self, puzzle, k, visualizer=None, stats=None):
        self.model = RowModel(puzzle, k)
        self.stats = stats if stats is not None else SearchStats()
        self.visualizer = visualizer
        n = self.model.n
        self.assigned = [-1] * n
        self.cols = [0] * n
        self.regions = [0] * n


    def solution(self):
        return {(r, c) for r, p in enumerate(self.assigned) if p >= 0
                for c in self.model.patterns[p]}


    def emit(self, reason, domains=None, row=None):
        if self.visualizer is not None:
            self.visualizer.add_step(
                action='snapshot', message=reason, row=row,
                placed=sorted(self.solution()), assigned=self.assigned.copy(),
                domain_sizes=None if domains is None else
                [None if self.assigned[r] >= 0 else d.bit_count() for r, d in enumerate(domains)])


    def legal_domain(self, row, domain):
        m = self.model
        for near in (row-1, row+1):
            if 0 <= near < m.n and self.assigned[near] >= 0:
                domain &= m.compatible[self.assigned[near]]
        for c, count in enumerate(self.cols):
            if count == m.k:
                domain &= ~m.col_support[c]
        for g, thresholds in m.region_allowed[row].items():
            domain &= thresholds[m.k - self.regions[g]]
        return domain


    def assign(self, row, pattern, delta):
        m = self.model
        self.assigned[row] = pattern if delta == 1 else -1
        for c in m.patterns[pattern]:
            self.cols[c] += delta
        for g, count in m.contributions[row][pattern]:
            self.regions[g] += delta * count


    def goal(self):
        return all(x == self.model.k for x in self.cols + self.regions)


    def dfs(self, row=0):
        s, m = self.stats, self.model
        s.nodes += 1
        s.max_depth = max(s.max_depth, row)
        if row == m.n:
            return self.solution() if self.goal() else None
        candidates = self.legal_domain(row, m.full)
        while candidates:
            bit = candidates & -candidates
            candidates ^= bit
            pattern = bit.bit_length() - 1
            s.decisions += 1
            self.assign(row, pattern, 1)
            self.emit('DFS: assign row', row=row)
            result = self.dfs(row + 1)
            if result is not None:
                return result
            self.assign(row, pattern, -1)
            s.backtracks += 1
            self.emit('DFS: restore after backtracking', row=row)
        return None



def star_battle_dfs_solver(puzzle, stars, visualizer=None, *, stats=None):
    search = Search(puzzle, stars, visualizer, stats)
    domains = [search.model.full] * search.model.n
    search.emit('Start', domains)
    result = search.dfs()
    search.emit('Solved' if result is not None else 'No solution')
    return result
