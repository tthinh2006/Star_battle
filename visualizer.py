from __future__ import annotations

import importlib
import importlib.util
import math
from pathlib import Path
import queue
import sys
import threading
import time

from PySide6.QtCore import Qt, QRectF, QPointF, QSize, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QApplication, QComboBox, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSlider, QWidget,
)

PUZZLES = [{'name': '5x5_1star_custom', 'size': 5, 'stars': 1, 'regions': [[0, 0, 1, 1, 1], [1, 1, 1, 1, 1], [1, 1, 2, 4, 4], [3, 3, 2, 4, 4], [3, 3, 2, 4, 4]]}, {'name': '6x6_1star_custom', 'size': 6, 'stars': 1, 'regions': [[0, 1, 1, 2, 2, 2], [0, 0, 0, 2, 2, 2], [0, 3, 3, 3, 5, 5], [4, 4, 3, 3, 5, 5], [4, 4, 4, 5, 5, 5], [4, 4, 4, 5, 5, 5]]}, {'name': '7x7_1star', 'size': 7, 'stars': 1, 'regions': [[0, 0, 0, 1, 1, 1, 1], [2, 2, 0, 1, 1, 1, 4], [2, 2, 0, 3, 3, 4, 4], [2, 2, 3, 3, 3, 4, 4], [5, 5, 3, 3, 6, 4, 4], [5, 5, 5, 6, 6, 6, 6], [5, 5, 5, 6, 6, 6, 6]]}, {'name': '8x8_1star', 'size': 8, 'stars': 1, 'regions': [[0, 0, 0, 0, 1, 1, 1, 1], [2, 2, 0, 0, 1, 1, 1, 1], [2, 2, 2, 3, 3, 4, 1, 1], [2, 2, 2, 3, 3, 4, 4, 4], [5, 2, 3, 3, 4, 4, 4, 4], [5, 5, 5, 6, 6, 4, 4, 4], [5, 5, 7, 7, 6, 6, 6, 6], [5, 5, 7, 7, 7, 6, 6, 6]]}, {'name': '10x10_1star', 'size': 10, 'stars': 1, 'regions': [[0, 0, 0, 1, 1, 1, 2, 2, 2, 2], [3, 0, 0, 1, 1, 1, 2, 2, 2, 2], [3, 3, 0, 1, 4, 4, 2, 2, 2, 2], [3, 3, 3, 4, 4, 4, 5, 5, 2, 2], [6, 3, 3, 4, 4, 4, 5, 5, 5, 5], [6, 6, 3, 7, 4, 4, 5, 5, 5, 5], [6, 6, 6, 7, 7, 8, 8, 5, 5, 5], [6, 6, 6, 7, 7, 8, 8, 8, 9, 9], [6, 6, 6, 7, 7, 8, 8, 8, 9, 9], [6, 6, 6, 7, 7, 8, 8, 8, 9, 9]]}, {'name': '10x10_2stars', 'size': 10, 'stars': 2, 'regions': [[0, 0, 0, 0, 0, 1, 1, 2, 2, 2], [0, 0, 0, 0, 0, 1, 1, 1, 1, 2], [3, 3, 0, 0, 0, 1, 1, 1, 1, 1], [3, 3, 0, 0, 0, 4, 4, 4, 4, 4], [3, 3, 0, 0, 5, 4, 4, 4, 4, 4], [6, 6, 7, 5, 5, 5, 5, 4, 4, 4], [6, 6, 7, 5, 5, 5, 5, 4, 4, 4], [6, 7, 7, 5, 5, 5, 5, 8, 8, 8], [6, 7, 7, 5, 5, 5, 9, 9, 8, 8], [7, 7, 7, 9, 9, 9, 9, 9, 8, 8]]}]


PAL = ["#dff0d9", "#dfe5fb", "#fdeecb", "#f7dcdc", "#ead9f2", "#d6eaf6",
       "#fbe1d0", "#d9f1ec", "#efe6d2", "#e6e7f5", "#f0f5d2", "#f8dce9"]
SPEEDS = [1, 2, 5, 10, 30, 100, 300, 1000]
DOT = dict(start="#8aa0c2", assign="#2557b3", back="#e8a317",
           wipe="#b3382c", solved="#1f8a5b", fail="#b3382c")
NAVY, INK, MUTE, BLUE = "#1b3358", "#2d4a78", "#5f7699", "#2557b3"
BG, LINE = "#f6f9fd", "#e2e9f4"


_SOLVER_LOAD_LOCK = threading.RLock()


def load_solver(key):
    module_name = "blind_search" if key == "dfs" else "heuristic_search"
    folder = Path(__file__).resolve().parent
    package_name = "_star_battle_algorithms"
    # Give the original solver modules a package context so that their
    # `from .core import ...` resolves to core.py beside this index.py.
    # import_module also removes a partially loaded solver if an import fails.
    with _SOLVER_LOAD_LOCK:
        if package_name not in sys.modules:
            spec = importlib.util.spec_from_loader(package_name, loader=None,
                                                   is_package=True)
            spec.submodule_search_locations = [str(folder)]
            package = importlib.util.module_from_spec(spec)
            sys.modules[package_name] = package
        return importlib.import_module("." + module_name, package_name)


def validate_solution(puzzle, placed):
    n, k, board = puzzle["size"], puzzle["stars"], puzzle["regions"]
    cells = set(map(tuple, placed))
    if len(cells) != n * k or any(not (0 <= r < n and 0 <= c < n) for r, c in cells):
        return False
    if any(sum(r == i for r, c in cells) != k or
           sum(c == i for r, c in cells) != k for i in range(n)):
        return False
    if any(sum(board[r][c] == g for r, c in cells) != k
           for g in {g for row in board for g in row}):
        return False
    return not any((r + dr, c + dc) in cells for r, c in cells
                   for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc)


class Cancelled(Exception):
    pass


class SearchRun(threading.Thread):
    """Callback bridge. Pause the original recursion at each emitted event.

    The worker never touches Qt widgets. Snapshots and counters are copied
    before enqueueing, so replay cannot accidentally display future counters.
    """
    def __init__(self, puzzle, algorithm):
        super().__init__(daemon=True)
        self.puzzle, self.algorithm = puzzle, algorithm
        self.events = queue.Queue()
        self.condition = threading.Condition()
        self.permits = 0
        self.fast = False
        self.cancelled = False
        self.stats = None

    def advance(self, count=1):
        with self.condition:
            self.permits += count
            self.condition.notify_all()

    def to_end(self):
        with self.condition:
            self.fast = True
            self.condition.notify_all()

    def pause(self):
        with self.condition:
            self.fast = False
            self.permits = 0

    def cancel(self):
        with self.condition:
            self.cancelled = True
            self.condition.notify_all()

    def add_step(self, **data):
        if self.cancelled:
            raise Cancelled()
        s = self.stats
        data["c"] = [s.nodes, s.decisions, s.backtracks, s.bound_failures]
        data["row"] = -1 if data["row"] is None else data["row"]
        if data["message"] == "Solved":
            data["valid"] = validate_solution(self.puzzle, data["placed"])
        self.events.put(("step", data))
        if data["message"] in ("Solved", "No solution"):
            return
        with self.condition:
            self.condition.wait_for(lambda: self.cancelled or self.fast or self.permits > 0)
            if self.cancelled:
                raise Cancelled()
            if not self.fast:
                self.permits -= 1

    def run(self):
        try:
            module = load_solver(self.algorithm)
            self.stats = module.SearchStats()
            fn = (module.star_battle_dfs_solver if self.algorithm == "dfs"
                  else module.star_battle_heuristic_solver)
            fn(self.puzzle["regions"], self.puzzle["stars"], self, stats=self.stats)
            self.events.put(("done", None))
        except Cancelled:
            pass
        except Exception as error:
            self.events.put(("error", str(error)))


def font(size=14, weight=400):
    f = QFont("Segoe UI")
    f.setPixelSize(size)
    f.setWeight(QFont.Weight(weight))
    return f


def text(painter, rect, value, size=14, weight=400, color=NAVY,
         align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
         wrap=False):
    painter.setFont(font(size, weight))
    painter.setPen(QColor(color))
    flags = int(align)
    if wrap:
        flags |= int(Qt.TextFlag.TextWordWrap)
    painter.drawText(QRectF(*rect), flags, str(value))


def wrapped_height(value, width, size=14, minimum=0, weight=400):
    fm = QFontMetricsF(font(size, weight))
    h = fm.boundingRect(QRectF(0, 0, width, 10000),
                        int(Qt.TextFlag.TextWordWrap), value).height()
    return max(minimum, math.ceil(h) + 4)


def box(p, rect, fill="#fff", stroke=LINE, radius=18, pen_width=1):
    p.setBrush(QColor(fill))
    p.setPen(QPen(QColor(stroke), pen_width) if stroke else Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(*rect), radius, radius)


def line(p, x, y, width):
    p.setPen(QPen(QColor(LINE), 1))
    p.drawLine(QPointF(x, y), QPointF(x + width, y))


def star(p, cx, cy, radius, color=NAVY):
    points = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        q = radius if i % 2 == 0 else radius * .45
        points.append(QPointF(cx + q * math.cos(angle), cy + q * math.sin(angle)))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    p.drawPolygon(QPolygonF(points))


def fmt(value):
    return f"{value:,}".replace(",", ".")


def letters(columns):
    return ", ".join(chr(65 + c) for c in columns)


def explain(puzzle, step, previous):
    raw, r = step["message"], step["row"]
    row = r + 1
    columns = letters([c for rr, c in step["placed"] if rr == r])
    bound = step["c"][3] - (previous["c"][3] if previous else 0)
    if raw == "Start":
        return ("Khởi tạo", "Tạo các mẫu đặt sao khả thi trên từng hàng và chuẩn bị bắt đầu tìm kiếm.", "start")
    if raw == "DFS: assign row":
        return (f"Gán hàng {row}", f"DFS đi lần lượt từ trên xuống: chọn mẫu hợp lệ đầu tiên chưa thử cho hàng {row}, đặt sao ở cột {columns}, rồi xuống hàng kế tiếp.", "assign")
    if raw == "DFS: restore after backtracking":
        return (f"Quay lui hàng {row}", f"Các hàng phía dưới không còn cách đặt nào hợp lệ. DFS gỡ mẫu ở hàng {row} và thử mẫu kế tiếp của hàng này.", "back")
    if raw == "MRV: assign row; forward check":
        ds = previous["domain_sizes"] if previous else None
        left = ds[r] if ds is not None else None
        reason = (f"Trước bước này, hàng {row} chỉ còn {left} phương án, ít nhất trong các hàng chưa gán nên được xét trước. "
                  if left is not None else f"Hàng {row} được chọn theo MRV. ")
        return (f"Chọn hàng {row} (MRV)", reason + f"Đặt sao ở cột {columns}, sau đó forward checking loại các phương án xung đột ở những hàng còn lại.", "assign")
    if raw == "MRV: domain wipeout":
        return ("Có hàng hết phương án", f"Sau khi gán hàng {row}, forward checking làm một hàng chưa gán không còn phương án nào, nên lần gán này bị hủy.", "wipe")
    if raw == "MRV: restore after backtracking":
        reason = f"Gỡ mẫu vừa gán ở hàng {row} và thử phương án kế tiếp của hàng này."
        if bound > 0:
            reason += " Nhánh con vừa bị cắt vì cột hoặc vùng không thể đủ sao (capacity_possible)."
        return (f"Quay lui hàng {row}", reason, "back")
    if raw == "Solved":
        reason = f"Mọi hàng, cột và vùng đều đủ {puzzle['stars']} sao, không có hai sao kề nhau."
        if step.get("valid"):
            reason += " Python đã kiểm tra nghiệm này bằng validate_solution: hợp lệ."
        return ("Tìm thấy nghiệm", reason, "solved")
    if raw == "No solution":
        return ("Vô nghiệm", "Đã duyệt hết không gian tìm kiếm mà không có cách đặt sao nào thỏa mọi ràng buộc.", "fail")
    return raw, "", "start"


class IconButton(QPushButton):
    def __init__(self, kind, name, parent):
        super().__init__(parent)
        self.kind = kind
        self.paused = True
        self.setAccessibleName(name)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        play = self.kind == "play"
        fill = BLUE if play else ("#f2f6fc" if self.underMouse() else "#fff")
        if not self.isEnabled():
            p.setOpacity(.42)
        box(p, (1, 1, self.width()-2, self.height()-2), fill,
            BLUE if play else "#d4e1f4", 13)
        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(BLUE), 2))
            p.drawRoundedRect(QRectF(3, 3, self.width()-6, self.height()-6), 11, 11)
        p.translate((self.width()-19)/2, (self.height()-19)/2)
        p.scale(19/24, 19/24)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#fff" if play else NAVY))
        if play and not self.paused:
            p.drawRect(QRectF(7, 5, 3.6, 14))
            p.drawRect(QRectF(13.4, 5, 3.6, 14))
        elif self.kind in ("play", "forward"):
            p.drawPolygon(QPolygonF([QPointF(7, 5), QPointF(18, 12), QPointF(7, 19)]))
        elif self.kind == "back":
            p.drawPolygon(QPolygonF([QPointF(17.5, 5), QPointF(6.5, 12), QPointF(17.5, 19)]))
        elif self.kind == "first":
            p.drawRect(QRectF(6, 5, 2.5, 14))
            p.drawPolygon(QPolygonF([QPointF(20, 5), QPointF(10, 12), QPointF(20, 19)]))
        else:
            p.drawRect(QRectF(15.5, 5, 2.5, 14))
            p.drawPolygon(QPolygonF([QPointF(4, 5), QPointF(14, 12), QPointF(4, 19)]))


class Select(QComboBox):
    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(NAVY), 2, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        x, y = self.width()-20, self.height()/2
        p.drawPolyline(QPolygonF([QPointF(x-5, y-2), QPointF(x, y+3), QPointF(x+5, y-2)]))


class Page(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(420)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.puzzle_index, self.algorithm = 0, "heu"
        self.history, self.index = [], 0
        self.worker = None
        self.finished = self.playing = self.seeking_end = False
        self.pending = 0
        self.accumulator = 0.0
        self.last_tick = time.monotonic()
        self.setup_controls()
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.tick)
        self.timer.start()
        self.load()

    @property
    def puzzle(self):
        return PUZZLES[self.puzzle_index]

    @property
    def step(self):
        return self.history[self.index] if self.history else None

    def setup_controls(self):
        style = """
        QComboBox {font:700 15px 'Segoe UI'; color:#1b3358; background:#fff;
          border:1px solid #d4e1f4; border-radius:12px; padding:10px 14px;}
        QComboBox::drop-down {border:0; width:27px;}
        QComboBox QAbstractItemView {background:#fff;color:#1b3358;
          selection-background-color:#e6effc;selection-color:#2557b3;}
        """
        self.picker = Select(self)
        self.picker.setAccessibleName("Bàn cờ mẫu")
        base = [f"{p['size']}×{p['size']} · {p['stars']} sao" for p in PUZZLES]
        for p, name in zip(PUZZLES, base):
            self.picker.addItem(name + (f" ({p['name']})" if base.count(name) > 1 else ""))
        self.picker.setStyleSheet(style)
        self.picker.currentIndexChanged.connect(self.select_puzzle)
        self.speed = Select(self)
        self.speed.setAccessibleName("Tốc độ")
        self.speed.addItems([f"{n} bước/giây" for n in SPEEDS])
        self.speed.setCurrentIndex(2)
        self.speed.setStyleSheet(style.replace("15px", "13px").replace("10px 14px", "7px 12px"))
        self.tabs = {}
        for key, title in (("dfs", "DFS"), ("heu", "Heuristic")):
            button = QPushButton(title, self)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet("""QPushButton {font:700 15px 'Segoe UI';color:#5f7699;
              background:transparent;border:0;border-radius:12px;}
              QPushButton:checked {background:#fff;color:#2557b3;}
              QPushButton:focus {border:2px solid #2557b3;}""")
            button.clicked.connect(lambda checked=False, k=key: self.select_algorithm(k))
            self.tabs[key] = button
        self.slider = QSlider(Qt.Orientation.Horizontal, self)
        self.slider.setAccessibleName("Thanh tiến trình")
        self.slider.setStyleSheet("""
          QSlider::groove:horizontal {height:8px;border-radius:4px;background:#d9e5f7;}
          QSlider::sub-page:horizontal {background:#2557b3;border-radius:4px;}
          QSlider::handle:horizontal {background:white;border:3px solid #2557b3;
              width:12px;height:12px;border-radius:9px;margin:-5px 0;}
          """)
        self.slider.valueChanged.connect(self.scrub)
        self.slider.sliderPressed.connect(self.stop)
        self.buttons = {}
        for kind, name, slot in (
            ("first", "Về bước đầu", lambda: self.go(0)),
            ("back", "Bước lùi", lambda: self.go(self.index-1)),
            ("play", "Chạy", self.toggle_play),
            ("forward", "Bước tiến", self.step_forward),
            ("last", "Đến bước cuối", self.to_end),
        ):
            button = IconButton(kind, name, self)
            button.clicked.connect(slot)
            self.buttons[kind] = button

    def select_puzzle(self, value):
        self.puzzle_index = value
        self.load()

    def select_algorithm(self, key):
        self.algorithm = key
        self.load()

    def load(self):
        if self.worker:
            self.worker.cancel()
        self.picker.blockSignals(True)
        self.picker.setCurrentIndex(self.puzzle_index)
        self.picker.blockSignals(False)
        self.history, self.index = [], 0
        self.finished = self.playing = self.seeking_end = False
        self.pending = 0
        self.accumulator = 0
        for key, button in self.tabs.items():
            button.setChecked(key == self.algorithm)
        self.worker = SearchRun(self.puzzle, self.algorithm)
        self.worker.start()
        self.refresh()

    def stop(self):
        self.playing = self.seeking_end = False
        self.accumulator = 0
        if self.worker:
            self.worker.pause()
        # At most one in-flight event can still arrive, but it must not move
        # the displayed cursor after the user has paused or scrubbed.
        self.pending = 0
        self.refresh()

    def go(self, index):
        self.stop()
        if self.history:
            self.index = max(0, min(len(self.history)-1, index))
        self.refresh()

    def scrub(self, index):
        self.go(index)

    def step_forward(self):
        self.stop()
        self.advance(1)

    def advance(self, count):
        if not self.history or count < 1:
            return
        available = len(self.history)-1-self.index
        take = min(available, count)
        self.index += take
        remaining = count-take
        if remaining and not self.finished:
            # Only one batch in flight; UI polling remains bounded.
            if self.pending == 0:
                self.pending = remaining
                self.worker.advance(remaining)
        if self.finished and self.index == len(self.history)-1:
            self.playing = False
        self.refresh()

    def toggle_play(self):
        if self.playing or self.seeking_end:
            self.stop()
            return
        if self.finished and self.index == len(self.history)-1:
            self.index = 0
        self.playing = True
        self.accumulator = 0
        self.last_tick = time.monotonic()
        self.refresh()

    def to_end(self):
        self.stop()
        if self.finished:
            self.go(len(self.history)-1)
        else:
            self.seeking_end = True
            self.worker.to_end()
            self.refresh()

    def tick(self):
        now = time.monotonic()
        dt, self.last_tick = now-self.last_tick, now
        changed = False
        for _ in range(2000):
            try:
                kind, data = self.worker.events.get_nowait()
            except queue.Empty:
                break
            changed = True
            if kind == "step":
                self.history.append(data)
                if self.seeking_end or self.pending > 0:
                    self.index = len(self.history)-1
                self.pending = max(0, self.pending-1)
                if data["message"] in ("Solved", "No solution"):
                    self.finished = True
                    self.playing = self.seeking_end = False
                    self.pending = 0
            elif kind == "error":
                self.finished = True
                self.stop()
                QMessageBox.critical(self, "Star Battle", data)
        if self.playing and self.pending == 0:
            self.accumulator += min(dt, .25)*SPEEDS[self.speed.currentIndex()]
            count = int(self.accumulator)
            if count:
                self.accumulator -= count
                self.advance(count)
        if changed:
            self.refresh()

    def refresh(self):
        count = len(self.history)
        self.slider.blockSignals(True)
        self.slider.setRange(0, max(0, count-1))
        self.slider.setValue(self.index)
        self.slider.blockSignals(False)
        self.buttons["first"].setEnabled(self.index > 0)
        self.buttons["back"].setEnabled(self.index > 0)
        end = self.finished and self.index >= count-1
        for name in ("forward", "last"):
            self.buttons[name].setEnabled(bool(count) and not end)
        self.buttons["play"].setEnabled(bool(count))
        self.buttons["play"].paused = not (self.playing or self.seeking_end)
        self.buttons["play"].setAccessibleName("Dừng" if not self.buttons["play"].paused else "Chạy")
        self.buttons["play"].update()
        self.layout_page()
        self.update()

    def sizeHint(self):
        return QSize(1060, 900)

    def resizeEvent(self, event):
        self.layout_page()

    def chip_data(self):
        step = self.step
        if not step:
            return []
        chips = []
        for r in range(self.puzzle["size"]):
            cols = [c for rr, c in step["placed"] if rr == r]
            ds = step["domain_sizes"]
            if cols:
                value = f"H{r+1}: ★ {letters(cols)}"
            elif self.algorithm == "heu" and ds is not None and ds[r] is not None:
                value = f"H{r+1}: {ds[r]}"
            else:
                value = f"H{r+1}: -"
            chips.append((value, bool(cols), step["row"] == r))
        return chips

    def layout_page(self):
        if not hasattr(self, "picker"):
            return
        page_width = min(1060, self.width())
        self.left = (self.width()-page_width)/2+20
        self.content_width = page_width-40
        x, w = self.left, self.content_width
        self.narrow = self.width() <= 860
        # Same wrap breakpoint and column order as the original CSS.
        self.header_wrap = w < 626
        self.title_width = w if self.header_wrap else w-206
        self.title_height = wrapped_height("Trực quan hóa quá trình tìm kiếm", self.title_width,
                                           26 if self.narrow else 32, 39, 800)
        self.subtitle_y = 28+self.title_height+8
        self.subtitle_height = wrapped_height("So sánh DFS và Heuristic trên cùng bàn cờ Star Battle.",
                                              self.title_width, 14, 21)
        header_bottom = self.subtitle_y+self.subtitle_height
        self.picker_y = header_bottom+32 if self.header_wrap else 51
        self.picker.setGeometry(round(x if self.header_wrap else x+w-190),
                                self.picker_y, 190, 44)
        self.tabs_y = self.picker_y+66 if self.header_wrap else header_bottom+22
        tabs_h = 88 if w < 510 else 61
        self.tabs["dfs"].setGeometry(round(x+8), self.tabs_y+8, 102, 45)
        self.tabs["heu"].setGeometry(round(x+114), self.tabs_y+8, 140, 45)
        self.grid_y = self.tabs_y+tabs_h+18
        left_w = w if self.narrow else (w-18)*1.05/2.05
        self.board_rect = (x, self.grid_y, left_w, left_w-48+196)
        rx = x if self.narrow else x+left_w+18
        rw = w if self.narrow else w-left_w-18
        ry = self.grid_y + self.board_rect[3]+18 if self.narrow else self.grid_y
        iw = rw-48
        step = self.step
        self.explanation = explain(self.puzzle, step, self.history[self.index-1] if self.index else None) if step else ("", "", "start")
        desc_h = wrapped_height(self.explanation[1], iw, 14, 42)
        cap = ("Số phương án còn lại theo từng hàng, tính sau bước này:"
               if self.algorithm == "heu" else "Trạng thái từng hàng (DFS đi lần lượt từ hàng 1):")
        cap_h = wrapped_height(cap, iw, 13, 20)
        self.cap = cap
        self.desc_y, self.desc_h = ry+87, desc_h
        self.line_y = self.desc_y+desc_h+16
        self.cap_y = self.line_y+16
        cy = self.cap_y+cap_h+10
        cx = rx+24
        self.chips = []
        fm = QFontMetricsF(font(12, 700))
        for value, on, current in self.chip_data():
            cw = math.ceil(fm.horizontalAdvance(value))+22
            if cx > rx+24 and cx+cw > rx+rw-24:
                cx = rx+24
                cy += 38
            self.chips.append(((cx, cy, cw, 30), value, on, current))
            cx += cw+8
        self.metrics_y = cy+30+18
        card_h = self.metrics_y+61+22-ry
        self.current_rect = (rx, ry, rw, card_h)
        control_y = ry+card_h+18
        self.control_wrap = iw < 375
        row_h = 76 if self.control_wrap else 38
        help_text = "Dùng các nút hoặc thanh tiến trình để xem từng bước tìm kiếm. Phím ← / → để lùi / tiến và Space để chạy / dừng."
        self.help_h = wrapped_height(help_text, iw, 13)
        self.control_rect = (rx, control_y, rw, 22+17+12+row_h+20+18+22+54+33+self.help_h+22)
        self.speed.setGeometry(round(rx+rw-24-142), round(control_y+51+(38 if self.control_wrap else 0)), 142, 36)
        slider_y = control_y+51+row_h+12
        self.slider.setGeometry(round(rx+24), round(slider_y), round(iw), 26)
        by = slider_y+48
        unit = (iw-40)/5.55
        bx = rx+24
        for key in ("first", "back", "play", "forward", "last"):
            bw = unit*(1.55 if key == "play" else 1)
            self.buttons[key].setGeometry(round(bx), round(by), round(bw), 54)
            bx += bw+10
        self.control_line = by+54+16
        self.help_y = self.control_line+17
        self.control_rect = (rx, control_y, rw, self.help_y+self.help_h+22-control_y)
        self.setMinimumHeight(math.ceil(max(self.board_rect[1]+self.board_rect[3],
                                            control_y+self.control_rect[3])+48))

    def draw_board(self, p):
        x, y, w, h = self.board_rect
        step, puzzle = self.step, self.puzzle
        box(p, self.board_rect)
        text(p, (x+24, y+22, w-48, 17), "BÀN CỜ STAR BATTLE", 11, 800)
        text(p, (x+24, y+41, 130, 36), f"{puzzle['size']}×{puzzle['size']}", 30, 800, "#3a5380")
        status, fill, color = "Sẵn sàng", "#e6effc", BLUE
        if self.playing or self.seeking_end:
            status = "Đang chạy"
        elif step and step["message"] in ("Solved", "No solution"):
            solved = step["message"] == "Solved"
            status, fill, color = ("Hoàn tất", "#e0f4ea", "#1f8a5b") if solved else ("Vô nghiệm", "#fdeceb", "#b3382c")
        elif self.index > 0:
            status = "Tạm dừng"
        sw = QFontMetricsF(font(12, 700)).horizontalAdvance(status)+26
        box(p, (x+w-24-sw, y+22, sw, 28), fill, None, 14)
        text(p, (x+w-24-sw, y+22, sw, 28), status, 12, 700, color, Qt.AlignmentFlag.AlignCenter)
        bx, by, board_w = x+24, y+90, w-48
        n, k, regions = puzzle["size"], puzzle["stars"], puzzle["regions"]
        cs_original = 62 if n <= 6 else (52 if n <= 8 else 44)
        scale = board_w/(n*cs_original+6)
        cell = cs_original*scale
        bx, by = bx+3*scale, by+3*scale
        labels = sorted({g for row in regions for g in row})
        for r in range(n):
            for c in range(n):
                g = regions[r][c]
                xx, yy = bx+c*cell, by+r*cell
                p.setPen(QPen(QColor("#fff"), 1.2*scale))
                p.setBrush(QColor(PAL[labels.index(g) % len(PAL)]))
                p.drawRect(QRectF(xx, yy, cell, cell))
                p.setOpacity(.9)
                text(p, (xx+6*scale, yy+1*scale, cell-6*scale, 17*scale),
                     str(g), max(1, round(11*scale)), 700, "#35507a")
                p.setOpacity(1)
        if step and step["row"] >= 0:
            p.setPen(QPen(QColor("#e8a317"), 2.5*scale))
            p.setBrush(QColor(255, 190, 50, 66))
            p.drawRoundedRect(QRectF(bx+1.5*scale, by+step["row"]*cell+1.5*scale,
                                     n*cell-3*scale, cell-3*scale), 4*scale, 4*scale)
        p.setPen(QPen(QColor("#1e3a66"), 2.6*scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for r in range(n):
            for c in range(n):
                if c+1 < n and regions[r][c] != regions[r][c+1]:
                    p.drawLine(QPointF(bx+(c+1)*cell, by+r*cell), QPointF(bx+(c+1)*cell, by+(r+1)*cell))
                if r+1 < n and regions[r][c] != regions[r+1][c]:
                    p.drawLine(QPointF(bx+c*cell, by+(r+1)*cell), QPointF(bx+(c+1)*cell, by+(r+1)*cell))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor("#1e3a66"), 3*scale))
        p.drawRoundedRect(QRectF(bx, by, n*cell, n*cell), 7*scale, 7*scale)
        placed = step["placed"] if step else []
        for r, c in placed:
            star(p, bx+(c+.5)*cell, by+(r+.5)*cell, cell*.33)
        ly = y+90+board_w+16
        line(p, x+24, ly, w-48)
        star(p, x+32, ly+24, 7)
        text(p, (x+48, ly+14, 35, 20), "Sao", 13, 400, INK)
        box(p, (x+107, ly+16, 18, 16), "#fff3d1", "#e8a317", 4, 2)
        text(p, (x+133, ly+14, w-157, 20), "Hàng đang xét", 13, 400, INK)
        done = sum(sum(regions[r][c] == g for r, c in placed) == k for g in labels)
        text(p, (x+24, ly+48, w-48, 20), f"{done} / {n} vùng hoàn thành", 13, 600, INK)
        text(p, (x+24, ly+48, w-48, 20), f"{len(placed)} / {n*k} sao", 13, 800,
             NAVY, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(BG))
        x, w = self.left, self.content_width
        text(p, (x, 28, self.title_width, self.title_height), "Trực quan hóa quá trình tìm kiếm", 26 if self.narrow else 32, 800,
             NAVY, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, True)
        text(p, (x, self.subtitle_y, self.title_width, self.subtitle_height), "So sánh DFS và Heuristic trên cùng bàn cờ Star Battle.", 14, 400, MUTE,
             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, True)
        text(p, (x if self.header_wrap else x+w-190, self.picker_y-23, 190, 17), "BÀN CỜ MẪU", 11, 800)
        tabs_h = 88 if w < 510 else 61
        box(p, (x, self.tabs_y, w, tabs_h), "#e8eff9", None, 16)
        rule = f"{self.puzzle['stars']} sao / hàng, cột, vùng"
        rule_rect = (x+20, self.tabs_y+58, w-40, 20) if w < 510 else (x+270, self.tabs_y+20, w-290, 20)
        text(p, rule_rect, rule, 12, 700, INK, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.draw_board(p)
        rx, ry, rw, rh = self.current_rect
        iw = rw-48
        box(p, self.current_rect)
        pos = f"{self.index+1} / {len(self.history)}" if self.history else "0 / 0"
        text(p, (rx+24, ry+22, iw, 17), "BƯỚC HIỆN TẠI", 11, 800)
        text(p, (rx+24, ry+22, iw, 20), pos, 15, 700, NAVY,
             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        title, description, kind = self.explanation
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(DOT[kind]))
        p.drawEllipse(QRectF(rx+24, ry+64, 10, 10))
        text(p, (rx+44, ry+55, iw-20, 27), title, 21, 800)
        text(p, (rx+24, self.desc_y, iw, self.desc_h), description, 14, 400, MUTE,
             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, True)
        line(p, rx+24, self.line_y, iw)
        text(p, (rx+24, self.cap_y, iw, self.metrics_y-self.cap_y), self.cap, 13, 400, MUTE,
             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, True)
        for rect, value, on, current in self.chips:
            fill = "#fff3d1" if current else ("#d7e5fb" if on else "#eaf1fb")
            box(p, rect, fill, "#e8a317" if current else "#d4e1f4", 9)
            text(p, rect, value, 12, 700, NAVY if current or on else INK, Qt.AlignmentFlag.AlignCenter)
        counters = self.step["c"] if self.step else [0, 0, 0, 0]
        values = [counters[0], counters[2], counters[3] if self.algorithm == "heu" else counters[1]]
        names = ["NÚT DUYỆT", "QUAY LUI", "CẮT NHÁNH" if self.algorithm == "heu" else "QUYẾT ĐỊNH"]
        mw = (iw-20)/3
        for i, (value, name) in enumerate(zip(values, names)):
            mx = rx+24+i*(mw+10)
            box(p, (mx, self.metrics_y, mw, 61), "#f2f6fc", None, 12)
            text(p, (mx+12, self.metrics_y+7, mw-24, 25), fmt(value), 19, 800)
            text(p, (mx+12, self.metrics_y+34, mw-24, 17), name, 11, 700, MUTE)
        cx, cy, cw, ch = self.control_rect
        box(p, self.control_rect)
        text(p, (cx+24, cy+22, cw-48, 17), "ĐIỀU KHIỂN THUẬT TOÁN", 11, 800)
        text(p, (cx+24, cy+51, iw if self.control_wrap else iw-204, 36), f"Bước {pos}", 19, 800, "#3a5380")
        text(p, (cx+cw-24-204, cy+51+(38 if self.control_wrap else 0), 54, 36), "Tốc độ", 13, 700, INK)
        line(p, cx+24, self.control_line, iw)
        text(p, (cx+24, self.help_y, iw, self.help_h),
             "Dùng các nút hoặc thanh tiến trình để xem từng bước tìm kiếm. Phím ← / → để lùi / tiến và Space để chạy / dừng.",
             13, 400, MUTE, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, True)

    def shutdown(self):
        self.timer.stop()
        if self.worker:
            self.worker.cancel()
            self.worker.join(timeout=1)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Star Battle: trực quan hóa quá trình tìm kiếm")
        self.page = Page()
        scroll = QScrollArea()
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.page)
        scroll.setStyleSheet("QScrollArea {background:#f6f9fd; border:0;}")
        self.setCentralWidget(scroll)
        self.resize(1080, 940)
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Type.KeyPress and self.isActiveWindow():
            key = event.key()
            if key == Qt.Key.Key_Left:
                self.page.go(self.page.index-1)
            elif key == Qt.Key.Key_Right:
                self.page.step_forward()
            elif key == Qt.Key.Key_Home:
                self.page.go(0)
            elif key == Qt.Key.Key_End:
                self.page.to_end()
            elif key == Qt.Key.Key_Space:
                if isinstance(QApplication.focusWidget(), (QComboBox, QPushButton)):
                    return False
                self.page.toggle_play()
            else:
                return False
            return True
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        self.page.shutdown()
        QApplication.instance().removeEventFilter(self)
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(font(15))
    window = Window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
