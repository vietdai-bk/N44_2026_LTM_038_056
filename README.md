# Cấp phát tài nguyên cho mạng nhiều UAV làm trạm gốc có ưu tiên người dùng

Đồ án môn Lập trình mạng. Nhiều UAV mang trạm gốc LTE bay tới vùng thiên tai để phát sóng cho người dùng mặt đất.
Người dùng chia thành ba nhóm ưu tiên: **normal** (người dân), **important** (điều phối, camera) và **critical** (đội
cứu hộ, y tế). Mỗi giây, hệ thống phải quyết định người dùng nối với UAV nào, mỗi người được bao nhiêu băng thông, và
UAV bay về đâu.

Nhóm xây dựng heuristic **calib-ifair**: ưu tiên nhóm critical mà không bỏ rơi các nhóm khác. Khác với các bài báo chỉ
tính bằng công thức Shannon, mọi kết quả ở đây được **đo lại ở mức gói tin bằng NS-3 LTE** (eNB bay, handover, UDP thật).

![Ba thuật toán chạy trên cùng một kịch bản; hình thoi viền đỏ là người dùng critical](experiments/results/anim_classes.gif)

## Kết quả chính

Đo bằng NS-3 LTE: 3 UAV, 20 người dùng (3 critical, 5 important, 12 normal), lưu lượng 4 Mbps mỗi người, trung bình
3 seed.

| | kmeans-equal | kmeans-wmaxmin (cũng biết nhóm) | **calib-ifair** |
|---|---|---|---|
| Người dùng critical đạt chất lượng dịch vụ | 69% | 86% | **96%** |
| Tốc độ tối thiểu nhóm critical | 1.64 Mbps | 2.79 Mbps | **3.25 Mbps** |
| Tốc độ tối thiểu nhóm normal | 0.68 Mbps | 0.49 Mbps | **0.95 Mbps** |
| Throughput tổng | **49.9 Mbps** | 44.3 Mbps | 44.1 Mbps |

- calib-ifair ưu tiên được nhóm critical, kể cả so với baseline max-min có trọng số cùng biết nhóm người dùng.
- Đổi lại, throughput tổng ở tải cao thấp hơn khoảng 11% so với baseline không biết nhóm. Đây là đánh đổi có chủ đích.
- Mô hình khớp NS-3 với liên kết lý tưởng dưới 1% (105 lần chạy). Trên LTE thật, tốc độ chỉ bằng 25–40% con số
  Shannon mà các bài báo dùng.

## Thuật toán calib-ifair

Mỗi khe thời gian, heuristic làm ba bước rồi áp quyết định xuống tầng MAC:

1. **Liên kết và SINR có nhiễu:** người dùng nối UAV có kênh mạnh nhất; SINR tính cả nhiễu từ các UAV khác.
2. **Chia băng (ifair):** b<sub>k</sub> ∝ w<sub>k</sub> / ŜE<sub>k</sub>, với trọng số w = 1 / 2 / 4 theo nhóm. Trong
   mỗi UAV, người dùng critical được tốc độ gấp 4 lần người dùng normal
   (khi hiệu suất phổ không thấp hơn sàn 0.05 bit/s/Hz).
3. **Di chuyển (calib):** UAV bay về tâm cụm người dùng, rồi thử 17 nước đi và giữ nước làm tăng Σ w·log(tốc độ).
4. **Áp ở tầng MAC:** b<sub>k</sub> làm trọng số cho scheduler Weighted PF viết thêm trong NS-3.

Công thức, mã giả và lưu đồ: [`docs/THUAT_TOAN_DE_XUAT.md`](docs/THUAT_TOAN_DE_XUAT.md).

## Kiến trúc

![Kiến trúc tổng thể](docs/figures/kien_truc.png)

- **`uavsim` (Python):** mô hình kênh, SINR, hàng đợi, năng lượng bay; các thuật toán; môi trường học tăng cường.
- **NS-3 3.47 LTE (C++):** phát lại kế hoạch của thuật toán và đo throughput, độ trễ, mất gói từng người dùng.
- **Dashboard web và Gazebo:** điều khiển và quan sát thời gian thực, đo NS-3 ngay từ trình duyệt.

## Trạm điều khiển thời gian thực

Dashboard web nhận trạng thái mô hình qua WebSocket mỗi khe 0.25 s. Bản đồ vẽ UAV, người dùng (tròn: normal, vuông:
important, thoi: critical; dấu × khi dưới ngưỡng QoS) và liên kết; hai bên là danh sách UAV, lái tay, tham số kịch bản,
bảng theo nhóm người dùng và bảng từng người dùng.

![Dashboard chạy calib-ifair với 3 UAV, 20 người dùng](docs/figures/dashboard.png)

| Nền bản đồ SINR, người dùng tô theo SINR | "Ghi & đo": chạy NS-3 ngay từ web |
|---|---|
| ![Bản đồ SINR](docs/figures/dashboard_sinr.png) | ![Kết quả NS-3 trên dashboard](docs/figures/dashboard_ns3.png) |
| Lớp nền là SINR tốt nhất tại mỗi điểm, tính có nhiễu từ các UAV khác. | Ghi 10 s rồi phát lại trong NS-3: mô hình 20.00 Mbps, NS-3 đo 19.99 Mbps. |

| Đổi kịch bản khi đang chạy: 5 UAV, 40 người dùng |
|---|
| ![Dashboard với 5 UAV, 40 người dùng](docs/figures/dashboard_5uav.png) |
| Bấm "Áp dụng" là kịch bản dựng lại từ khe 0; Gazebo cập nhật theo mà không cần khởi động lại. |

## Mô phỏng 3D trong Gazebo

Gazebo hiển thị đúng kịch bản của mô hình trên một bãi thảm họa, tỷ lệ 1 m Gazebo = 10 m mô hình. Vị trí UAV và người
dùng được gửi sang 20 lần mỗi giây qua gz-transport và khớp mô hình (lệch 0.000 m). Gazebo chỉ hiển thị, không ảnh hưởng
số liệu.

![Toàn cảnh world Gazebo: 3 UAV X500 bay trên bãi thảm họa, 20 người dùng](docs/figures/gazebo.png)

| Cận cảnh UAV và ba nhóm người dùng | Cách đọc |
|---|---|
| ![UAV X500 và người dùng](docs/figures/gazebo_x500_closeup.png) | **UAV:** quadrotor X500, cánh quạt quay, màu cánh trùng màu UAV trên dashboard.<br><br>**Người dùng:** áo mang màu của UAV đang phục vụ, áo đỏ khi không được phục vụ.<br><br>**Nhóm:** không vòng là normal, vòng vàng là important, vòng đỏ là critical.<br><br>Kích thước UAV và người được phóng to để nhìn rõ trên bản đồ 1:10; vị trí vẫn đúng tỷ lệ. |

## Cài đặt

Yêu cầu: Ubuntu 22.04, Python 3.10, NS-3 3.47 có module `lte`. Gazebo Harmonic chỉ cần khi muốn xem 3D.

```bash
git clone https://github.com/vietdai-bk/uav-bs-resource-allocation.git
cd uav-bs-resource-allocation
python3 -m venv .venv                  # thêm --system-site-packages nếu dùng Gazebo
.venv/bin/pip install -r requirements.txt

# đưa kịch bản NS-3 vào thư mục NS-3 rồi build
ns3/install.sh <thư-mục-ns-3.47>
```

## Chạy nhanh

```bash
# so sánh thuật toán trên mô hình
.venv/bin/python -m uavsim.run

# đo bằng NS-3 LTE, có ba nhóm người dùng
.venv/bin/python -m uavsim.ns3 --algos kmeans-wmaxmin calib-ifair --scheduler wpf \
    --set slots=60 --set demand_mbps=2 --set important_frac=0.25 --set critical_frac=0.15

# dashboard thời gian thực tại http://localhost:8000 (bỏ --gazebo nếu không có Gazebo)
.venv/bin/python -m uavsim.live --gazebo

# kiểm thử
.venv/bin/python -m pytest -q tests
```

Mọi tham số, lệnh tái lập từng thí nghiệm và kết quả chi tiết: [`docs/HUONG_DAN_CHAY.md`](docs/HUONG_DAN_CHAY.md).

## Cấu trúc thư mục

```
uavsim/              mô hình, thuật toán, dashboard, kết nối NS-3 và Gazebo
ns3/scratch/uav_lte/ kịch bản NS-3 LTE và scheduler Weighted PF
experiments/         script vẽ biểu đồ, kết quả các thí nghiệm (results/)
tests/               46 test tự động
docs/                báo cáo, thiết kế, thuật toán, hướng dẫn, sơ đồ draw.io
slides/              slide bảo vệ (LaTeX Beamer)
```

## Tài liệu

| Tài liệu | Nội dung |
|---|---|
| [`docs/THUAT_TOAN_DE_XUAT.md`](docs/THUAT_TOAN_DE_XUAT.md) | Bài toán tối ưu, mã giả, lưu đồ của calib-ifair |
| [`docs/MO_TA_DU_AN.md`](docs/MO_TA_DU_AN.md) | Mô tả ngắn toàn dự án |
| [`docs/THIET_KE_MO_PHONG.md`](docs/THIET_KE_MO_PHONG.md) | Thiết kế mô phỏng, công thức, thông số |
| [`docs/HUONG_DAN_CHAY.md`](docs/HUONG_DAN_CHAY.md) | Hướng dẫn chạy chi tiết, kết quả từng thí nghiệm |
| [`docs/TAI_LAP_KET_QUA.md`](docs/TAI_LAP_KET_QUA.md) | Tái lập trên máy khác và so với số chuẩn |
| [`slides/main.pdf`](slides/main.pdf) | Slide bảo vệ |

## Hạn chế

calib-ifair là heuristic nên không đảm bảo nghiệm tối ưu. Thí nghiệm mới dùng một cấu hình (3 UAV, 20 người dùng, đô
thị) với 3 seed; NS-3 phát lại kế hoạch chứ chưa chạy vòng kín với thuật toán. Chi tiết ở mục 7.2 của báo cáo.
