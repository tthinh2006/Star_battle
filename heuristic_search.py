"""Star Battle — Backtracking + Forward Checking + MRV (Python 3.10+).

Dùng get_region_cell từ game.py trong cùng package star_battle.
Giữ nguyên tên hàm và tham số để chạy với benchmark của bản tham khảo.

Mỗi biến là một hàng; mỗi giá trị là một cách đặt đủ k sao không kề nhau.
Bản tách giữ nguyên thứ tự tìm kiếm, kiểm tra và bộ đếm của bản cải tiến.
Không lưu sẵn đáp án cho bất kỳ bàn cờ nào.

visualizer (tùy chọn) nhận action='snapshot' như bản cải tiến;
visualizer cũ cần điều chỉnh để hiển thị định dạng này.
"""
from dataclasses import dataclass
from itertools import combinations
from .game import get_region_cell


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
    nodes: int = 0             # Entries into recursive search, including root/goal.
    decisions: int = 0         # Row assignments attempted.
    backtracks: int = 0        # Attempted row assignments undone after failure.
    domain_values_removed: int = 0  # FC removals, including revisited branches.
    bound_failures: int = 0
    max_depth: int = 0



class RowModel:
    def __init__(self, puzzle, k):
        self.n, regions = validate_puzzle(puzzle, k)
        self.k = k
        labels = {g: i for i, g in enumerate(sorted(regions))}
        self.board = [[labels[g] for g in row] for row in puzzle]
        n = self.n
        # Generate only nonconsecutive columns: c_i = y_i + i.
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
        # Whole snapshots faithfully restore state on backtracking. No work when off.
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


    def capacity_possible(self, domains):
        """Necessary lower/upper quota bounds, not arc consistency.

        Sum each unassigned row's min/max possible contribution to a column or
        region. A quota outside that interval cannot be reached by any solution.
        Passing this check is NOT a proof that the branch is solvable.
        """
        m = self.model
        low_c, high_c = self.cols.copy(), self.cols.copy()
        low_g, high_g = self.regions.copy(), self.regions.copy()
        for r, domain in enumerate(domains):
            if self.assigned[r] >= 0:
                continue
            if not domain:
                return False
            for c, support in enumerate(m.col_support):
                if domain & support:
                    high_c[c] += 1
                    if not domain & ~support:
                        low_c[c] += 1
            for g, buckets in m.region_exact[r].items():
                possible = [q for q, mask in enumerate(buckets) if domain & mask]
                low_g[g] += possible[0]
                high_g[g] += possible[-1]
        return all(lo <= m.k <= hi for lo, hi in zip(low_c + low_g, high_c + high_g))


    def heuristic(self, domains, depth=0):
        s, m = self.stats, self.model
        s.nodes += 1
        s.max_depth = max(s.max_depth, depth)
        if depth == m.n:
            return self.solution() if self.goal() else None
        if not self.capacity_possible(domains):
            s.bound_failures += 1
            return None
        # Exact MRV over remaining ROW-PATTERN values, then smallest row index.
        row = min((r for r in range(m.n) if self.assigned[r] < 0),
                  key=lambda r: (domains[r].bit_count(), r))
        candidates = domains[row]
        while candidates:
            bit = candidates & -candidates
            candidates ^= bit
            pattern = bit.bit_length() - 1
            s.decisions += 1
            self.assign(row, pattern, 1)
            # Domains are Python integers. Shallow copy, no recursive deepcopy.
            new_domains = domains.copy()
            new_domains[row] = 0
            valid = True
            for other in range(m.n):
                if self.assigned[other] < 0:
                    old = domains[other]
                    new = self.legal_domain(other, old)
                    new_domains[other] = new
                    s.domain_values_removed += old.bit_count() - new.bit_count()
                    if not new:
                        valid = False
                        break
            # Do not present partially filtered domains if FC stopped early.
            self.emit('MRV: assign row; forward check' if valid else 'MRV: domain wipeout',
                      new_domains if valid else None, row)
            if valid:
                result = self.heuristic(new_domains, depth+1)
                if result is not None:
                    return result
            self.assign(row, pattern, -1)
            s.backtracks += 1
            self.emit('MRV: restore after backtracking', domains, row)
        return None



def star_battle_heuristic_solver(puzzle, stars, visualizer=None, *, stats=None):
    """Trả về tập (hàng, cột) của nghiệm đầu tiên, hoặc None nếu vô nghiệm.

    puzzle: ma trận nhãn vùng vuông, gồm n vùng liên thông cạnh.
    stars: số sao bắt buộc trên mỗi hàng, cột và vùng.
    stats: tùy chọn, truyền SearchStats() để đọc các bộ đếm sau khi chạy.
    Đầu vào không hợp lệ phát sinh ValueError. Không sửa ma trận đầu vào.
    """
    search = Search(puzzle, stars, visualizer, stats)
    domains = [search.model.full] * search.model.n
    search.emit('Start', domains)
    result = search.heuristic(domains)
    search.emit('Solved' if result is not None else 'No solution')
    return result
