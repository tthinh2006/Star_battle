# Star Battle

Bài tập lớn 1 – Tìm kiếm (Nhập môn Trí tuệ Nhân tạo, CO3061). Chương trình giải
**Star Battle** bằng hai thuật toán, viết bằng Python 3, có giao diện trực quan
hóa từng bước bằng PySide6:

- **DFS** (blind search): gán lần lượt từng hàng, từ trên xuống, quay lui khi vi phạm ràng buộc.
- **Heuristic**: quay lui kết hợp MRV, Forward Checking và kiểm tra cận số sao của cột/vùng.

**Luật chơi:** bàn `N × N` chia thành `N` vùng; đặt đúng `k` sao trên mỗi hàng,
mỗi cột và mỗi vùng; hai sao không được chạm nhau (kể cả chéo).

## 1. Cài đặt

Yêu cầu Python ≥ 3.10. Chạy trong thư mục gốc của project:

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install PySide6
```

> macOS/Linux: thay `py -3` bằng `python3` và `.venv\Scripts\python` bằng `.venv/bin/python`.
>
> Các thuật toán chỉ dùng thư viện chuẩn; PySide6 chỉ cần cho visualizer.

## 2. Chạy test (đo thời gian và bộ nhớ)

Chạy cả hai thuật toán trên 6 puzzle trong `test/star_battle/`:

```powershell
.venv\Scripts\python run_benchmark.py
```

Hoặc chạy riêng một file:

```powershell
.venv\Scripts\python run_benchmark.py test/star_battle/10x10_2stars.txt
```

Mỗi dòng kết quả gồm thời gian (ms) và bộ nhớ đỉnh (KB, đo bằng `tracemalloc`)
của DFS và Heuristic. Giới hạn mỗi lần chạy là 120 giây; nếu thuật toán không trả
về lời giải, chương trình in thêm dòng `no solution returned`.

## 3. Mở visualizer

```powershell
.venv\Scripts\python visualizer.py
```

1. Chọn puzzle ở mục **BÀN CỜ MẪU** (5×5 → 10×10, 1 hoặc 2 sao).
2. Chọn thuật toán ở tab **DFS** hoặc **Heuristic**.
3. Dùng **ĐIỀU KHIỂN THUẬT TOÁN**:

| Nút | Chức năng |
| --- | --- |
| ⏮ / ⏭ | Về bước đầu / chạy đến khi xong |
| ◀ / ▶ | Lùi / tiến một bước |
| Play / Pause | Chạy tự động / tạm dừng |
| Thanh trượt | Xem lại các bước đã chạy |
| Tốc độ | 1 → 1000 bước/giây |

Phím tắt: **← / →** lùi/tiến, **Home / End** đầu/cuối, **Space** chạy/dừng.

Bàn cờ hiển thị các vùng màu, sao đã đặt, hàng đang xét (tô vàng). Mục **BƯỚC
HIỆN TẠI** giải thích bước hiện tại (gán hàng, quay lui, domain rỗng, tìm được
lời giải…) cùng các bộ đếm **NÚT DUYỆT**, **QUAY LUI** và **QUYẾT ĐỊNH** (DFS)
hoặc **CẮT NHÁNH** (Heuristic). Đổi puzzle hoặc thuật toán sẽ chạy lại từ đầu.

## 4. Cấu trúc project

```text
core.py               # Kiểm tra input, sinh mẫu hàng (RowModel), trạng thái tìm kiếm, thống kê
blind_search.py       # Thuật toán DFS
heuristic_search.py   # Thuật toán Heuristic: MRV + Forward Checking + kiểm tra cận
visualizer.py         # Giao diện PySide6 (puzzle mẫu nhúng sẵn, chạy thuật toán trên thread riêng)
run_benchmark.py      # Chạy test, đo thời gian và bộ nhớ của hai thuật toán
utils.py              # Hàm measure(): đo thời gian, bộ nhớ, giới hạn 120 giây
test/star_battle/     # 6 puzzle test (.txt)
```

**Ý tưởng chung:** mỗi **hàng là một biến**, giá trị là một mẫu gồm `k` vị trí sao
không kề nhau. Gán một hàng là đặt cả `k` sao của hàng đó, nên ràng buộc hàng luôn
đúng; chỉ cần kiểm tra cột, vùng và sao kề nhau giữa hai hàng liên tiếp.

- **DFS** xét hàng theo thứ tự cố định 0 → N−1, thử các mẫu hợp lệ lần lượt.
- **Heuristic** chọn hàng còn ít mẫu hợp lệ nhất (MRV); sau mỗi lần gán thì lọc
  mẫu của các hàng còn lại (Forward Checking) và cắt nhánh nếu một hàng hết mẫu
  hoặc các hàng còn lại không thể đủ/vượt số sao của cột/vùng.

## 5. Định dạng file test

Dòng đầu: `N k` (kích thước bàn, số sao mỗi hàng/cột/vùng). `N` dòng tiếp theo là
mã vùng của từng ô:

```text
5 1
0 0 1 1 1
1 1 1 1 1
1 1 2 4 4
3 3 2 4 4
3 3 2 4 4
```

Các ô cùng vùng phải liền nhau theo cạnh; `validate_puzzle()` trong `core.py` báo
`ValueError` nếu input sai.

## 6. Quy ước thống kê

| Trường | Ý nghĩa |
| --- | --- |
| `nodes` | số lần gọi hàm đệ quy `dfs()` / `heuristic()` (tính cả gốc) |
| `decisions` | số lần thử gán một mẫu cho một hàng |
| `backtracks` | số lần gán bị hủy vì nhánh con thất bại |
| `max_depth` | số hàng đã gán lớn nhất |
| `domain_values_removed` | số mẫu bị loại bởi Forward Checking (chỉ Heuristic) |
| `bound_failures` | số nhánh bị cắt do kiểm tra cận cột/vùng (chỉ Heuristic, hiển thị là **CẮT NHÁNH**) |

Thời gian chạy animation trong visualizer không phải thời gian của thuật toán;
số liệu cho báo cáo lấy từ `run_benchmark.py`.
