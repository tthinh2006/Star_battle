from .core import (Search, SearchStats, RowModel, validate_puzzle, get_region_cell)

# Các tên import từ core được giữ lại ở đây để mã cũ vẫn import được từ heuristic_search.
__all__ = ["HeuristicSearch", "star_battle_heuristic_solver", "Search",
           "SearchStats", "RowModel", "validate_puzzle", "get_region_cell"]



class HeuristicSearch(Search):
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
    search = HeuristicSearch(puzzle, stars, visualizer, stats)
    domains = [search.model.full] * search.model.n
    search.emit('Start', domains)
    result = search.heuristic(domains)
    search.emit('Solved' if result is not None else 'No solution')
    return result
