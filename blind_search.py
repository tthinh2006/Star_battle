from .core import (Search, SearchStats, RowModel, validate_puzzle, get_region_cell)

# Các tên import từ core được giữ lại ở đây để mã cũ vẫn import được từ blind_search.
__all__ = ["DFSSearch", "star_battle_dfs_solver", "Search", "SearchStats",
           "RowModel", "validate_puzzle", "get_region_cell"]



class DFSSearch(Search):
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
    search = DFSSearch(puzzle, stars, visualizer, stats)
    domains = [search.model.full] * search.model.n
    search.emit('Start', domains)
    result = search.dfs()
    search.emit('Solved' if result is not None else 'No solution')
    return result
