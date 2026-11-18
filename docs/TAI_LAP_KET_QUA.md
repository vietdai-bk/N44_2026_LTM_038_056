# Tái lập và so sánh kết quả trên máy khác

Tài liệu này ghi môi trường, lệnh chạy và **con số chuẩn** của mọi thí nghiệm trong báo cáo (E1–E12), để chạy lại trên
một máy khác rồi so từng con số. Số chuẩn lấy từ máy gốc, commit `3cae652` (17/11/2026).

## 1. Môi trường của máy gốc

| Thành phần | Phiên bản |
|---|---|
| Hệ điều hành | Ubuntu 22.04.5 LTS |
| CPU | Intel Core i5-11400H, 12 luồng |
| Python | 3.10.12 |
| numpy / matplotlib / gymnasium / websockets | 2.2.6 / 3.9.4 / 1.0.0 / 16.1.1 |
| NS-3 | 3.47, profile default, có module `lte`, đặt ở `~/simulation/ns-3.47` |
| Gazebo | Sim 8.15.0 (Harmonic), chỉ cần cho phần hiển thị, không ảnh hưởng số liệu |

Mô hình và NS-3 đều **tất định**: cùng phiên bản, cùng seed thì ra cùng số đến từng bit (đã kiểm tra bằng cách chạy lại
E10, E11 trên máy gốc). Số luồng chạy song song (`--parallel`) không làm đổi kết quả.

## 2. Cài đặt

```bash
git clone https://github.com/vietdai-bk/uav-bs-resource-allocation.git LapTrinhMang
cd LapTrinhMang
python3 -m venv .venv                      # thêm --system-site-packages nếu dùng Gazebo
.venv/bin/pip install -r requirements.txt
ns3/install.sh ~/simulation/ns-3.47        # symlink kịch bản uav_lte vào NS-3 rồi build
.venv/bin/python -m pytest -q tests        # phải ra: 46 passed
```

NS-3 ở chỗ khác thì đặt biến môi trường `NS3_DIR` trước khi chạy `uavsim.ns3`.

## 3. Lưu số chuẩn trước khi chạy

Thư mục `experiments/results/` trong git đã chứa kết quả của máy gốc. Lưu số chuẩn **trước** khi chạy lại (các lệnh dưới
sẽ ghi đè vào đúng các thư mục đó):

```bash
.venv/bin/python experiments/check_reproduce.py > ref.txt
```

`ref.txt` phải trùng với mục 6 của tài liệu này.

## 4. Chạy lại các thí nghiệm

Chạy từ thư mục dự án. Đặt `P=.venv/bin/python`. Thời gian đo trên máy gốc với `--parallel 10`; máy ít nhân hơn thì
giảm `--parallel` và chờ lâu hơn.

```bash
P=.venv/bin/python
R=experiments/results
L="--load 0.5 1 1.5 2 2.5 3 4 --seeds 3 --set slots=60 --set demand_mbps=1 --parallel 10"

# E1: mô hình, 6 thuật toán, 200 khe, 3 seed (vài giây)
$P -m uavsim.run --algos hover-equal hover-maxmin kmeans-equal kmeans-maxmin random-equal random-maxmin --out $R/demo

# E2: NS-3 LTE theo tải, 90 run (khoảng 36 phút)
$P -m uavsim.ns3 --algos hover-equal kmeans-equal kmeans-maxmin --load 0.5 0.6 0.7 0.8 0.9 1.0 --seeds 5 \
    --set slots=60 --parallel 10 --out $R/ns3-matrix

# E3: tách nhiễu, có trace PHY/MAC (khoảng 10 phút)
$P -m uavsim.ns3 --algos kmeans-equal --load 1 --seeds 3 --traces --out $R/ns3-interference/A_3uav_chung_tan_so
$P -m uavsim.ns3 --algos kmeans-equal --load 1 --seeds 3 --traces --set interference=false --out $R/ns3-interference/B_3uav_tan_so_rieng
$P -m uavsim.ns3 --algos kmeans-equal --load 1 --seeds 3 --traces --set num_uavs=1 --out $R/ns3-interference/C_1uav

# E4: đường cong một liên kết, hiệu chỉnh, phân rã (vài phút; cần E2 và E3)
$P -m uavsim.validate --glob '*_load1_seed*' --runs $R/ns3-interference/A_3uav_chung_tan_so \
    $R/ns3-interference/B_3uav_tan_so_rieng $R/ns3-interference/C_1uav $R/ns3-matrix

# E5, E6: lưu lượng 0.5–4 Mbps/user, LTE (khoảng 30 + 20 phút)
$P -m uavsim.ns3 --algos hover-equal kmeans-equal kmeans-maxmin --link lte $L --out $R/ns3-demand-lte
$P -m uavsim.ns3 --algos hover-maxmin kmeans-maxmin --scheduler wpf --link lte $L --out $R/ns3-demand-wpf-lte

# E7: cùng kế hoạch với liên kết lý tưởng (vài phút)
$P -m uavsim.ns3 --algos hover-equal kmeans-equal kmeans-maxmin --link ideal $L --out $R/ns3-demand-ideal
$P -m uavsim.ns3 --algos hover-maxmin kmeans-maxmin --scheduler wpf --link ideal $L --out $R/ns3-demand-wpf-ideal

# E10: thuật toán đề xuất và hai bản tách thành phần (khoảng 40 phút + vài phút)
$P -m uavsim.ns3 --algos calib-ifair kmeans-ifair calib-equal --scheduler wpf --link lte $L --out $R/ns3-proposed-lte
$P -m uavsim.ns3 --algos calib-ifair kmeans-ifair calib-equal --scheduler wpf --link ideal $L --out $R/ns3-proposed-ideal
$P experiments/compare_proposed.py $R/proposed

# E11: ba nhóm user (khoảng 35 phút)
C="--set important_frac=0.25 --set critical_frac=0.15"
$P -m uavsim.ns3 --algos calib-ifair calib-ifair-shannon --scheduler wpf --link lte $L $C --out $R/ns3-classes-lte
$P -m uavsim.ns3 --algos kmeans-wmaxmin --scheduler wpf --link lte $L $C --out $R/ns3-wmaxmin-lte
$P experiments/compare_classes.py $R/classes

# E12: hiệu năng server WebSocket (khoảng 2 phút; cổng 8100–8101 phải trống)
$P experiments/bench_websocket.py $R/websocket
```

Tổng cộng khoảng 3–4 giờ với 12 luồng. E8 (thời gian chạy) và E9 (điều khiển thời gian thực) phụ thuộc phần cứng, có
Gazebo, nên không nằm trong phép so tự động; cách đo ở mục 6.9–6.10 của báo cáo.

## 5. So sánh

```bash
.venv/bin/python experiments/check_reproduce.py > new.txt
diff ref.txt new.txt && echo "Trùng khớp hoàn toàn"
git diff --stat experiments/results          # xem file kết quả nào đã đổi
```

Cách đọc kết quả `diff`:

| Nhóm số | Kỳ vọng | Nếu lệch |
|---|---|---|
| E1–E7, E10, E11 | Trùng từng chữ số khi cùng phiên bản Python, numpy, NS-3 | Kiểm tra phiên bản trước. Khác numpy hoặc khác NS-3 có thể làm lệch ở chữ số cuối; lệch quá 2–3% là bất thường |
| E4 `lte_alpha`, `lte_se_max` | 0.4010 và 3.5137 | Hai hằng số này đo từ NS-3 LTE; lệch nghĩa là bản NS-3 hoặc cấu hình LTE khác |
| E7 sai số ba tầng | Dưới 0.001 | Lớn hơn nghĩa là đường ống xuất kế hoạch hoặc mô hình hàng đợi có vấn đề |
| E12 `state_bytes`, `state_per_s` | Khoảng 1730 byte, đúng 4.00 bản tin/giây | `state_per_s` thấp hơn 4 nghĩa là máy không theo kịp nhịp khe 0.25 s |
| E12 `rtt_ms_p95` | Phụ thuộc máy | Không cần trùng; chỉ cần nhỏ hơn nhiều so với 250 ms |

`git diff` trên các file `ns3.log` luôn có khác biệt vì chúng ghi thời gian chạy (`wall=…s`); bỏ qua các file này.

## 6. Số chuẩn của máy gốc

Đầu ra của `experiments/check_reproduce.py` trên máy gốc. Đơn vị: Mbps cho tốc độ, ms cho độ trễ; `delivered`,
`ns3_loss`, `sat_critical` là tỷ lệ (0–1); `min_gain` là mức tăng tương đối (0.18 = +18%).

```text
Thư mục kết quả: experiments/results

# E1 mô hình
E1 hover-equal sum_rate_mbps                 = 87.4
E1 hover-equal min_rate_mbps                 = 0.71
E1 hover-maxmin sum_rate_mbps                = 76.1
E1 hover-maxmin min_rate_mbps                = 0.84
E1 kmeans-equal sum_rate_mbps                = 144.6
E1 kmeans-equal min_rate_mbps                = 1.85
E1 kmeans-maxmin sum_rate_mbps               = 142.8
E1 kmeans-maxmin min_rate_mbps               = 1.90
E1 random-equal sum_rate_mbps                = 96.7
E1 random-equal min_rate_mbps                = 1.01
E1 random-maxmin sum_rate_mbps               = 88.7
E1 random-maxmin min_rate_mbps               = 1.25

# E2 NS-3 theo tải
E2 hover-equal load0.5 ns3_sum_mbps          = 22.6
E2 hover-equal load0.5 delivered             = 1.000
E2 hover-equal load0.5 ns3_min_mbps          = 0.229
E2 hover-equal load1.0 ns3_sum_mbps          = 31.6
E2 hover-equal load1.0 delivered             = 0.688
E2 hover-equal load1.0 ns3_min_mbps          = 0.261
E2 kmeans-equal load0.5 ns3_sum_mbps         = 37.1
E2 kmeans-equal load0.5 delivered            = 1.000
E2 kmeans-equal load0.5 ns3_min_mbps         = 0.481
E2 kmeans-equal load1.0 ns3_sum_mbps         = 52.8
E2 kmeans-equal load1.0 delivered            = 0.708
E2 kmeans-equal load1.0 ns3_min_mbps         = 0.571
E2 kmeans-maxmin load0.5 ns3_sum_mbps        = 36.4
E2 kmeans-maxmin load0.5 delivered           = 0.999
E2 kmeans-maxmin load0.5 ns3_min_mbps        = 0.513
E2 kmeans-maxmin load1.0 ns3_sum_mbps        = 52.7
E2 kmeans-maxmin load1.0 delivered           = 0.718
E2 kmeans-maxmin load1.0 ns3_min_mbps        = 0.570

# E3–E4 hiệu chỉnh
E4 lte_alpha                                 = 0.4010
E4 lte_se_max                                = 3.5137
E4 A_3uav_chung_tan_so shannon_mbps          = 146.89
E4 A_3uav_chung_tan_so lte36942_mbps         = 76.27
E4 A_3uav_chung_tan_so model_cal_mbps        = 55.95
E4 A_3uav_chung_tan_so ns3_app_mbps          = 57.05
E4 A_3uav_chung_tan_so ratio_cal             = 1.02
E4 B_3uav_tan_so_rieng shannon_mbps          = 321.17
E4 B_3uav_tan_so_rieng lte36942_mbps         = 103.88
E4 B_3uav_tan_so_rieng model_cal_mbps        = 81.93
E4 B_3uav_tan_so_rieng ns3_app_mbps          = 80.80
E4 B_3uav_tan_so_rieng ratio_cal             = 0.99
E4 C_1uav shannon_mbps                       = 121.71
E4 C_1uav lte36942_mbps                      = 43.36
E4 C_1uav model_cal_mbps                     = 33.58
E4 C_1uav ns3_app_mbps                       = 33.71
E4 C_1uav ratio_cal                          = 1.00
E4 ns3-matrix shannon_mbps                   = 114.28
E4 ns3-matrix lte36942_mbps                  = 64.17
E4 ns3-matrix model_cal_mbps                 = 44.91
E4 ns3-matrix ns3_app_mbps                   = 45.74
E4 ns3-matrix ratio_cal                      = 1.01

# E5 lưu lượng
E5 kmeans-equal 1.0Mbps model_thr_mbps       = 20.000
E5 kmeans-equal 1.0Mbps ns3_sum_mbps         = 19.571
E5 kmeans-equal 1.0Mbps model_delay_ms       = 17.320
E5 kmeans-equal 1.0Mbps ns3_delay_ms         = 151.980
E5 kmeans-equal 1.0Mbps ns3_loss             = 0.022
E5 kmeans-equal 2.0Mbps model_thr_mbps       = 39.493
E5 kmeans-equal 2.0Mbps ns3_sum_mbps         = 33.921
E5 kmeans-equal 2.0Mbps model_delay_ms       = 278.572
E5 kmeans-equal 2.0Mbps ns3_delay_ms         = 1396.955
E5 kmeans-equal 2.0Mbps ns3_loss             = 0.152
E5 kmeans-equal 4.0Mbps model_thr_mbps       = 71.631
E5 kmeans-equal 4.0Mbps ns3_sum_mbps         = 49.939
E5 kmeans-equal 4.0Mbps model_delay_ms       = 749.220
E5 kmeans-equal 4.0Mbps ns3_delay_ms         = 2173.213
E5 kmeans-equal 4.0Mbps ns3_loss             = 0.376

# E6 WPF
E6 hover-maxmin/hover-equal 1.0Mbps min_gain = 0.180
E6 hover-maxmin/hover-equal 2.0Mbps min_gain = 0.156
E6 hover-maxmin/hover-equal 4.0Mbps min_gain = 0.156
E6 kmeans-maxmin/kmeans-equal 1.0Mbps min_gain = 0.010
E6 kmeans-maxmin/kmeans-equal 2.0Mbps min_gain = 0.097
E6 kmeans-maxmin/kmeans-equal 4.0Mbps min_gain = 0.107

# E7 ba tầng
E7 max |ns3_ideal/model - 1| throughput      = 0.00019

# E10 thuật toán đề xuất
E10 kmeans-equal 1.0Mbps min_mbps            = 0.839
E10 kmeans-equal 1.0Mbps sum_mbps            = 19.57
E10 kmeans-equal 1.0Mbps min_ratio_vs_equal  = 1.000
E10 kmeans-equal 2.0Mbps min_mbps            = 0.722
E10 kmeans-equal 2.0Mbps sum_mbps            = 33.92
E10 kmeans-equal 2.0Mbps min_ratio_vs_equal  = 1.000
E10 kmeans-equal 4.0Mbps min_mbps            = 0.671
E10 kmeans-equal 4.0Mbps sum_mbps            = 49.94
E10 kmeans-equal 4.0Mbps min_ratio_vs_equal  = 1.000
E10 kmeans-maxmin 1.0Mbps min_mbps           = 0.848
E10 kmeans-maxmin 1.0Mbps sum_mbps           = 19.61
E10 kmeans-maxmin 1.0Mbps min_ratio_vs_equal = 1.011
E10 kmeans-maxmin 2.0Mbps min_mbps           = 0.792
E10 kmeans-maxmin 2.0Mbps sum_mbps           = 34.02
E10 kmeans-maxmin 2.0Mbps min_ratio_vs_equal = 1.104
E10 kmeans-maxmin 4.0Mbps min_mbps           = 0.743
E10 kmeans-maxmin 4.0Mbps sum_mbps           = 49.68
E10 kmeans-maxmin 4.0Mbps min_ratio_vs_equal = 1.114
E10 kmeans-ifair 1.0Mbps min_mbps            = 0.920
E10 kmeans-ifair 1.0Mbps sum_mbps            = 19.75
E10 kmeans-ifair 1.0Mbps min_ratio_vs_equal  = 1.112
E10 kmeans-ifair 2.0Mbps min_mbps            = 1.285
E10 kmeans-ifair 2.0Mbps sum_mbps            = 33.36
E10 kmeans-ifair 2.0Mbps min_ratio_vs_equal  = 1.773
E10 kmeans-ifair 4.0Mbps min_mbps            = 1.272
E10 kmeans-ifair 4.0Mbps sum_mbps            = 46.14
E10 kmeans-ifair 4.0Mbps min_ratio_vs_equal  = 1.869
E10 calib-equal 1.0Mbps min_mbps             = 0.900
E10 calib-equal 1.0Mbps sum_mbps             = 19.77
E10 calib-equal 1.0Mbps min_ratio_vs_equal   = 1.092
E10 calib-equal 2.0Mbps min_mbps             = 0.799
E10 calib-equal 2.0Mbps sum_mbps             = 35.27
E10 calib-equal 2.0Mbps min_ratio_vs_equal   = 1.097
E10 calib-equal 4.0Mbps min_mbps             = 0.745
E10 calib-equal 4.0Mbps sum_mbps             = 52.20
E10 calib-equal 4.0Mbps min_ratio_vs_equal   = 1.090
E10 calib-ifair 1.0Mbps min_mbps             = 0.952
E10 calib-ifair 1.0Mbps sum_mbps             = 19.90
E10 calib-ifair 1.0Mbps min_ratio_vs_equal   = 1.161
E10 calib-ifair 2.0Mbps min_mbps             = 1.368
E10 calib-ifair 2.0Mbps sum_mbps             = 34.75
E10 calib-ifair 2.0Mbps min_ratio_vs_equal   = 1.917
E10 calib-ifair 4.0Mbps min_mbps             = 1.366
E10 calib-ifair 4.0Mbps sum_mbps             = 48.22
E10 calib-ifair 4.0Mbps min_ratio_vs_equal   = 2.026

# E11 ba nhóm user
E11 kmeans-equal 2.0Mbps sat_critical        = 0.693
E11 kmeans-equal 2.0Mbps min_critical        = 1.268
E11 kmeans-equal 2.0Mbps min_normal          = 0.729
E11 kmeans-equal 2.0Mbps thr_mbps            = 33.92
E11 kmeans-equal 4.0Mbps sat_critical        = 0.687
E11 kmeans-equal 4.0Mbps min_critical        = 1.640
E11 kmeans-equal 4.0Mbps min_normal          = 0.678
E11 kmeans-equal 4.0Mbps thr_mbps            = 49.94
E11 kmeans-maxmin 2.0Mbps sat_critical       = 0.689
E11 kmeans-maxmin 2.0Mbps min_critical       = 1.297
E11 kmeans-maxmin 2.0Mbps min_normal         = 0.813
E11 kmeans-maxmin 2.0Mbps thr_mbps           = 34.02
E11 kmeans-maxmin 4.0Mbps sat_critical       = 0.661
E11 kmeans-maxmin 4.0Mbps min_critical       = 1.673
E11 kmeans-maxmin 4.0Mbps min_normal         = 0.764
E11 kmeans-maxmin 4.0Mbps thr_mbps           = 49.68
E11 kmeans-wmaxmin 2.0Mbps sat_critical      = 0.872
E11 kmeans-wmaxmin 2.0Mbps min_critical      = 1.803
E11 kmeans-wmaxmin 2.0Mbps min_normal        = 0.589
E11 kmeans-wmaxmin 2.0Mbps thr_mbps          = 31.83
E11 kmeans-wmaxmin 4.0Mbps sat_critical      = 0.856
E11 kmeans-wmaxmin 4.0Mbps min_critical      = 2.792
E11 kmeans-wmaxmin 4.0Mbps min_normal        = 0.492
E11 kmeans-wmaxmin 4.0Mbps thr_mbps          = 44.30
E11 calib-ifair-noclass 2.0Mbps sat_critical = 0.652
E11 calib-ifair-noclass 2.0Mbps min_critical = 1.516
E11 calib-ifair-noclass 2.0Mbps min_normal   = 1.385
E11 calib-ifair-noclass 2.0Mbps thr_mbps     = 34.75
E11 calib-ifair-noclass 4.0Mbps sat_critical = 0.591
E11 calib-ifair-noclass 4.0Mbps min_critical = 1.628
E11 calib-ifair-noclass 4.0Mbps min_normal   = 1.397
E11 calib-ifair-noclass 4.0Mbps thr_mbps     = 48.22
E11 calib-ifair-shannon 2.0Mbps sat_critical = 0.976
E11 calib-ifair-shannon 2.0Mbps min_critical = 1.964
E11 calib-ifair-shannon 2.0Mbps min_normal   = 1.007
E11 calib-ifair-shannon 2.0Mbps thr_mbps     = 32.50
E11 calib-ifair-shannon 4.0Mbps sat_critical = 0.956
E11 calib-ifair-shannon 4.0Mbps min_critical = 3.239
E11 calib-ifair-shannon 4.0Mbps min_normal   = 0.941
E11 calib-ifair-shannon 4.0Mbps thr_mbps     = 44.17
E11 calib-ifair 2.0Mbps sat_critical         = 0.974
E11 calib-ifair 2.0Mbps min_critical         = 1.966
E11 calib-ifair 2.0Mbps min_normal           = 1.019
E11 calib-ifair 2.0Mbps thr_mbps             = 32.42
E11 calib-ifair 4.0Mbps sat_critical         = 0.957
E11 calib-ifair 4.0Mbps min_critical         = 3.252
E11 calib-ifair 4.0Mbps min_normal           = 0.952
E11 calib-ifair 4.0Mbps thr_mbps             = 44.13

# E12 WebSocket
E12 1 client state_bytes                     = 1742
E12 1 client state_per_s                     = 4.00
E12 1 client rtt_ms_p95 (phụ thuộc máy)      = 1.30
E12 5 client state_bytes                     = 1739
E12 5 client state_per_s                     = 4.00
E12 5 client rtt_ms_p95 (phụ thuộc máy)      = 1.56
E12 10 client state_bytes                    = 1735
E12 10 client state_per_s                    = 4.00
E12 10 client rtt_ms_p95 (phụ thuộc máy)     = 3.40
E12 20 client state_bytes                    = 1732
E12 20 client state_per_s                    = 4.00
E12 20 client rtt_ms_p95 (phụ thuộc máy)     = 1.89
E12 50 client state_bytes                    = 1733
E12 50 client state_per_s                    = 4.00
E12 50 client rtt_ms_p95 (phụ thuộc máy)     = 1.26
```
