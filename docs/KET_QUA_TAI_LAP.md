# Đối chiếu tái lập kết quả

Cập nhật: 2026-11-17 17:12:26+0700.

Trạng thái: **Hoàn tất**. Bước hiện tại: `complete`.

Đối chiếu trực tiếp mục 6 của `TAI_LAP_KET_QUA.md`: 167 chỉ số E1–E7/E10/E11; 167 trùng, 0 khác, 0 chưa có.

E8 và E9 được tài liệu loại khỏi phép so tự động. E12 phụ thuộc phần cứng và thời điểm đo; đánh giá riêng nhịp trạng thái, kích thước bản tin và độ trễ.

| Nhóm | Số chỉ số | Trùng | Khác | Chưa có |
|---|---:|---:|---:|---:|
| E1 | 12 | 12 | 0 | 0 |
| E2 | 18 | 18 | 0 | 0 |
| E4 | 22 | 22 | 0 | 0 |
| E5 | 15 | 15 | 0 | 0 |
| E6 | 6 | 6 | 0 | 0 |
| E7 | 1 | 1 | 0 | 0 |
| E10 | 45 | 45 | 0 | 0 |
| E11 | 48 | 48 | 0 | 0 |
| E12 | 15 | 9 | 6 | 0 |

## Điều chỉnh lệnh E3 để đúng cấu hình gốc

Ba lệnh E3 trong tài liệu thiếu `--set slots=30`. `SimConfig.slots` mặc định là 200, trong khi cả ba `config.json` kết quả gốc ghi `slots: 30`. Lần tái lập này thêm `--set slots=30` cho E3 A/B/C. Các tham số thí nghiệm còn lại theo tài liệu; chỉ đổi đường dẫn đầu ra sang `.local-run/reproduction/results` và dùng một luồng BLAS cho mỗi tiến trình.

Kết quả mới độc lập với `experiments/results` của máy gốc. Các script tổng hợp E10/E11 được nạp với biến đường dẫn `R` trỏ tới kết quả mới; không thay đổi thuật toán hoặc cách tính chỉ số.

## Chỉ số khác số chuẩn

Không có sai khác trong các chỉ số tất định đã hoàn tất.

## E12: WebSocket

| Client | Byte/trạng thái | Bản tin/giây | Khoảng cách TB (ms) | RTT p95 (ms) |
|---:|---:|---:|---:|---:|
| 1 | 1742 | 4.05 | 250.8 | 1.16 |
| 5 | 1739 | 4 | 250.9 | 2.766 |
| 10 | 1735 | 4 | 250.8 | 1.508 |
| 20 | 1732 | 4 | 250.9 | 2.615 |
| 50 | 1733 | 4 | 250.9 | 1.374 |

Nhịp đếm có thể là 4,05 thay vì 4,00 trong cửa sổ 20 giây do một bản tin sát biên cửa sổ; khoảng cách giữa trạng thái được ghi kèm để kiểm tra nhịp thực tế. Giá trị E12 không dùng để kết luận sai khác thuật toán.

## Lệnh và bằng chứng

- `.local-run/reproduction/commands.json`: toàn bộ lệnh thực tế.
- `.local-run/reproduction/status.json`: thời gian và mã thoát từng bước.
- `.local-run/reproduction/logs/`: log riêng cho từng thí nghiệm.
- `.local-run/reproduction/results/`: CSV, kế hoạch, log NS-3 và hình mới.
- `.local-run/reproduction/environment.json`: môi trường, commit và SHA-256 binary NS-3.
- `.local-run/reproduction/document-reference.txt`: số chuẩn trích từ tài liệu.
- `.local-run/reproduction/new.txt`: các số đo tổng hợp mới.
- `.local-run/reproduction/comparison.csv`: đối chiếu toàn bộ chỉ số.
- `.local-run/reproduction/comparison.diff`: khác biệt so với mục 6.

Tổng thời gian các bước: 110.3 phút.

## Kiểm tra dữ liệu gói tin

513/513 lượt NS-3 kết thúc thành công. 513/513 file `ns3_slots.csv` trùng toàn bộ giá trị từng hàng với bản gốc, bao gồm các lượt đo đường cong liên kết E4.

Chi tiết: `.local-run/reproduction/all-packet-comparison.json`.

## Một số kết quả chính đã tái lập

| Chỉ số | Chuẩn | Chạy lại |
|---|---:|---:|
| E4 lte_alpha | 0.4010 | 0.4010 |
| E4 lte_se_max | 3.5137 | 3.5137 |
| E7 sai số throughput lớn nhất | 0.00019 | 0.00019 |
| E11 calib-ifair, 4 Mbps/user: critical đạt QoS | 0.957 | 0.957 |
| E11 calib-ifair, 4 Mbps/user: min critical (Mbps) | 3.252 | 3.252 |
| E11 calib-ifair, 4 Mbps/user: min normal (Mbps) | 0.952 | 0.952 |
| E11 calib-ifair, 4 Mbps/user: throughput tổng (Mbps) | 44.13 | 44.13 |
