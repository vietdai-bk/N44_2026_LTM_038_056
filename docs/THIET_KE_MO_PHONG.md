# Thiết kế mô phỏng `uavsim` + NS-3 LTE: cấp phát tài nguyên cho mạng Multi-UAV Base Station

Tài liệu này giải thích toàn bộ mô phỏng: kịch bản, các mô hình toán học và nguồn gốc của chúng, bài toán
cấp phát, vòng lặp mô phỏng, thông số thiết lập, thuật toán baseline, môi trường DRL, chỉ số đánh giá, ý nghĩa
từng file và cách chạy.

---

## Mục lục

1. [Tổng quan](#1-tổng-quan)
2. [Kịch bản hệ thống](#2-kịch-bản-hệ-thống)
3. [Các mô hình toán học](#3-các-mô-hình-toán-học)
4. [Bài toán cấp phát tài nguyên](#4-bài-toán-cấp-phát-tài-nguyên)
5. [Vòng lặp mô phỏng](#5-vòng-lặp-mô-phỏng)
6. [Thông số thiết lập](#6-thông-số-thiết-lập)
7. [Thuật toán baseline](#7-thuật-toán-baseline)
8. [Môi trường DRL (Gymnasium)](#8-môi-trường-drl-gymnasium)
9. [Chỉ số đánh giá](#9-chỉ-số-đánh-giá)
10. [Cấu trúc mã nguồn và ý nghĩa từng file](#10-cấu-trúc-mã-nguồn-và-ý-nghĩa-từng-file)
11. [Cách chạy và dữ liệu đầu ra](#11-cách-chạy-và-dữ-liệu-đầu-ra)
12. [Đo bằng NS-3 LTE](#12-đo-bằng-ns-3-lte)
13. [Kiểm thử](#13-kiểm-thử)
14. [Kết quả](#14-kết-quả)
15. [Giới hạn và hướng mở rộng](#15-giới-hạn-và-hướng-mở-rộng)
16. [Tài liệu tham khảo](#16-tài-liệu-tham-khảo)

---

## 1. Tổng quan

### 1.1. Mục tiêu

Xây dựng một **khung mô phỏng số (numerical simulation)** cho bài toán cấp phát tài nguyên trong mạng nhiều UAV
làm trạm gốc trên không, theo đúng cách các paper IEEE (TWC, TVT, IoT-J, JSAC) thường làm. Khung này phải:

- dùng các mô hình kênh và năng lượng **chuẩn, được trích dẫn nhiều** để kết quả so sánh được với paper;
- cho phép **cắm thuật toán mới** (heuristic, tối ưu, DRL) qua một giao diện duy nhất;
- **tái lập được**: cùng cấu hình và seed thì cho kết quả giống hệt từng bit;
- xuất số liệu (CSV), biểu đồ và animation để phân tích;
- **đo kết quả ở mức gói tin bằng NS-3** (yêu cầu của đồ án môn Lập trình mạng).

### 1.2. Hai tầng: mô hình Python ra quyết định, NS-3 đo

Mỗi công cụ được dùng vào việc nó làm tốt nhất:

| Tiêu chí | Mô phỏng số (uavsim) | NS-3 LTE mức gói tin |
|---|---|---|
| Vai trò | Ra quyết định, huấn luyện DRL, quét tham số nhanh | Đo throughput/delay/mất gói của kế hoạch ở mức gói tin |
|---|---|---|
| Tốc độ | 200 khe × 6 thuật toán × 3 seed < 1 giây | Vài phút mỗi run |
| Mô hình kênh A2G | Cài trực tiếp công thức trong paper | Cài lại cùng công thức thành `PropagationLossModel` C++ |
| Cắm tối ưu lồi / DRL | Python thuần, gọi trực tiếp | Không cần: chỉ phát lại kế hoạch qua file CSV |
| Mức trừu tượng | Rate Shannon, đúng như paper (kết quả *tính*) | Mô phỏng giao thức MAC/PHY/RLC/EPC/UDP: overhead, hàng đợi, handover (kết quả *đo*) |

Quy trình: thuật toán chạy trên mô hình Python, xuất **kế hoạch** (quỹ đạo UAV, liên kết, rate từng user từng khe);
NS-3 phát lại kế hoạch đó và đo. Cách "huấn luyện/quyết định trên mô hình số, kiểm chứng bằng simulator mạng" được
nhiều paper dùng, và cho thêm một kết quả đáng báo cáo: **khoảng cách giữa mô hình giải tích và mô phỏng giao thức
LTE**. Lưu ý: cả hai tầng đều là mô phỏng; NS-3 sát thực tế hơn công thức nhưng không phải thử nghiệm phần cứng.
Chi tiết ở mục 12.

Để tách bạch "mô hình đúng hay sai" với "LTE khác lý thuyết", NS-3 có hai chế độ liên kết, tạo thành **ba tầng so sánh**:

```
Lý thuyết (paper) ──khớp < 1%──► NS-3 liên kết lý tưởng ──chênh──► NS-3 LTE
   công thức                      gói UDP thật,                     giao thức LTE
                                  tốc độ = rate lý thuyết           đầy đủ
```

- Tầng 1 → 2 kiểm chứng mô hình hàng đợi và pipeline ở mức gói tin (mục 12.7, 14.9).
- Tầng 2 → 3 cho thấy mọi khoảng chênh còn lại đều do giao thức LTE (mục 14.4–14.6).

---

## 2. Kịch bản hệ thống

```
                 ▲ UAV 1 (H = 100 m)            ▲ UAV 2              ▲ UAV 3
                /|\  \                          /|\                   |
   tín hiệu    / | \   \  nhiễu đồng kênh      / | \                  |
   mong muốn  /  |  \    \ ─ ─ ─ ─ ─ ─ ─ ─ ─ ►/  |  \                 |
             ●   ●   ●     ●                 ●   ●   ●               ●  ●
           ───────────── user mặt đất trong vùng 1 km × 1 km ─────────────
```

- **M UAV** (mặc định 3) bay ở **độ cao cố định H**, mỗi UAV là một trạm gốc phát **downlink** xuống user.
- **K user mặt đất** (mặc định 20), đứng yên hoặc đi bộ ngẫu nhiên.
- Mỗi user được **đúng một UAV** phục vụ (hoặc không UAV nào).
- Trong một UAV: các user chia nhau băng thông theo kiểu **OFDMA**, không nhiễu lẫn nhau.
- Giữa các UAV: **dùng lại cùng một băng tần (reuse 1)**, nên UAV khác gây **nhiễu đồng kênh**.
- Thời gian chia thành **N khe**, mỗi khe dài `dt`. Trong một khe, vị trí và kênh coi như không đổi
  (giả thiết *quasi-static*, chuẩn trong các paper tối ưu quỹ đạo).
- Ở mỗi khe, thuật toán quyết định: **liên kết user–UAV, băng thông, công suất, vận tốc UAV**.

---

## 3. Các mô hình toán học

### 3.1. Hình học

UAV m ở vị trí ngang **q_m = (x_m, y_m)**, độ cao H. User k ở **w_k = (x_k, y_k)**, độ cao 0.

- Khoảng cách ngang: r_mk = ‖q_m − w_k‖
- Khoảng cách 3D: d_mk = √(r_mk² + H²)
- Góc nâng nhìn từ user: θ_mk = arctan(H / r_mk) (độ)

Code: `channel.py: channel_gain`.

### 3.2. Mô hình kênh Air-to-Ground

Có hai lựa chọn, chọn bằng tham số `channel`.

#### a) Al-Hourani, xác suất LoS (mặc định, `channel="al_hourani"`)

Nguồn: A. Al-Hourani, S. Kandeepan, S. Lardner, *"Optimal LAP Altitude for Maximum Coverage"*, IEEE Wireless
Communications Letters, 2014. Đây là mô hình được dùng nhiều nhất cho bài toán đặt vị trí UAV-BS.

Xác suất có đường nhìn thẳng (LoS) tăng theo góc nâng:

$$P_{LoS}(\theta) = \frac{1}{1 + a\,\exp\!\big(-b(\theta - a)\big)}$$

Suy hao trung bình (dB) gồm suy hao không gian tự do (FSPL) cộng suy hao phụ (*excess loss*) có trọng số theo
xác suất LoS/NLoS:

$$PL = \underbrace{20\log_{10}\!\Big(\frac{4\pi f_c d}{c}\Big)}_{FSPL} + P_{LoS}\,\eta_{LoS} + (1-P_{LoS})\,\eta_{NLoS}$$

Hằng số theo môi trường (`config.py: ENVIRONMENTS`):

| Môi trường | a | b | η_LoS (dB) | η_NLoS (dB) |
|---|---|---|---|---|
| `suburban` | 4.88 | 0.43 | 0.1 | 21 |
| `urban` (mặc định) | 9.61 | 0.16 | 1.0 | 20 |
| `dense_urban` | 12.08 | 0.11 | 1.6 | 23 |
| `highrise` | 27.23 | 0.08 | 2.3 | 34 |

Ý nghĩa: `a`, `b` mô tả mật độ và chiều cao tòa nhà; `η` là suy hao thêm do bóng che và tán xạ.

**Ví dụ số** (urban, f_c = 2 GHz, H = 100 m, UAV phát 1 W trên cả 10 MHz, nhiễu −99 dBm), tính bằng chính code:

| Khoảng cách ngang | Góc nâng | P_LoS | Suy hao | SNR | Rate nếu dùng cả 10 MHz |
|---|---|---|---|---|---|
| 0 m (ngay dưới) | 90° | 1.00 | 79.5 dB | 49.5 dB | 164.5 Mbps |
| 100 m | 45° | 0.97 | 83.1 dB | 45.9 dB | 152.5 Mbps |
| 200 m | 26.6° | 0.61 | 93.9 dB | 35.1 dB | 116.8 Mbps |
| 300 m | 18.4° | 0.30 | 102.8 dB | 26.2 dB | 87.1 Mbps |
| 500 m | 11.3° | 0.12 | 110.3 dB | 18.7 dB | 62.2 Mbps |
| 700 m | 8.1° | 0.08 | 114.0 dB | 15.0 dB | 50.2 Mbps |

Nhận xét: từ 100 m lên 300 m, suy hao tăng gần 20 dB, phần lớn do **mất LoS** chứ không chỉ do khoảng cách.
Vì vậy việc **di chuyển UAV lại gần cụm user** mang lại lợi ích rất lớn.

#### b) LoS thuần (`channel="los"`)

Nguồn: Q. Wu, Y. Zeng, R. Zhang, *"Joint Trajectory and Communication Design for Multi-UAV Enabled Wireless
Networks"*, IEEE TWC, 2018.

$$g_{mk} = \frac{\beta_0}{d_{mk}^2},\qquad \beta_0 = -60\text{ dB (độ lợi tại 1 m)}$$

Mô hình đơn giản, giả định luôn có LoS (phù hợp vùng nông thôn, trống trải). Đây là mô hình chuẩn trong các
paper tối ưu quỹ đạo bằng BCD + SCA, vì g là hàm lồi theo ‖q − w‖² nên dễ xấp xỉ.

#### c) Fading nhỏ Rician (tùy chọn, `rician_k_db`)

Nhân thêm độ lợi ngẫu nhiên |h|² có kỳ vọng bằng 1:

$$h = \sqrt{\tfrac{K}{K+1}} + \sqrt{\tfrac{1}{K+1}}\,\tilde h,\quad \tilde h \sim \mathcal{CN}(0,1)$$

K là tỷ số công suất thành phần LoS / tán xạ. K lớn (ví dụ 15 dB) thì gần LoS thuần; K = 0 thì thành Rayleigh.
Mặc định `None` (tắt), để kết quả phản ánh tác động của vị trí, không bị dao động ngẫu nhiên che mất.

Độ lợi kênh tuyến tính cuối cùng: **g_mk = 10^(−PL/10) · |h|²**, lưu trong ma trận `net.gain` kích thước [M, K].

### 3.3. Đa truy nhập và công thức rate

Biến quyết định cho user k (được UAV m = a_k phục vụ):

- b_k ∈ [0, 1]: tỷ lệ băng thông của UAV m cấp cho k, nên băng thông thực là b_k · B (Hz);
- p_k ≥ 0: công suất phát (W) dành cho k.

Mật độ phổ công suất tín hiệu nhận: S_k = (p_k / (b_k B)) · g_mk (W/Hz).

Mật độ nhiễu đồng kênh từ các UAV khác:

$$I_k = \sum_{j \ne m} \frac{P_j}{B}\, g_{jk},\qquad P_j = \sum_{k':\,a_{k'}=j} p_{k'}$$

Rate theo Shannon:

$$\boxed{\,r_k = b_k B \log_2\!\left(1 + \frac{S_k}{I_k + N_0}\right)\,}$$

**Giả thiết về nhiễu (xấp xỉ PSD):** coi mỗi UAV j trải tổng công suất P_j đều trên toàn băng B, nên mọi user, bất
kể ở subcarrier nào, đều nhận nhiễu với mật độ P_j/B từ UAV j. Đây là xấp xỉ "trung bình hóa" thường dùng khi
không mô hình hóa việc gán subcarrier cụ thể. UAV không phục vụ user nào thì P_j = 0, tức không phát và không gây
nhiễu.

Đặt `interference=false` thì I_k = 0, dùng làm kịch bản lý tưởng để so sánh.

**Rate kiểu LTE (`rate_model="lte"`).** Shannon thuần không có giới hạn trên. Ở SNR 40–50 dB nó cho 13–16 bit/s/Hz,
trong khi LTE SISO với bảng MCS chỉ đạt khoảng 4–5 bit/s/Hz. Khi cần sát với LTE (bắt buộc khi gửi kế hoạch sang
NS-3), dùng Shannon cắt ngọn theo 3GPP TR 36.942, Phụ lục A.1:

$$SE = \begin{cases} 0 & SINR < -10\text{ dB} \\ \min\big(0.6\log_2(1+SINR),\ 4.4\big) & \text{ngược lại}\end{cases},\qquad r_k = b_k B \cdot SE$$

α = 0.6 mô tả tổn hao do overhead và mã hóa thực tế; 4.4 bit/s/Hz là hiệu suất phổ tối đa (MCS cao nhất).
Hằng số là tham số cấu hình `lte_alpha` (mặc định 0.6) và `lte_se_max` (mặc định 4.4) trong `SimConfig`.

Code: `network.py: Network.rates`.

### 3.4. Mô hình năng lượng bay (UAV cánh quay)

Nguồn: Y. Zeng, J. Xu, R. Zhang, *"Energy Minimization for Wireless Communication With Rotary-Wing UAV"*, IEEE
TWC, 2019. Đây là mô hình năng lượng chuẩn cho quadcopter trong hầu hết paper.

$$P(V) = \underbrace{P_0\Big(1+\frac{3V^2}{U_{tip}^2}\Big)}_{\text{blade profile}} + \underbrace{P_i\Big(\sqrt{1+\frac{V^4}{4v_0^4}}-\frac{V^2}{2v_0^2}\Big)^{1/2}}_{\text{induced}} + \underbrace{\tfrac12 d_0\rho s A V^3}_{\text{parasite}}$$

| Ký hiệu | Giá trị | Ý nghĩa vật lý |
|---|---|---|
| P₀ | 79.86 W | Công suất thắng ma sát của cánh quạt khi hover |
| P_i | 88.63 W | Công suất tạo lực nâng (induced) khi hover |
| U_tip | 120 m/s | Tốc độ đầu cánh quạt |
| v₀ | 4.03 m/s | Vận tốc dòng khí cảm ứng trung bình qua rotor khi hover |
| d₀ | 0.6 | Tỷ số lực cản thân máy bay |
| ρ | 1.225 kg/m³ | Mật độ không khí |
| s | 0.05 | Độ đặc của rotor (solidity) |
| A | 0.503 m² | Diện tích đĩa rotor |

Ba thành phần: cánh quạt (tăng nhẹ theo V²), lực nâng (*giảm* khi bay nhanh vì rotor nhận thêm dòng khí), lực cản
thân (tăng theo V³).

| Vận tốc | Công suất | Ghi chú |
|---|---|---|
| 0 m/s (hover) | 168.5 W | P₀ + P_i |
| **10.2 m/s** | **126.0 W** | Tối thiểu: bay vừa phải tiết kiệm hơn đứng yên |
| 20 m/s (v_max) | 178.3 W | Lực cản thân bắt đầu chi phối |

Năng lượng một khe: **E_m = P(‖v_m‖) · dt** (J). Mô phỏng chỉ tính năng lượng bay, vì năng lượng phát sóng
(≤ 1 W) nhỏ hơn hai bậc.

Code: `energy.py: rotary_power`.

### 3.5. Mô hình di chuyển

- **UAV:** nhận vận tốc v_m từ thuật toán. Nếu ‖v_m‖ > v_max thì co về v_max và giữ nguyên hướng. Vị trí mới
  q_m ← q_m + v_m · dt, rồi kẹp trong vùng [0, area]².
- **User:** nếu `user_speed > 0`, mỗi khe đi một bước dài `user_speed · dt` theo hướng ngẫu nhiên đều trong
  [0, 2π) (random walk), rồi kẹp trong vùng.
- **Vị trí ban đầu:** UAV phân bố đều ngẫu nhiên trong vùng. User theo `user_layout`:
  - `uniform`: đều ngẫu nhiên trong vùng;
  - `clustered`: chọn M tâm cụm trong [15%, 85%] vùng, mỗi user gán vào một tâm ngẫu nhiên rồi lệch theo phân bố
    chuẩn với độ lệch 8% cạnh vùng (80 m). Kịch bản này giống "hotspot" và là lý do để UAV cần di chuyển.

Code: `network.py: Network.reset, _place_users, step`.

### 3.6. Lưu lượng, hàng đợi, delay và mất gói (tùy chọn)

Khi `demand_mbps` khác `None`, mỗi user nhận lưu lượng CBR A = `demand_mbps`·Δt bit mỗi khe, xếp vào một hàng đợi
riêng tại UAV, được phục vụ với tốc độ r_k của khe đó. Đây là mô hình hàng đợi theo khe kiểu Lyapunov mà các paper
về UAV có QoS hay dùng:

$$Q_k[t+1] = \min\Big(\max\big(Q_k[t] + A - r_k[t]\,\Delta t,\ 0\big),\ Q_{max}\Big)$$

- **Phục vụ:** S_k = min(Q_k + A, r_k·Δt). Throughput = S_k / Δt.
- **Mất gói:** phần vượt bộ đệm Q_max = `buffer_bytes`·8 (mặc định 1 MiB, bằng `LteRlcUm::MaxTxBufferSize` của kịch
  bản NS-3). Tỷ lệ mất mỗi khe = phần tràn / lưu lượng đến.
- **Delay** (FIFO chính xác): hàng đợi là FIFO dạng lỏng, lưu lượng đến và tốc độ phục vụ không đổi trong khe. Gọi A(t)
  là số bit đã vào hàng đợi tích lũy (không tính bit bị bỏ), S(t) là số bit đã phục vụ tích lũy. Bit thứ x đến lúc
  A⁻¹(x) và rời lúc S⁻¹(x), nên delay chờ của nó là S⁻¹(x) − A⁻¹(x). Delay của user trong khe = trung bình delay chờ
  của các bit phục vụ trong khe + `pkt_bytes`·8 / r_k (thời gian phát một gói 1200 byte). Delay của mạng là trung bình
  theo số bit phục vụ.

  Hàm `network.py: fifo_delay` tính tích phân này bằng cách chia mỗi khe thành 200 bước con và giữ lịch sử A(t) của
  từng user (bỏ phần đã phục vụ hết). Bản trước dùng định luật Little với Q̄ = (Q đầu khe + Q cuối khe)/2; cách đó sai
  khi hàng đợi cạn hay đầy giữa khe, hoặc khi bit phục vụ trong khe đã đến từ các khe trước, và lệch NS-3 tới 25%
  (mục 14.9).

Hàm thuần `network.py: queue_step` cài phương trình hàng đợi; `Network._queue` gọi nó và `fifo_delay` mỗi khe. Chỉ số
thêm vào mỗi khe: `throughput`, `min_throughput`, `delay_ms`, `loss`, `queue_bits`, `capacity` (tốc độ phục vụ thực
của từng user, sau khi chia lại băng nếu `work_conserving`).

**Mất gói khi so với NS-3.** NS-3 tính mất = 1 − gói nhận / gói gửi, nên gói còn nằm trong hàng đợi lúc mô phỏng dừng
cũng bị tính là mất. `uavsim/ns3.py: run_one` vì vậy báo `model_loss` = Σ phần tràn / Σ lưu lượng đến + Q cuối episode /
Σ lưu lượng đến, cùng định nghĩa với NS-3. Chỉ số `loss` từng khe của mô phỏng chính giữ nguyên.

Mặc định mô hình giữ đúng giả định của paper. Hai tùy chọn bật thêm cơ chế của LTE, dùng để giải thích chênh lệch với
NS-3 (mục 14.6):
- `work_conserving=True`: trong mỗi UAV, băng thông được chia lại theo nhu cầu thực (Q + A) bằng water-filling max-min
  (`network.py: waterfill`). User cần ít nhận đúng phần cần, phần dư chia cho user còn chờ. Mặc định (False) mỗi user giữ
  cố định b_k do thuật toán cấp, dùng không hết cũng không nhường.
- `load_coupled=True`: nhiễu từ UAV j nhân với tỷ lệ băng UAV j thực sự dùng ở khe trước (load-coupled interference).
  Mặc định (False) mọi UAV luôn phát đủ công suất trên cả băng, tức nhiễu tối đa.

---

## 4. Bài toán cấp phát tài nguyên

Tại mỗi khe n, thuật toán chọn **Action** gồm bốn biến:

| Biến | Ký hiệu | Shape | Miền |
|---|---|---|---|
| Liên kết | a_k | [K] | {−1, 0, …, M−1}, −1 là không phục vụ |
| Băng thông | b_k | [K] | [0, 1] |
| Công suất | p_k | [K] | ≥ 0 (W) |
| Vận tốc UAV | v_m | [M, 2] | ‖v_m‖ ≤ v_max |

Dạng bài toán tổng quát (ví dụ tối đa tổng rate trên cả episode):

$$\max_{\{a,b,p,v\}}\ \sum_{n=1}^{N}\sum_{k=1}^{K} r_k[n]$$

$$\text{s.t.}\quad \sum_{k:\,a_k=m} b_k[n] \le 1,\qquad \sum_{k:\,a_k=m} p_k[n] \le P_{max},\qquad \|v_m[n]\| \le V_{max},\qquad \forall m, n$$

Các biến thể hay gặp trong paper, đều tính được từ dữ liệu mô phỏng xuất ra:

- **max-min fairness:** max min_k r_k (xem `min_rate`);
- **hiệu suất năng lượng:** max (Σ bit) / (Σ năng lượng) (xem `energy_eff`);
- **ràng buộc QoS:** r_k ≥ r_min (xem `coverage`);
- **ràng buộc năng lượng hay pin:** Σ_n E_m[n] ≤ E_max (chưa cài, xem mục 15).

Bài toán này là **non-convex hỗn hợp nguyên** (a_k rời rạc; q xuất hiện trong kênh và nhiễu), nên trong paper
thường được giải bằng phân rã (BCD), xấp xỉ lồi (SCA) hoặc DRL. `uavsim` không ép một phương pháp nào, mà chỉ
cung cấp môi trường để đánh giá mọi phương pháp **trên cùng một mô hình**.

**Kiểm tra ràng buộc:** `Network.check` **từ chối** (ném `ValueError`) mọi Action vi phạm ràng buộc băng thông,
công suất, giá trị âm hay shape sai, thay vì âm thầm sửa. Mục đích là để lỗi của thuật toán lộ ra ngay. Riêng vận
tốc được **co về v_max** (không báo lỗi) vì đó là giới hạn vật lý, và DRL thường xuất vận tốc thô.

---

## 5. Vòng lặp mô phỏng

```
Network(cfg)                         # khởi tạo vị trí UAV, user, tính gain [M,K]
algo.reset(net)
for n = 0 … N−1:
    action = algo.act(net)           # 1. thuật toán đọc trạng thái, trả về Action
    net.check(action)                # 2. kiểm tra ràng buộc (sai thì báo lỗi)
    r = net.rates(action)            # 3. rate từng user tại vị trí hiện tại
    v = co về v_max(action.velocity)
    E = P(‖v‖)·dt                    # 4. năng lượng bay của khe
    ghi metrics (sum, min, Jain, coverage, energy)
    q ← clip(q + v·dt)               # 5. di chuyển UAV
    w ← random walk (nếu có)         #    di chuyển user
    gain ← channel_gain(q, w)        # 6. tính lại kênh (và fading mới) cho khe sau
```

Thứ tự này có nghĩa: **rate của khe n được tính tại vị trí đầu khe n**, còn vận tốc chọn ở khe n chỉ ảnh hưởng
từ khe n+1. Đây là quy ước thời gian rời rạc chuẩn (*zero-order hold*).

Mọi số ngẫu nhiên (vị trí ban đầu, random walk, fading) dùng một bộ sinh `numpy.random.default_rng(seed)` duy
nhất trong `Network`. Thuật toán `random` có bộ sinh riêng (seed + 1), để việc thuật toán dùng số ngẫu nhiên không
làm thay đổi kịch bản. Nhờ vậy **mọi thuật toán cùng seed đều thấy cùng một kịch bản**, nên so sánh được công bằng.

---

## 6. Thông số thiết lập

Toàn bộ nằm trong `uavsim/config.py: SimConfig`. Giá trị mặc định chọn theo dải hay gặp trong các paper
multi-UAV BS.

### 6.1. Topology

| Tham số | Mặc định | Đơn vị | Ý nghĩa và lý do chọn |
|---|---|---|---|
| `num_uavs` | 3 | | Số UAV M. Paper thường dùng 2–6 |
| `num_users` | 20 | | Số user K. Paper thường dùng 10–50 |
| `area` | 1000 | m | Vùng vuông 1×1 km, mức phổ biến nhất |
| `altitude` | 100 | m | Độ cao cố định H. Dải 50–150 m, nằm dưới giới hạn 120 m của nhiều quy định bay |
| `user_layout` | `clustered` | | `clustered` (hotspot) hoặc `uniform` |
| `user_speed` | 0 | m/s | 0 là đứng yên; 1–3 m/s mô phỏng người đi bộ |

### 6.2. Thời gian và chuyển động

| Tham số | Mặc định | Đơn vị | Ý nghĩa |
|---|---|---|---|
| `slots` | 200 | khe | Số khe N trong một episode |
| `dt` | 1 | s | Độ dài một khe. Tổng thời gian T = N·dt = 200 s |
| `v_max` | 20 | m/s | Vận tốc ngang tối đa. Mỗi khe đi tối đa 20 m; đi hết cạnh vùng mất 50 khe |

### 6.3. Kênh

| Tham số | Mặc định | Đơn vị | Ý nghĩa |
|---|---|---|---|
| `channel` | `al_hourani` | | `al_hourani` hoặc `los` (mục 3.2) |
| `environment` | `urban` | | Bộ hằng số Al-Hourani |
| `fc` | 2·10⁹ | Hz | Tần số sóng mang (băng LTE/5G sub-6 GHz) |
| `beta0_db` | −60 | dB | Độ lợi kênh tại 1 m, chỉ dùng với `channel=los`; ứng với khoảng 2.4 GHz |
| `rician_k_db` | None | dB | Hệ số K Rician; None là tắt fading nhỏ |

### 6.4. Vô tuyến

| Tham số | Mặc định | Đơn vị | Ý nghĩa |
|---|---|---|---|
| `bandwidth` | 10·10⁶ | Hz | Băng thông B của mỗi UAV, các UAV dùng chung (reuse 1) |
| `noise_psd_dbm` | −169 | dBm/Hz | N₀ = −174 dBm/Hz (nhiễu nhiệt ở 290 K) + noise figure 5 dB. Trên 10 MHz là −99 dBm |
| `p_max` | 1 | W | Tổng công suất phát mỗi UAV (30 dBm), dải paper 0.1–5 W |
| `interference` | true | | Bật hoặc tắt nhiễu đồng kênh giữa các UAV |
| `demand_mbps` | None | Mbps | Lưu lượng CBR mỗi user; None = full buffer (chỉ tính năng lực, không delay/mất gói) |
| `buffer_bytes` | 1048576 | byte | Bộ đệm mỗi user, bằng bộ đệm RLC của NS-3 |
| `pkt_bytes` | 1200 | byte | Kích thước gói, bằng payload UDP của NS-3 |
| `work_conserving` | false | | Chia lại băng thông theo nhu cầu trong mỗi UAV (mục 3.6) |
| `load_coupled` | false | | Nhiễu tỷ lệ với phần băng UAV gây nhiễu thực sự dùng (mục 3.6) |
| `rate_model` | `shannon` | | `shannon` hoặc `lte` (mục 3.3); `uavsim.ns3` tự đặt `lte` |
| `lte_alpha`, `lte_se_max` | 0.6, 4.4 | —, bit/s/Hz | Hằng số của rate kiểu LTE; giá trị khớp với NS-3 là 0.401, 3.514 (mục 14.4) |
| `r_min` | 10⁶ | bit/s | Ngưỡng QoS 1 Mbps, dùng để tính `coverage` |
| `seed` | 0 | | Hạt giống; chạy nhiều seed thì dùng seed, seed+1, … |

`SimConfig.__post_init__` kiểm tra giá trị hợp lệ (tên kênh, môi trường, layout, số lượng ≥ 1).
`SimConfig.from_json` từ chối khóa lạ trong file JSON, để tránh gõ sai tên tham số mà không biết.

### 6.5. Hằng số cố định

- Hằng số Al-Hourani: mục 3.2.
- Hằng số năng lượng Zeng: mục 3.4.
- `TOL = 1e-6` (`network.py`): sai số cho phép khi kiểm tra Σb ≤ 1 và Σp ≤ P_max.

---

## 7. Thuật toán baseline

File `uavsim/algorithms.py`. Mỗi baseline là tổ hợp **một chiến lược di chuyển × một chiến lược cấp phát**,
đặt tên `{mobility}-{alloc}`, tổng cộng 6 thuật toán:

| | `equal` | `maxmin` |
|---|---|---|
| `hover` | hover-equal | hover-maxmin |
| `kmeans` | kmeans-equal | kmeans-maxmin |
| `random` | random-equal | random-maxmin |

### 7.1. Liên kết user–UAV: max-gain (dùng chung cho mọi baseline)

$$a_k = \arg\max_m g_{mk}$$

User gắn vào UAV có kênh tốt nhất. Đơn giản, phổ biến, nhưng không cân bằng tải: một UAV có thể bị quá nhiều user.

Hàm: `associate_max_gain`.

### 7.2. Cấp phát băng thông

Trong mỗi UAV m, chia băng thông theo trọng số w_k:

$$b_k = \frac{w_k}{\sum_{k':\,a_{k'}=m} w_{k'}}$$

Hàm: `split_by_weight`. Sau khi chia, Σ b_k = 1 với mỗi UAV có user.

- **`equal`:** w_k = 1, tức các user của một UAV chia đều băng.
- **`maxmin`:** w_k = 1 / SE_k, với hiệu suất phổ

  $$SE_k = \log_2\!\Big(1 + \frac{P_{max}}{B}\cdot\frac{g_{a_k k}}{N_0}\Big)$$

  *Suy ra:* vì công suất tỷ lệ với băng thông (mục 7.3), mật độ công suất trên phần băng của user k luôn là
  P_max/B, nên khi không có nhiễu, r_k = b_k · B · SE_k. Muốn mọi user trong một UAV có **rate bằng nhau** thì
  b_k ∝ 1/SE_k. User kênh yếu được nhiều băng hơn: tăng `min_rate`, giảm nhẹ `sum_rate`. Khi có nhiễu, rate chỉ
  xấp xỉ bằng nhau.

### 7.3. Cấp phát công suất: tỷ lệ băng thông

$$p_k = b_k \cdot P_{max}$$

Hàm: `power_by_bw`. Kết quả là mật độ công suất phẳng P_max/B trên toàn bộ phần băng được dùng, và Σp_k = P_max.
Cách này giữ đúng giả thiết PSD của mô hình nhiễu (mục 3.3).

### 7.4. Chiến lược di chuyển

- **`hover`:** v_m = 0, UAV đứng yên tại vị trí xuất phát. Đây là baseline "triển khai tĩnh".
- **`random`:** mỗi khe chọn hướng ngẫu nhiên đều, bay với v_max. Đây là mốc so sánh "di chuyển vô định hướng",
  tốn năng lượng nhất.
- **`kmeans`:** mỗi khe:
  1. Chạy k-means (Lloyd, 20 vòng) trên vị trí user hiện tại, **khởi tạo tâm cụm bằng chính vị trí UAV**. Nhờ
     đó cụm j luôn ứng với UAV j (UAV bay về cụm gần nó nhất), không bị đổi nhãn giữa các khe.
  2. **Xử lý cụm rỗng:** nếu không user nào gần tâm j nhất, ví dụ UAV xuất phát ở góc xa mọi user, thì đặt tâm
     j vào user đang **xa tâm của mình nhất**. Nếu không xử lý, UAV đó đứng yên cả episode và bỏ phí tài nguyên.
     Lỗi này đã được phát hiện nhờ animation.
  3. Vận tốc v_m = (tâm_m − q_m) / dt, rồi `Network` co về v_max. Kết quả là UAV bay thẳng về tâm cụm với tốc độ
     tối đa và dừng lại khi tới nơi.

  Đặt UAV ở tâm cụm là heuristic đặt vị trí kinh điển trong paper UAV-BS: tối thiểu tổng bình phương khoảng cách
  tới user, nên gần như tối đa độ lợi kênh trung bình.

### 7.5. Thuật toán đề xuất: `calib-ifair`

**Ba nhóm user.** `SimConfig.important_frac`, `critical_frac` (mặc định 0, tức mọi user là normal như các thí nghiệm
cũ) đặt tỷ lệ user important và critical. `network.user_classes(cfg)` bốc nhóm bằng rng riêng `[seed, 7]`, nên vị trí
user và mọi số liệu cũ không đổi. Mỗi nhóm có trọng số `class_weights = (1, 2, 4)` và tốc độ mong muốn
`class_rmin_mbps = (0.5, 1, 2)`. Khi có nhóm, `Network.step` thêm `min_<nhóm>` (min tốc độ, hoặc min throughput khi có
lưu lượng) và `sat_<nhóm>` (tỷ lệ user đạt min(r_min nhóm, 0.9·λ)). Mục tiêu của thuật toán là Σ w_k log(r_k + r_0);
khi mọi w = 1 nó trở về tổng log thường.

Ý tưởng: các baseline quyết định dựa trên Shannon và bỏ qua nhiễu, trong khi các thí nghiệm NS-3 (mục 14.4–14.7) cho
thấy hai điều: tốc độ thật đi theo đường cong LTE (độ dốc 0.401, trần 3.514 bit/s/Hz), và việc chia băng chỉ có tác
dụng khi áp ở tầng MAC. Thuật toán đề xuất dùng chính đường cong đo được để ra quyết định, và đưa quyết định chia băng
xuống MAC bằng scheduler WPF.

**Chia băng `ifair`.** Với SINR thật của user (có nhiễu từ mọi UAV đang phục vụ), tính hiệu suất phổ dự đoán theo LTE
đã hiệu chỉnh:

$$\widehat{SE}_k = \min\big(0.401\log_2(1+SINR_k),\ 3.514\big),\qquad b_k = \frac{w_k/\max(\widehat{SE}_k, 0.05)}{\sum_{k':a_{k'}=a_k} w_{k'}/\max(\widehat{SE}_{k'}, 0.05)}$$

Nhờ vậy rate dự đoán của các user trong một UAV tỷ lệ với trọng số nhóm (bằng nhau khi cùng nhóm). Khác với `maxmin` (dùng SNR không nhiễu và Shannon không
trần), `ifair` biết user nào đang chịu nhiễu và biết user ở gần đã chạm trần LTE, nên không phí băng cho user không thể
nhanh hơn. Sàn 0.05 bit/s/Hz tránh việc một user gần như mất sóng hút hết băng của cả UAV.

**Di chuyển `calib`.** Hai pha cho mỗi UAV:
1. Còn cách tâm cụm k-means hơn một bước bay thì bay thẳng về tâm cụm (giống `kmeans`).
2. Tới nơi thì tinh chỉnh bằng tìm kiếm cục bộ: thử đứng yên và 8 hướng × 2 cỡ bước (v_max·Δt và một phần tư), giữ
   nước đi làm tăng tiện ích công bằng tỷ lệ dự đoán

$$U(q) = \sum_k w_k\log\big(\hat r_k(q) + 10^3\big),\qquad \hat r_k = \frac{B\,w_k}{\sum_{k':a_{k'}=a_k} w_{k'}/\widehat{SE}_{k'}}$$

   (rate mỗi user khi UAV chia băng theo `ifair`, có nhiễu, có trần LTE). Các UAV được xét lần lượt, mỗi UAV thấy vị
   trí mới của UAV trước.

Trong pha tìm kiếm cục bộ, không nhận nước đi làm giảm số UAV có user (pha bay về tâm cụm không kiểm tra điều này). Khi thử bản không có ràng buộc này, tìm kiếm cục bộ thường "tắt" một UAV
để giảm nhiễu tức thời, dẫn tới nghiệm kém hơn nhiều (ví dụ seed 1: 2 user / 0 / 18 user, sum rate 13 Mbps so với 43
Mbps của kmeans-ifair).

**Độ phức tạp mỗi khe:** O(M · 17 · M·K) cho phần tinh chỉnh (17 ứng viên mỗi UAV, mỗi ứng viên tính lại kênh M×K),
đo được 5.5 ms/khe với 3 UAV, 20 user và 13.6 ms/khe với 8 UAV, 60 user (cấu hình lớn nhất của dashboard), nhỏ hơn
nhiều so với khe 0.25 s.

**Bản so sánh cùng mục tiêu:** `kmeans-ifair` (chỉ đổi cách chia băng), `calib-equal` (chỉ đổi cách di chuyển),
`calib-ifair-noclass` (`Heuristic(weighted=False)`, mọi w = 1) và `calib-ifair-shannon` (`Heuristic(rate="shannon")`:
`calibrated_se(..., model="shannon")` trả log2(1+SINR), không trần, vẫn có nhiễu). Bảng dưới là số liệu không có nhóm
user (mọi w = 1, nên `calib-ifair` ở đây chính là `calib-ifair-noclass`); kết quả ba nhóm ở mục 14.11.

**Trên mô hình LTE đã hiệu chỉnh** (10 seed, 60 khe):

| Thuật toán | Sum rate (Mbps) | Min rate (Mbps) | Jain | Coverage |
|---|---|---|---|---|
| kmeans-equal | 58.2 | 0.83 | 0.686 | 83% |
| kmeans-maxmin | 57.0 | 0.95 | 0.698 | 84% |
| kmeans-ifair | 52.0 | 1.60 | 0.724 | 85% |
| calib-equal | 59.5 | 0.89 | 0.703 | 86% |
| **calib-ifair** | 53.5 | **1.71** | **0.744** | **88%** |

So với kmeans-equal, calib-ifair tăng min rate khoảng 2.1 lần và coverage 5 điểm, đổi lại sum rate giảm 8%. Kết quả đo
bằng NS-3 LTE ở mục 14.10.

### 7.6. Giao diện để cắm thuật toán mới

Mọi thuật toán chỉ cần hai phương thức:

```python
from uavsim.network import Action, Network

class MyAlgo:
    name = "my-algo"

    def reset(self, net: Network) -> None:
        """Gọi đầu mỗi episode: khởi tạo trạng thái nội bộ, bộ sinh ngẫu nhiên, ..."""

    def act(self, net: Network) -> Action:
        """Đọc trạng thái, trả về quyết định của khe hiện tại."""
        # Trạng thái đọc được:
        #   net.uav_xy  [M,2]  vị trí UAV (m)
        #   net.user_xy [K,2]  vị trí user (m)
        #   net.gain    [M,K]  độ lợi kênh tuyến tính
        #   net.t              khe hiện tại
        #   net.cfg            toàn bộ SimConfig
        # Có thể gọi net.rates(action) để thử nghiệm (không làm thay đổi trạng thái).
        ...
```

Đăng ký vào `REGISTRY` trong `algorithms.py`:

```python
REGISTRY["my-algo"] = MyAlgo
```

Sau đó dùng được ngay: `python -m uavsim.run --algos my-algo kmeans-equal`.

Các hàm có thể dùng lại: `associate_max_gain`, `split_by_weight`, `power_by_bw`, `kmeans`.

Việc `net.rates(action)` không làm thay đổi trạng thái rất hữu ích cho các thuật toán cần đánh giá nhiều phương án
trong một khe, như tìm kiếm tham lam, SCA lặp, hay đánh giá ứng viên vị trí.

---

## 8. Môi trường DRL (Gymnasium)

File `uavsim/env.py`, lớp `UavBsEnv`, tuân thủ chuẩn Gymnasium 1.0 (đã qua `check_env`).

### 8.1. Phân chia nhiệm vụ

Theo cách phổ biến trong paper DRL cho UAV: **agent học quỹ đạo (vận tốc UAV)**, còn **cấp phát tài nguyên giao
cho một allocator đóng** (mặc định max-gain + equal). Lý do:

- không gian hành động liên tục và nhỏ (2M chiều), hợp với DDPG, TD3, PPO, SAC;
- tách rõ phần "học được" và phần "giải tường minh", dễ phân tích đóng góp của DRL.

Đổi allocator bằng tham số `allocator=Heuristic("hover", "maxmin")`; chỉ phần cấp phát được dùng, phần vận tốc
bị bỏ qua.

### 8.2. Đặc tả

| Thành phần | Định nghĩa |
|---|---|
| Observation | `Box(0, 1, (2(M+K),))`: vị trí UAV rồi vị trí user, chia cho `area` |
| Action | `Box(−1, 1, (M, 2))`: nhân với v_max ra vận tốc. Chuẩn vô hướng vẫn có thể đạt √2·v_max, khi đó `Network` co về v_max |
| Reward | `reward_fn(metrics, cfg)`, mặc định `sum_rate / (K · r_min)`. Chẳng hạn reward = 20 nghĩa là trung bình mỗi user đạt đúng r_min |
| Kết thúc | `truncated = True` sau `slots` khe; không có `terminated` (không có trạng thái thất bại) |
| `info` | Toàn bộ metrics của khe (rates, energy, …) |
| `reset(seed=None)` | Sinh một kịch bản mới ngẫu nhiên, để agent tổng quát hóa thay vì học thuộc một bản đồ |
| `reset(seed=s)` | Tái lập đúng kịch bản s, dùng khi đánh giá |

### 8.3. Ví dụ reward đánh đổi rate và năng lượng

```python
from uavsim.config import SimConfig
from uavsim.env import UavBsEnv

env = UavBsEnv(
    SimConfig(num_uavs=3, num_users=20),
    reward_fn=lambda m, c: m["sum_rate"] / 1e8 - 1e-3 * m["energy"],
)
obs, _ = env.reset(seed=0)
obs, reward, terminated, truncated, info = env.step(env.action_space.sample())
```

Môi trường đã sẵn sàng, nhưng **chưa có agent nào được huấn luyện**. Muốn huấn luyện cần cài thêm `torch` và
`stable-baselines3`.

---

## 9. Chỉ số đánh giá

### 9.1. Mỗi khe (`timeseries.csv`)

| Chỉ số | Công thức | Đơn vị | Ý nghĩa |
|---|---|---|---|
| `sum_rate` | Σ_k r_k | bit/s | Hiệu quả tổng của mạng |
| `min_rate` | min_k r_k | bit/s | User kém nhất, thước đo max-min fairness |
| `jain` | (Σr_k)² / (K·Σr_k²) | 0–1 | Chỉ số công bằng Jain; 1 là mọi user có rate bằng nhau, 1/K là chỉ một user có rate |
| `coverage` | (1/K)·#{k : r_k ≥ r_min} | 0–1 | Tỷ lệ user đạt QoS |
| `energy` | Σ_m P(‖v_m‖)·dt | J | Năng lượng bay của mọi UAV trong khe |

Lưu ý: Jain ở đây tính trên rate tuyệt đối. Khi user ở xa thì Jain thấp là tự nhiên, kể cả với thuật toán tốt.

### 9.2. Tổng hợp (`summary.csv`, một dòng mỗi thuật toán × seed)

- `sum_rate`, `min_rate`, `jain`, `coverage`, `energy`: **trung bình theo khe** của episode.
- `energy_eff` = (Σ_n sum_rate[n] · dt) / (Σ_n energy[n]): **tổng bit / tổng Joule** (bit/J), tức hiệu suất năng
  lượng toàn episode.

Bảng in ra màn hình lấy tiếp **trung bình ± độ lệch chuẩn qua các seed**.

---

## 10. Cấu trúc mã nguồn và ý nghĩa từng file

```
LapTrinhMang/
├── uavsim/                  # gói mô phỏng
│   ├── __init__.py          # xuất SimConfig, Action, Network
│   ├── config.py            # tham số + hằng số Al-Hourani
│   ├── channel.py           # mô hình kênh A2G
│   ├── energy.py            # mô hình năng lượng bay
│   ├── network.py           # trạng thái mạng, ràng buộc, rate, bước thời gian
│   ├── algorithms.py        # baseline + REGISTRY
│   ├── env.py               # môi trường Gymnasium cho DRL
│   ├── run.py               # CLI so sánh thuật toán, xuất CSV và biểu đồ
│   ├── animate.py           # CLI tạo animation GIF/MP4
│   ├── live.py              # điều khiển thời gian thực: server WebSocket, lái tay, ghi phiên
│   ├── gazebo.py            # hiển thị 3D trong Gazebo
│   ├── web/index.html       # dashboard
│   ├── ns3.py               # cầu nối NS-3: xuất kế hoạch, chạy, đo, so sánh
│   └── validate.py          # kiểm chứng nguyên nhân chênh lệch mô hình–NS-3
├── ns3/
│   ├── scratch/uav_lte/uav-lte.cc  # kịch bản NS-3 LTE
│   ├── scratch/uav_lte/wpf-ff-mac-scheduler.{h,cc}  # scheduler Weighted PF (trọng số b_k)
│   └── install.sh           # symlink vào NS-3 và build
├── tests/                  # 46 test (test_uavsim.py, test_gazebo_pool.py)
├── docs/THIET_KE_MO_PHONG.md  # tài liệu này
├── docs/MO_TA_DU_AN.md      # mô tả tổng quan dự án
├── experiments/plot_three_tier.py  # biểu đồ ba tầng lý thuyết / NS-3 lý tưởng / NS-3 LTE
└── experiments/results/     # kết quả các lần chạy
```

| File | Dòng | Vai trò | Nội dung chính |
|---|---|---|---|
| `config.py` | ~65 | Nơi duy nhất chứa tham số | `SimConfig` (dataclass), `ENVIRONMENTS`, kiểm tra hợp lệ, `from_json`, `noise_psd` (đổi dBm/Hz sang W/Hz) |
| `channel.py` | ~40 | Mô hình kênh | `los_probability`, `path_loss_db` (Al-Hourani hoặc β₀/d²), `rician_power`, `channel_gain` → ma trận [M, K] |
| `energy.py` | ~20 | Mô hình năng lượng | Hằng số Zeng 2019, `rotary_power(v)` (nhận số hoặc mảng) |
| `network.py` | ~225 | Lõi mô phỏng | `Action` (4 biến quyết định), `queue_step` (hàng đợi theo khe), `fifo_delay` (delay FIFO chính xác), `waterfill`, `Network`: `reset` (sinh kịch bản), `check` (ràng buộc), `rates` (SINR, Shannon hoặc LTE), `_queue` (lưu lượng, delay, mất gói), `step` (một khe: rate, năng lượng, di chuyển, cập nhật kênh), `jain` |
| `algorithms.py` | ~80 | Thuật toán | Hàm dựng sẵn (`associate_max_gain`, `split_by_weight`, `power_by_bw`, `kmeans`), lớp `Heuristic(mobility, alloc)`, `REGISTRY` tên → hàm tạo |
| `env.py` | ~45 | Cầu nối DRL | `UavBsEnv` (Gymnasium), `sum_rate_reward` |
| `run.py` | ~130 | Chạy thí nghiệm | `run_episode`, `summarize`, `parse_set` (đọc `--set k=v`), `plot` (3 biểu đồ), `main` (CLI) |
| `animate.py` | ~85 | Trực quan hóa | `record` (ghi lại vị trí, liên kết, rate mỗi khe), `animate` (vẽ các thuật toán cạnh nhau) |
| `ns3.py` | ~370 | Cầu nối NS-3 | `export_plan` (kế hoạch kèm `cap_bps`), `ns3_command`, `run_ns3` (subprocess có timeout, ghi log), `ns3_metrics`, `trace_stats`, `run_one`, `aggregate`, `plot`, `plot_matrix`, `main` (CLI `--link lte|ideal`, chạy song song) |
| `validate.py` | ~320 | Kiểm chứng | `link_point` (đường cong một liên kết), `fit_alpha_cap`, `replay_model`, `ns3_sinr_per_slot`, `analyze_run` (hiệu chỉnh, so SINR, phân rã), `demand_variants` và `plot_demand` (delay, mất gói), `main` |
| `live.py` | ~250 | Thời gian thực | `LiveSession` (step có lái tay, ghi phiên), `Server` (WebSocket, vòng lặp), `serve_static`, `main` |
| `gazebo.py` | ~100 | Hiển thị 3D | `world_sdf`, `GazeboView.update` |
| `web/index.html` | ~330 | Dashboard | Bản đồ canvas, chỉ số, 3 biểu đồ có tooltip, nút lái tay, phím, d-pad |
| `ns3/scratch/uav_lte/wpf-ff-mac-scheduler.{h,cc}` | ~2500 (sao từ NS-3) | Scheduler | Bản sao `PfFfMacScheduler` của NS-3 3.47, đổi tên; thêm `SetDlWeight(rnti, w)` và nhân w vào chỉ số PF (1 dòng logic) |
| `ns3/scratch/uav_lte/uav-lte.cc` | ~580 | Kịch bản NS-3 | `AlHouraniPropagationLossModel`, đọc kế hoạch, dựng LTE + EPC, waypoint, handover, bộ phát UDP rate theo khe, đo từng khe, FlowMonitor; `RunIdeal` cho `link=ideal` (mục 12.7) |
| `experiments/plot_three_tier.py` | ~90 | Biểu đồ | Đọc `aggregate_ns3.csv` của một lần chạy `--link ideal` và một lần `--link lte`, vẽ 4 ô (throughput, min, delay, mất gói) và ghi bảng sai số từng tầng |
| `ns3/install.sh` | ~10 | Cài đặt | Gỡ symlink hỏng trong `scratch/`, symlink `uav_lte`, `./ns3 build uav-lte` |
| `tests/test_uavsim.py` | ~290 | Kiểm thử | Mục 13 |

**Luồng phụ thuộc** (không có vòng):
`config` ← `channel`, `energy` ← `network` ← `algorithms` ← `env`, `run` ← `animate`, `ns3`.
`ns3.py` gọi binary NS-3 qua subprocess (không cần Python bindings của NS-3, vốn đang tắt trong bản build).

---

## 11. Cách chạy và dữ liệu đầu ra

Mọi lệnh chạy từ thư mục `~/LapTrinhMang`. Dùng Python trong `.venv` (đã có numpy, matplotlib, gymnasium 1.0,
pytest).

### 11.1. So sánh thuật toán

```bash
# mọi baseline, 3 seed, tham số mặc định
.venv/bin/python -m uavsim.run

# chọn thuật toán, số seed, đổi tham số
.venv/bin/python -m uavsim.run --algos hover-equal kmeans-equal kmeans-maxmin --seeds 5 \
    --set num_uavs=5 --set num_users=40 --set environment=dense_urban --set rician_k_db=10

# đọc tham số từ JSON (khóa phải trùng tên trong SimConfig), --set ghi đè lên JSON
.venv/bin/python -m uavsim.run --config my_scenario.json --set seed=10 --out experiments/results/thu1
```

Tham số dòng lệnh:

| Tham số | Ý nghĩa |
|---|---|
| `--algos` | Danh sách tên trong `REGISTRY` (mặc định là tất cả) |
| `--seeds` | Số seed, chạy seed = base, base+1, … |
| `--set KEY=VAL` | Ghi đè tham số, lặp được nhiều lần. VAL được đọc như JSON (số, true/false, null); không phải JSON thì coi là chuỗi |
| `--config` | File JSON cấu hình |
| `--out` | Thư mục kết quả, mặc định `experiments/results/<thời gian>` |
| `--no-plot` | Bỏ qua vẽ biểu đồ |

Đầu ra trong thư mục `--out`:

| File | Nội dung |
|---|---|
| `config.json` | Cấu hình thực tế đã chạy, kèm danh sách thuật toán và số seed, để tái lập |
| `timeseries.csv` | `algo, seed, t, sum_rate, min_rate, jain, coverage, energy`: mỗi dòng một khe |
| `summary.csv` | `algo, seed, ...trung bình..., energy_eff`: mỗi dòng một episode |
| `compare.png` | Sum rate và min rate theo thời gian, quỹ đạo UAV (seed đầu tiên) |

### 11.2. Animation

```bash
.venv/bin/python -m uavsim.animate --algos hover-equal kmeans-equal random-equal \
    --set user_speed=3 --out experiments/results/anim.gif      # .mp4 cũng được (cần ffmpeg)
```

| Tham số | Ý nghĩa |
|---|---|
| `--algos` | Các thuật toán vẽ cạnh nhau, cùng kịch bản |
| `--every N` | Lấy 1 frame mỗi N khe (mặc định 2) |
| `--set`, `--out` | Như trên |

Cách đọc animation:
- **▲** là UAV, đường mờ là quỹ đạo đã bay;
- **●** là user, cùng màu với UAV phục vụ, chấm càng to thì rate càng cao;
- **×** là user dưới `r_min`;
- đường mảnh nối UAV với các user của nó;
- tiêu đề mỗi ô ghi khe hiện tại, sum rate, min rate và coverage.

### 11.3. Dùng trong code (notebook, script riêng)

```python
from uavsim.config import SimConfig
from uavsim.algorithms import REGISTRY
from uavsim.run import run_episode, summarize

cfg = SimConfig(num_uavs=4, channel="los", seed=7)
rows, traj = run_episode(cfg, REGISTRY["kmeans-maxmin"]())   # rows: list dict mỗi khe, traj: [N+1, M, 2]
print(summarize(rows, cfg))
```

### 11.4. Trạm điều khiển thời gian thực (`uavsim.live`)

```bash
.venv/bin/python -m uavsim.live [--gazebo] [--algo calib-ifair] [--dt 0.25] [--port 8000] [--set KEY=VAL]
```

**Kiến trúc:**

```
Trình duyệt (web/index.html)  ◄── WebSocket :8001 (JSON) ──►  live.Server (asyncio)
  vẽ 60 Hz, nội suy giữa 2 khe      lệnh: vel, goto, manual,       │ mỗi dt / tốc độ giây
  bản đồ, chỉ số, biểu đồ           algo, pause, resume, speed,    ▼
  lái tay, nhấp-bay-tới,            reset, config, measure      LiveSession.step()
  tham số, đo NS-3                                                thuật toán → Action
HTTP :8000 (trang tĩnh)                                           vận tốc UAV lái tay (phím hoặc điểm đến)
                                                                  Network.step; SINR → Shannon và LTE dự đoán
                                                                  PlanRecorder (khi đang đo)
                                                                   │                    │ đủ số khe
                              gz-transport, 20 Hz, nội suy ◄───────┘                    ▼
                              /world/multi_uav_world/set_pose_vector         ns3.replay (luồng riêng)
                              → Gazebo (chỉ hiển thị)                        → kết quả về web
```

| Thành phần | Vai trò |
|---|---|
| `live.LiveSession` | Trạng thái phiên, không phụ thuộc web: `Network` với số khe không giới hạn, thuật toán, UAV lái tay (vận tốc lệnh hoặc điểm đến), bản ghi. `step()` trả trạng thái JSON gồm tốc độ theo Shannon và theo LTE đã hiệu chỉnh, SINR từng user, tải từng UAV. `apply_config()` đổi tham số trong danh sách `EDITABLE` (có kiểm tra khoảng) rồi dựng lại kịch bản |
| `live.Server` | Vòng lặp mô phỏng, nhận lệnh, phát trạng thái. Lệnh sai chỉ bị từ chối. Không còn client thì UAV lái tay dừng. Phép đo: ghi `slots` khe từ khe 0, rồi chạy `ns3.replay` trong luồng riêng để vòng lặp không bị chặn |
| `live.Server.gazebo_loop` | Gửi vị trí nội suy giữa hai khe sang Gazebo 20 lần mỗi giây |
| `ns3.PlanRecorder`, `ns3.replay` | Ghi kế hoạch cùng định dạng thí nghiệm; phát lại trong NS-3 và trả throughput, min, độ trễ, mất gói của mô hình và NS-3 |
| `gazebo.*` | Vẽ đúng kịch bản của mô hình trên nền bãi `~/simulation/multi_uav`. World dựng sẵn bể 8 UAV (quadrotor khối cơ bản), 60 × 9 hình người (áo màu UAV phục vụ, đỏ = không được phục vụ) và vòng nhóm important/critical; model chưa dùng nằm ở độ cao −50 m, nên đổi số UAV, số user không cần khởi động lại Gazebo. Bản sao `disaster_site` bỏ 54 người có sẵn; tỷ lệ 1 m Gazebo = 10 m mô hình |
| `web/index.html` | Một file HTML, không thư viện ngoài, theo phong cách trạm điều khiển mặt đất (nền sáng, số liệu font mono, trạng thái dạng pill và badge) |

**Lái tay:** vận tốc lệnh thay cho `Action.velocity` của UAV đó; mô hình vẫn cắt về `v_max` và giữ UAV trong vùng.
Lệnh "bay tới" tính vận tốc hướng về điểm đến, khe cuối chỉ đi vừa đủ quãng còn lại rồi dừng. Liên kết, băng thông và
công suất vẫn do thuật toán quyết định.

**Dự đoán LTE trên dashboard:** cùng SINR của khe, tốc độ LTE = b_k·B·min(0.401·log₂(1+SINR), 3.514), tức ánh xạ đo
được từ thí nghiệm một liên kết (mục 14.4). Đây là số đặt cạnh Shannon để người xem thấy ngay khoảng chênh.

**Bản đồ SINR:** trình duyệt tính trên lưới 48 × 48 ô, mỗi ô là một user giả định gắn vào UAV mạnh nhất, nhiễu từ các
UAV còn lại đang phục vụ (cùng công thức Al-Hourani, xấp xỉ PSD như mô hình).

**Tham số đổi được từ web:** số UAV (1–8), số user (1–60), độ cao (20–300 m), công suất (0.05–5 W), lưu lượng
(0.1–20 Mbps/user), vận tốc tối đa (1–40 m/s), tốc độ đi bộ của user (0–5 m/s), seed, môi trường, phân bố user, bật
tắt nhiễu. Băng thông giữ 10 MHz để NS-3 LTE luôn chạy được.

### 11.5. Đo bằng NS-3

```bash
ns3/install.sh ~/simulation/ns-3.47                       # một lần: symlink + build kịch bản
.venv/bin/python -m uavsim.ns3 --algos hover-equal kmeans-equal kmeans-maxmin --set slots=60
.venv/bin/python -m uavsim.ns3 --algos kmeans-equal --scheduler rr --load 0.7 --seeds 3
```

Tham số riêng: `--scheduler pf|rr|wpf`, `--link lte|ideal`, `--load` (hệ số nhân rate kế hoạch, hoặc nhân demand khi
có `demand_mbps`), `--traces`, `--parallel`, `--timeout`. Đầu ra và cách đo được mô tả ở mục 12.

```bash
# ba tầng: cùng cấu hình, chạy một lần với liên kết lý tưởng và một lần với LTE, rồi vẽ
.venv/bin/python -m uavsim.ns3 --link ideal --set demand_mbps=1 --load 0.5 1 2 4 --out experiments/results/x-ideal
.venv/bin/python -m uavsim.ns3 --link lte   --set demand_mbps=1 --load 0.5 1 2 4 --out experiments/results/x-lte
.venv/bin/python experiments/plot_three_tier.py experiments/results/x-ideal experiments/results/x-lte three_tier.png
```

---

## 12. Đo bằng NS-3 LTE

### 12.1. Ý tưởng

Thuật toán vẫn ra quyết định trên mô hình Python. Toàn bộ quyết định của một episode, gọi là **kế hoạch**, được ghi
ra file. NS-3 dựng một mạng LTE (mô phỏng đầy đủ giao thức) với cùng hình học, cùng kênh, cùng công suất và băng thông, phát lại đúng kế
hoạch đó và **đo** những gì mô hình không có: overhead giao thức, hàng đợi, delay, mất gói, handover.

```
uavsim.ns3.export_plan ──► plan/uavs.csv, plan/users.csv
                               │
                               ▼
ns3.47-uav-lte-default (C++) ──► ns3_slots.csv, flowmon.xml, ns3.log
                               │
                               ▼
uavsim.ns3.ns3_metrics ──► compare_slots.csv, summary_ns3.csv, ns3_compare.png
```

Liên kết là **một chiều, offline**: NS-3 không phản hồi cho thuật toán trong lúc chạy. Với các baseline và với
cách đánh giá "học trên mô hình, kiểm chứng trên NS-3" thì như vậy là đủ. Nếu cần thuật toán phản ứng theo số đo
của NS-3 (vòng kín), phải dùng ns3-gym; việc này chưa làm.

### 12.2. Ánh xạ mô hình → NS-3

| Mô hình Python | NS-3 (`ns3/scratch/uav_lte/uav-lte.cc`) |
|---|---|
| UAV m ở (x, y, H) | Node eNB với `WaypointMobilityModel`; waypoint tại thời điểm `warmup + s·dt` là vị trí đầu khe s; giữa hai waypoint nội suy tuyến tính |
| User k ở (x, y, 0) | Node UE, cũng dùng waypoint (đi được nếu `user_speed > 0`) |
| Kênh Al-Hourani / LoS | Lớp `AlHouraniPropagationLossModel : PropagationLossModel` cài cùng công thức (`channel.py`), gắn qua `LteHelper::SetPathlossModelType` |
| Băng B, reuse 1 | `DlBandwidth = UlBandwidth` = số RB (10 MHz → 50 RB); mọi eNB cùng EARFCN nên LTE PHY tính nhiễu liên cell |
| p_max | `LteEnbPhy::TxPower = 10·log10(p_max·1000)` dBm, trải đều trên các RB |
| N₀ = −169 dBm/Hz | LTE dùng −174 dBm/Hz + `LteUePhy::NoiseFigure`, nên NF = −169 + 174 = 5 dB |
| Liên kết a_k | `LteHelper::Attach(ue, enb)` ở khe 0; khi kế hoạch đổi UAV phục vụ thì `LteHelper::HandoverRequest` (handover X2, cần EPC). Thuật toán handover tự động tắt (`NoOpHandoverAlgorithm`) để handover chỉ theo kế hoạch |
| Cấp phát b_k, rate r_k | Mỗi UE nhận một luồng UDP downlink từ remote host, **rate gửi trong khe s = r_k[s] × load**. Việc chia RB do MAC scheduler LTE quyết định (`pf` = Proportional Fair, `rr` = Round Robin). Với `wpf`, b_k thành trọng số của scheduler Weighted PF (mục 14.7), nên quyết định chia băng thông được áp ở tầng MAC |
| Khe thời gian | Đầu mỗi khe: đặt rate mới và handover nếu cần. Cuối mỗi khe: ghi số đo rồi reset bộ đếm |

Mạng IP đầy đủ: remote host ↔ (P2P 10 Gb/s, 1 ms) ↔ PGW ↔ EPC ↔ eNB ↔ UE. Gói UDP payload 1200 byte, mang
`SeqTsHeader` (số thứ tự + thời điểm gửi).

### 12.3. Đo lường

Bộ phát là một hàm tự viết (`SendPacket`/`SetRate`) thay vì `UdpClient`, vì `UdpClient` chỉ áp dụng `Interval` mới
sau khi gói đang chờ đã gửi, nên không đổi rate tức thì đúng đầu khe được. Mỗi khi đổi rate, thời điểm gửi gói đầu
tiên được lệch pha ngẫu nhiên, để các luồng không gửi đồng loạt.

Bên nhận là `UdpServer`. Trace `RxWithAddresses` được gọi trước khi header bị gỡ, nên đọc được `SeqTsHeader` để tính
delay = thời điểm nhận − thời điểm gửi.

Số đo mỗi khe × mỗi UE (`ns3_slots.csv`):

| Cột | Ý nghĩa |
|---|---|
| `plan_cell` | UAV phục vụ theo kế hoạch |
| `actual_cell` | Cell mà UE thực sự đang gắn vào (`LteUeRrc::GetCellId() − 1`), để kiểm tra handover có thành công không |
| `tx_pkts`, `rx_pkts`, `rx_bytes` | Gói gửi, gói nhận, byte payload nhận trong khe |
| `delay_sum_s` | Tổng delay của các gói nhận trong khe |

Chỉ số tính ra (`uavsim/ns3.py: ns3_metrics`), cùng tên với chỉ số mô hình để đặt cạnh nhau:
- throughput_k = rx_bytes·8 / dt;
- `sum_rate`, `min_rate`, `jain`, `coverage` tính trên throughput đo được;
- `delay_ms` = Σ delay / Σ gói nhận;
- `loss` = 1 − Σ nhận / Σ gửi;
- `cell_match` = tỷ lệ UE gắn đúng cell kế hoạch.

Lưu ý: gói gửi cuối khe s nhưng nhận ở khe s+1 được tính vào khe nhận. Vì vậy `loss` của từng khe chỉ là xấp xỉ.
Trên cả episode, `loss` tính cả các gói còn trong hàng đợi lúc kết thúc là mất; `model_loss` của mô hình được tính
theo cùng định nghĩa (mục 3.6).

`flowmon.xml` (FlowMonitor) chứa thống kê từng luồng IP trên cả episode, dùng để đối chiếu.

### 12.4. Thông số NS-3 suy ra từ `SimConfig`

| Tham số NS-3 | Lấy từ |
|---|---|
| `numUavs`, `numUsers`, `slots`, `dt`, `altitude`, `fc`, `channel`, `beta0Db` | Trùng tên trong SimConfig |
| `rb` | `bandwidth` (1.4/3/5/10/15/20 MHz → 6/15/25/50/75/100 RB); băng khác bị từ chối |
| `a`, `b`, `etaLos`, `etaNlos` | Bảng `ENVIRONMENTS[environment]` |
| `txPowerDbm` | `p_max` |
| `noiseFigure` | `noise_psd_dbm + 174` |
| `seed` | `seed + 1` (RngRun của NS-3, phải ≥ 1) |
| `scheduler`, `load` | Tham số dòng lệnh của `uavsim.ns3` |
| `warmup` | 0.5 s cố định, để EPC gắn UE và lập bearer xong trước khe 0 |
| `reuse1` | `interference`: `true` thì mọi eNB cùng EARFCN; `false` thì eNB m dùng DL EARFCN 100 + 2·rb·m (UL +18000), tức các kênh liền kề không chồng lấn |
| `traces` | Cờ `--traces` của `uavsim.ns3` (chỉ với `link=lte`) |
| `link` | Cờ `--link`: `lte` (mặc định) hoặc `ideal` (mục 12.7) |
| `bufferBytes` | `buffer_bytes`: `LteRlcUm::MaxTxBufferSize` khi `lte`, hàng đợi DropTail khi `ideal` |

**Trace LTE (`--traces`).** NS-3 ghi `DlRsrpSinrStats.txt` (SINR từng UE, đơn vị giây), `DlRxPhyStats.txt` (mỗi khối
truyền nhận được: MCS, kích thước, rv, đúng/sai; **thời gian theo ms**) và `DlMacStats.txt` (mỗi lần scheduler cấp
phát). `uavsim/ns3.py: trace_stats` tính trong khoảng đo:
- SINR p10, trung vị, p90 (dB);
- MCS trung bình của lần truyền đầu;
- tỷ lệ lỗi khối lần đầu, tỷ lệ khối là truyền lại HARQ (rv > 0);
- số cell có lưu lượng, và tỷ lệ TTI mà các cell đó có cấp phát;
- goodput PHY (khối nhận đúng);
- hiệu suất phổ mỗi cell có lưu lượng.

Các file trace có thể nén gzip; hàm đọc tự tìm file `.gz`.

Khi không có `demand_mbps` và `link=lte`, `uavsim.ns3` đặt `rate_model="lte"` (trừ khi `--set rate_model=...` ghi đè),
vì NS-3 gửi đúng rate kế hoạch mà rate Shannon thuần vượt xa năng lực LTE. Khi có `demand_mbps`, hoặc khi `link=ideal`,
mô hình giữ Shannon như paper.

### 12.5. Kiểm chứng pipeline

Phép kiểm chứng: gửi **ít hơn** năng lực mạng. Khi đó NS-3 phải nhận đủ, tức throughput bằng rate gửi, gần như
không mất gói, và delay chỉ là delay truyền cộng xử lý.

| Run (seed 0, PF) | Kế hoạch × load | NS-3 đo được | Delay | Mất gói | Handover |
|---|---|---|---|---|---|
| hover-equal, 10 khe, load 0.5 | 27.0 Mbps | 27.0 Mbps | 10 ms | 0.1% | 0 |
| hover-equal, 10 khe, load 1.0 | 54.0 Mbps | 39.9 Mbps | 1241 ms | 26% | 0 |
| kmeans-equal, 25 khe, load 1.0 | 78.8 Mbps | 60.9 Mbps | 1730 ms | 23% | 2/2 thành công, cell_match 100% |

Test `test_ns3_replay_low_load_matches_plan` tự động hóa phép kiểm chứng này với tải 30%.

Ở tải 100%, kế hoạch của mô hình LTE vượt năng lực đo được trong NS-3. Mục 14.4 kiểm chứng rằng nguyên nhân nằm ở
ánh xạ SINR → throughput của LTE: so với công thức 36.942 (α = 0.6, trần 4.4), LTE 10 MHz SISO trong NS-3 tương đương
α ≈ 0.40 và trần ≈ 3.51 bit/s/Hz. Kênh, nhiễu và HARQ không phải nguyên nhân. Phần dư không truyền kịp tích lại trong hàng đợi RLC, nên delay lên tới cỡ giây và mất
gói khi buffer đầy. Đây là kết quả đo, không phải lỗi. Ma trận thí nghiệm ở mục 14.2 định lượng chính xác khoảng
cách này (khoảng 70%) và hệ số an toàn (0.5–0.6).

### 12.6. Giới hạn của phần NS-3

- **Cấp phát băng thông:** với `pf`/`rr`, b_k chỉ áp ở tầng ứng dụng (tải gửi), việc chia RB do scheduler quyết
  định. Với `wpf` (mục 14.7), b_k là trọng số của Weighted PF: phần tài nguyên tỷ lệ b_k về lâu dài, không đúng tuyệt
  đối từng TTI. Công suất p_k chưa áp: eNB trải công suất đều trên các RB.
- **Lệch nhỏ về thời gian:** NS-3 nội suy vị trí UAV tuyến tính bên trong khe, còn mô hình Python tính rate tại vị trí
  đầu khe.
- **Lớp vật lý đơn giản:** antenna đẳng hướng, SISO, không fading nhỏ (`rician_k_db` chỉ có trong mô hình Python),
  không có shadowing.
- **Hướng truyền:** chỉ đo downlink; uplink chỉ mang tín hiệu điều khiển.
- **Chi phí thời gian:** khoảng 1.8 s cho mỗi khe với 3 eNB và 20 UE. `--parallel` chạy song song nhiều run.
  Chế độ `ideal` nhanh hơn khoảng 20 lần (60 khe, 20 user: khoảng 14 s).

### 12.7. Chế độ liên kết lý tưởng (`--link ideal`)

**Mục đích:** kiểm chứng riêng mô hình hàng đợi của lý thuyết ở mức gói tin, tách khỏi các hiệu ứng của LTE.

**Cách dựng** (`uav-lte.cc: RunIdeal`):
- Bỏ toàn bộ LTE/EPC. Remote host nối với mỗi UE bằng một liên kết điểm-điểm riêng, delay truyền 0.
- Đầu mỗi khe, tốc độ liên kết của user k đặt bằng `cap_bps` = tốc độ phục vụ lý thuyết r_k của khe đó (cột mới trong
  `users.csv`, lấy từ `capacity` của mô hình). Tốc độ trên dây được nâng thêm (1200 + 30)/1200 để bù header
  UDP/IP/PPP, nên goodput payload đúng bằng r_k.
- Hàng đợi DropTail của thiết bị có kích thước `buffer_bytes`, cũng nâng theo tỷ lệ header vì thiết bị đếm cả header.
  Qdisc mặc định của traffic-control bị gỡ (sau `Assign`, vì `Assign` tự cài lại), nên chỉ còn đúng một hàng đợi
  như mô hình.
- Bộ phát UDP, cách đo và file `ns3_slots.csv` giống hệt chế độ LTE; `actual_cell` = `plan_cell`.
- Không có hình học, kênh, nhiễu hay handover: tất cả đã nằm trong r_k do mô hình tính.

Chế độ này chỉ có ý nghĩa khi có `demand_mbps`. Không có demand thì lưu lượng gửi bằng đúng tốc độ liên kết, hàng
đợi luôn rỗng.

---

## 13. Kiểm thử

```bash
.venv/bin/python -m pytest -q tests        # 46 passed
```

| Test | Kiểm tra điều gì |
|---|---|
| `test_los_channel_matches_beta0_over_d2` | Kênh LoS cho đúng β₀/d² (ngay dưới UAV, d = 100 m thì g = 10⁻¹⁰) |
| `test_al_hourani_los_prob_grows_with_elevation_and_adds_excess_loss` | P_LoS tăng theo góc nâng; suy hao Al-Hourani > FSPL |
| `test_rotary_power_known_points` | P(0) = P₀ + P_i = 168.49 W; vận tốc tiết kiệm nhất trong khoảng 8–14 m/s |
| `test_single_link_rate_is_shannon` | 1 UAV, 1 user, không nhiễu: rate đúng bằng B·log₂(1+SNR) |
| `test_interference_lowers_rate` | Bật nhiễu thì rate không tăng và tổng rate giảm thực sự |
| `test_infeasible_action_rejected` | Σb > 1 hoặc Σp > P_max thì báo lỗi |
| `test_velocity_clipped_and_uav_stays_in_area` | Vận tốc bị co về v_max; UAV không ra khỏi vùng |
| `test_registry_algorithms_feasible_and_deterministic` (×6) | Mọi baseline cho Action hợp lệ, có user di chuyển và fading, chạy lại cho kết quả giống hệt |
| `test_maxmin_equalizes_rates_within_uav_without_interference` | maxmin cho rate bằng nhau khi không nhiễu (kiểm chứng phần suy ra ở mục 7.2) |
| `test_kmeans_mobility_improves_rate_over_hover` | kmeans cho sum rate cao hơn hover (kiểm tra hợp lý) |
| `test_gym_env_passes_checker` | `UavBsEnv` qua `gymnasium.utils.env_checker.check_env`; episode dài đúng `slots` |
| `test_lte_rate_model_is_capped_shannon` | `rate_model=lte` đúng 0.6·log₂(1+SNR) và không vượt 4.4 bit/s/Hz |
| `test_ns3_replay_low_load_matches_plan` | Chạy binary NS-3 (2 UAV, 4 UE, 4 khe, tải 30%): throughput = 0.3 × kế hoạch ±10%, mất gói < 2%, cell khớp 100%. Tự bỏ qua nếu chưa build NS-3 |
| `test_ns3_rejects_non_lte_bandwidth` | Băng thông không phải băng LTE thì báo lỗi |
| `test_ns3_traces_and_separate_channels` | 2 UAV, mỗi UAV 3 user: trace cho MCS, tỷ lệ lỗi khối hợp lệ; goodput PHY ≥ payload UDP; kênh riêng cho SINR trung vị cao hơn kênh chung ít nhất 3 dB |
| `test_fit_alpha_cap_recovers_known_curve` | `fit_alpha_cap` khôi phục đúng α = 0.4, trần = 3.5 từ đường cong sinh sẵn |
| `test_lte_alpha_and_cap_are_configurable` | `lte_alpha`, `lte_se_max` trong SimConfig được dùng khi tính rate |
| `test_queue_step_underload_and_overload` | Thiếu tải: không tồn đọng, không mất. Quá tải: hàng đợi bằng bộ đệm, mất đúng phần dư |
| `test_network_demand_gives_delay_and_loss` | Demand thấp: không mất, delay < 50 ms. Demand cao: mất > 50%, delay lớn hơn; throughput không vượt năng lực |
| `test_export_plan_sends_demand` | Có `demand_mbps` thì kế hoạch gửi NS-3 dùng đúng demand |
| `test_waterfill_max_min` | Water-filling max-min: không cấp quá nhu cầu, phần dư chia đều |
| `test_work_conserving_never_worse_than_static` | Chia linh hoạt không mất gói nhiều hơn, throughput không thấp hơn chia tĩnh |
| `test_load_coupled_interference_lowers_at_light_load` | Nhiễu theo tải: khe đầu giống nhiễu tối đa, các khe sau năng lực cao hơn khi tải nhẹ |
| `test_fifo_delay_exact` | Đến 2 bit/s, phục vụ 1 bit/s một khe rồi ngừng đến: delay trung bình 0.25 s khe đầu, 0.75 s khe sau, đúng lời giải tay |
| `test_ns3_ideal_link_matches_queue_model` | NS-3 `link=ideal`, tải gấp đôi: throughput ±1%, min ±2%, mất gói ±0.5 điểm %, delay ±3% so với mô hình |
| `test_live_manual_override_and_recording` | UAV lái tay đi đúng 20 m/khe khi lệnh 30 m/s (cắt về v_max), UAV hover đứng yên; phiên ghi ra `config.json` và `users.csv` đúng định dạng; UAV không tồn tại bị từ chối |
| `test_gazebo_world_follows_model` | Bản sao bãi bỏ hết người nhưng giữ nhà; world thêm đúng M UAV và K user của mô hình, tâm vùng ở tâm bãi, tỷ lệ 1:10, user không có va chạm. Tự bỏ qua nếu không có `~/simulation/multi_uav` |
| `test_wpf_scheduler_shares_resources_by_weight` | NS-3: 2 UE cùng chỗ, trọng số 0.8/0.2, bão hòa. `wpf` cho tỷ lệ throughput 4 ± 10%, `pf` cho 1 ± 5%, tổng bằng nhau ± 2% |

---

## 14. Kết quả

Hai loại số liệu trong mục này khác bản chất:
- **14.1** là kết quả *tính* theo công thức giải tích (mô hình Python, Shannon thuần), giống phần "Simulation results"
  của đa số paper;
- **14.2** là kết quả *đo* bằng mô phỏng giao thức LTE trong NS-3.

Năng lượng bay luôn là số liệu mô hình (Zeng 2019), vì NS-3 không mô phỏng động cơ UAV.

### 14.1. Mô hình (tính theo công thức)

Cấu hình mặc định (3 UAV, 20 user phân cụm, urban, 200 khe, `rate_model=shannon`), 3 seed, trung bình ± độ lệch
chuẩn:

| Thuật toán | Sum rate (Mbps) | Min rate (Mbps) | Jain | Coverage | Năng lượng (J/khe) | Hiệu suất (kbit/J) |
|---|---|---|---|---|---|---|
| hover-equal | 87 ± 38 | 0.71 ± 0.06 | 0.47 | 77% | 505.5 | 173 |
| hover-maxmin | 76 ± 30 | 0.84 ± 0.11 | 0.51 | 80% | 505.5 | 151 |
| kmeans-equal | 145 ± 22 | 1.85 ± 0.52 | 0.71 | 99.4% | 507.8 | 285 |
| kmeans-maxmin | 143 ± 22 | 1.90 ± 0.55 | 0.72 | 99.6% | 507.8 | 281 |
| random-equal | 97 ± 33 | 1.01 ± 0.24 | 0.64 | 89% | 534.9 | 181 |
| random-maxmin | 89 ± 31 | 1.25 ± 0.29 | 0.69 | 93% | 534.9 | 166 |

Nhận xét của mô hình (chỉ đúng với mô hình và cấu hình này):

1. **Di chuyển có định hướng là yếu tố chi phối.** So với hover, kmeans tăng sum rate khoảng 1.7 lần, min rate khoảng
   2.6 lần, coverage từ 77% lên khoảng 99%, mà năng lượng gần như không đổi: UAV bay khoảng 15 khe đầu rồi hover.
2. **`maxmin` đổi sum rate lấy công bằng:** min rate và Jain tăng, sum rate giảm nhẹ. Đây là đánh đổi kinh điển.
3. **Bay ngẫu nhiên tốn năng lượng nhất** (luôn bay ở v_max, 178 W so với 168.5 W khi hover) mà vẫn kém kmeans xa.
4. **Nhiễu đồng kênh có tác động rõ.** Trước khi sửa lỗi cụm rỗng, một UAV của kmeans đứng không ở góc và sum rate
   là 169 Mbps. Sau khi sửa, UAV đó bay vào phục vụ nhưng gây nhiễu cho UAV bên cạnh, nên sum rate giảm còn
   145 Mbps (min rate cũng giảm). **Thêm UAV hoạt động không tự động tốt hơn** khi các UAV dùng chung băng tần.
   Đây chính là khoảng trống để thuật toán thông minh hơn (quản lý nhiễu, liên kết cân bằng tải, DRL) thể hiện ưu
   thế.
5. Độ lệch chuẩn giữa seed lớn (±20–40%) vì mỗi seed là một bản đồ user khác nhau. Muốn kết luận chắc chắn cần nhiều
   seed hơn (≥ 20).

### 14.2. NS-3 LTE (đo bằng mô phỏng mức gói tin)

**Cấu hình ma trận:**
- 3 thuật toán (hover-equal, kmeans-equal, kmeans-maxmin) × 6 mức load (0.5, 0.6, 0.7, 0.8, 0.9, 1.0) × 5 seed (0–4)
  = 90 run;
- mỗi run 60 khe × 1 s, scheduler PF;
- tham số còn lại như mục 14.1, kế hoạch tính với `rate_model=lte`.

Lệnh tái lập:

```bash
.venv/bin/python -m uavsim.ns3 --algos hover-equal kmeans-equal kmeans-maxmin \
    --load 0.5 0.6 0.7 0.8 0.9 1.0 --seeds 5 --set slots=60 --parallel 10 --out experiments/results/ns3-matrix
```

**Thực thi:** 90/90 run thành công, khoảng 36 phút với 10 run song song trên máy 12 nhân. Mọi handover đều thành
công (0, 2, 5, 8 hoặc 18 lần mỗi run tùy thuật toán và seed), `cell_match` = 100% ở mọi run.

**Bảng tổng hợp** (`experiments/results/ns3-matrix/aggregate_ns3.csv`), trung bình ± độ lệch chuẩn qua 5 seed:

| Thuật toán | Load | Kế hoạch × load (Mbps) | NS-3 (Mbps) | Chuyển được | Delay | Mất gói | Min (Mbps) | Jain |
|---|---|---|---|---|---|---|---|---|
| hover-equal | 0.5 | 22.6 | 22.6 ± 9.0 | 100% | 11 ms | 0.03% | 0.23 | 0.52 |
| | 0.6 | 27.2 | 27.0 ± 11 | 99.6% | 130 ms | 0.5% | 0.25 | 0.51 |
| | 0.7 | 31.7 | 30.0 ± 12 | 94% | 1.5 s | 5.8% | 0.26 | 0.50 |
| | 0.8 | 36.2 | 31.6 ± 14 | 86% | 3.0 s | 14% | 0.26 | 0.49 |
| | 0.9 | 40.7 | 31.6 ± 14 | 76% | 4.0 s | 24% | 0.26 | 0.49 |
| | 1.0 | 45.3 | 31.6 ± 14 | 69% | 4.5 s | 31% | 0.26 | 0.49 |
| kmeans-equal | 0.5 | 37.1 | 37.1 ± 8.1 | 100% | 9 ms | 0.02% | 0.48 | 0.71 |
| | 0.6 | 44.6 | 44.4 ± 9.8 | 99.6% | 80 ms | 0.4% | 0.55 | 0.70 |
| | 0.7 | 52.0 | 50.0 ± 11 | 96% | 0.8 s | 4.1% | 0.57 | 0.69 |
| | 0.8 | 59.4 | 52.8 ± 13 | 88% | 1.8 s | 12% | 0.57 | 0.68 |
| | 0.9 | 66.8 | 52.8 ± 13 | 79% | 2.5 s | 21% | 0.57 | 0.68 |
| | 1.0 | 74.3 | 52.8 ± 13 | 71% | 2.6 s | 29% | 0.57 | 0.68 |
| kmeans-maxmin | 0.5 | 36.5 | 36.5 ± 7.9 | 99.9% | 20 ms | 0.12% | 0.51 | 0.72 |
| | 0.6 | 43.8 | 43.2 ± 9.3 | 98.6% | 233 ms | 1.4% | 0.55 | 0.71 |
| | 0.7 | 51.1 | 48.5 ± 11 | 95% | 0.8 s | 5.3% | 0.57 | 0.69 |
| | 0.8 | 58.4 | 51.7 ± 12 | 88% | 1.6 s | 12% | 0.57 | 0.68 |
| | 0.9 | 65.7 | 52.5 ± 13 | 80% | 2.3 s | 20% | 0.57 | 0.68 |
| | 1.0 | 73.0 | 52.7 ± 13 | 72% | 2.5 s | 28% | 0.57 | 0.68 |

"Chuyển được" = throughput NS-3 / lượng thực gửi vào mạng (kế hoạch × load). Biểu đồ: `ns3_matrix.png`. Số liệu
từng run: `summary_ns3.csv`.

**So sánh cặp trên cùng seed.** Độ lệch chuẩn của throughput tuyệt đối lớn (±8–14 Mbps) vì mỗi seed là một bản đồ
user khác. Vì vậy so sánh giữa các thuật toán dùng tỷ lệ trên cùng seed, kèm số seed mà thuật toán thứ nhất cao hơn:

| So sánh | Load | Throughput tổng | Min throughput | Jain | Delay | Mất gói |
|---|---|---|---|---|---|---|
| kmeans-equal / hover-equal | 0.5 | 1.95× (4/5) | 2.20× (5/5) | 1.47× (5/5) | 0.83× | 1.20× |
| | 1.0 | 2.06× (4/5) | 2.24× (5/5) | 1.52× (5/5) | 0.67× | 0.94× |
| kmeans-maxmin / kmeans-equal | 0.5 | 0.98× (0/5) | 1.06× (4/5) | 1.01× (4/5) | **2.26× (5/5)** | **5.5× (5/5)** |
| | 1.0 | 1.00× | 1.00× | 1.00× | 0.96× | 0.96× |

Trong ngoặc là số seed mà thuật toán đứng trước có giá trị lớn hơn.

**Nhận xét** (chỉ đúng với mô hình và cấu hình này):

1. **Mô hình đánh giá cao hơn LTE khoảng 30%.** Throughput NS-3 bão hòa từ load 0.8 trở lên, ở khoảng 32 Mbps
   (hover) và 53 Mbps (kmeans). Ở load 1.0, tỷ lệ chuyển được là 65–75% tùy seed, trung bình 69–72%. Như vậy năng
   lực LTE đo được bằng khoảng 70% công thức Shannon cắt ngọn 3GPP 36.942. So với Shannon thuần (mục 14.1), khoảng
   cách còn lớn hơn nhiều.
2. **Điểm vận hành an toàn là gửi 50–60% kế hoạch.**
   - Load 0.5: chuyển được ≥ 99.9%, delay 9–20 ms.
   - Load 0.6: vẫn chuyển được ≥ 98.6%, nhưng delay đã 80–233 ms, tức bắt đầu có hàng đợi.
   - Từ load 0.7: delay lên cỡ giây, mất gói tăng nhanh.

   Đường cong delay có "khuỷu" rõ giữa 0.6 và 0.7, đúng dạng của hệ thống hàng đợi khi tải tiến tới năng lực phục vụ.
3. **NS-3 xác nhận kết luận chính của mô hình: di chuyển UAV về phía user có lợi.**
   - kmeans hơn hover ở min throughput (khoảng 2.2×) và Jain (khoảng 1.5×) trên cả 5/5 seed.
   - Throughput tổng trung bình gấp khoảng 2× nhưng chỉ thắng 4/5 seed. Ở một seed, hover hơn khoảng 10%, phù hợp với
     nhận xét 4 của mục 14.1: UAV bay vào cụm có thể tăng nhiễu đồng kênh.
4. **Kết luận của mô hình về maxmin không còn đúng ở tầng giao thức.**
   - Mô hình nói maxmin đổi một ít sum rate lấy min rate cao hơn. Trong NS-3, ở load 0.5, min throughput chỉ tăng
     khoảng 6%, trong khi delay gấp 2.3 lần và mất gói gấp 5.5 lần (5/5 seed). Lý do: maxmin dồn lưu lượng cho user
     sóng yếu, mà đó lại là những user có năng lực LTE thấp hơn mô hình nhiều nhất (SINR thấp, MCS thấp, overhead
     tương đối lớn), nên hàng đợi của họ đầy trước.
   - Ở load 1.0, hai thuật toán cho kết quả trùng nhau (tỷ lệ 1.00), vì scheduler PF của LTE tự chia lại resource
     block bất kể lưu lượng được gửi theo tỷ lệ nào.
   - Kết luận: **cấp phát băng thông chỉ ở tầng ứng dụng không thay thế được cấp phát ở tầng MAC.** Muốn maxmin có
     tác dụng phải cài scheduler LTE theo tỷ lệ b_k.
5. **Min throughput bão hòa sớm hơn tổng:** từ load 0.7, min đứng yên ở khoảng 0.57 Mbps (kmeans) và 0.26 Mbps
   (hover), vì user kém nhất đã chạm năng lực của nó trước các user khác.

### 14.3. Tách nguyên nhân: nhiễu và trần LTE (NS-3 + trace)

**Câu hỏi:** vì sao throughput NS-3 chỉ đạt khoảng 70% mô hình (mục 14.2)?

**Thiết kế:** kmeans-equal, load 1.0, 30 khe, seed 0–2, `--traces`. Ba cấu hình:
- **A:** 3 UAV dùng chung tần số, giống 14.2;
- **B:** 3 UAV, mỗi UAV một kênh 10 MHz riêng (`interference=false`). Cùng user, cùng quỹ đạo với A, chỉ khác tần số;
- **C:** 1 UAV (`num_uavs=1`). Layout `clustered` sinh 1 cụm user, nên bản đồ user khác A/B; C dùng làm mốc "một cell
  không nhiễu".

```bash
R=experiments/results/ns3-interference
.venv/bin/python -m uavsim.ns3 --algos kmeans-equal --seeds 3 --traces --set slots=30 --out $R/A_3uav_chung_tan_so
.venv/bin/python -m uavsim.ns3 --algos kmeans-equal --seeds 3 --traces --set slots=30 --set interference=false --out $R/B_3uav_tan_so_rieng
.venv/bin/python -m uavsim.ns3 --algos kmeans-equal --seeds 3 --traces --set slots=30 --set num_uavs=1 --out $R/C_1uav
```

**Kết quả** (trung bình 3 seed):

| | A. chung tần số | B. tần số riêng | C. 1 UAV |
|---|---|---|---|
| Tổng phổ | 10 MHz | 30 MHz | 10 MHz |
| Mô hình LTE (Mbps) | 76.3 | 103.9 | 43.4 |
| NS-3 payload UDP (Mbps) | 57.1 ± 11 | 80.8 ± 16 | 33.7 ± 0.3 |
| NS-3 goodput PHY (Mbps) | 58.6 | 83.1 | 34.6 |
| NS-3 / mô hình | 0.75 | 0.78 | 0.78 |
| SINR p10 / trung vị / p90 (dB) | 5.7 / 19.7 / 29.0 | 28.3 / 42.0 / 48.8 | 23.0 / 38.7 / 48.6 |
| MCS trung bình lần đầu | 21.7 | 28.0 | 27.8 |
| Lỗi khối lần đầu | 0.06% | 0.02% | 0.05% |
| Tỷ lệ truyền lại HARQ | 0.06% | 0.02% | 0.05% |
| Hiệu suất phổ mỗi cell (bit/s/Hz) | 2.19 | 3.16 | 3.46 |
| Min throughput (Mbps) | 0.65 | 2.91 | 1.57 |
| Delay (s, quá tải) | 1.9 | 1.6 | 3.1 |

Ở seed 0, một UAV chưa phục vụ ai trong phần đầu episode (`cell_busy_frac` = 0.7), làm hiệu suất phổ trung bình của B
thấp đi; ở seed 1–2 là 3.49 và 3.52 bit/s/Hz.

**Phân tích:**

1. **Trần LTE 10 MHz SISO ≈ 3.5 bit/s/Hz mỗi cell.** Khi không có nhiễu (B, C), SINR trung vị ≈ 40 dB và gần như mọi
   khối truyền ở MCS 28, tức mức cao nhất. Throughput lúc đó bị chặn bởi bảng TBS của 3GPP (khoảng 35–36 Mbps mỗi
   cell, đã trừ overhead PDCCH và tín hiệu tham chiếu). Công thức 36.942 cho phép tới 4.4 bit/s/Hz; 3.5 / 4.4 ≈ 0.79,
   gần với tỷ lệ 0.78 đo được ở B và C. Mục 14.4 kiểm chứng đầy đủ: ngoài trần, độ dốc của LTE cũng thấp hơn.
2. **HARQ không phải nguyên nhân.** Tỷ lệ lỗi khối và truyền lại dưới 0.1%: AMC của NS-3 chọn MCS đủ an toàn, vị trí
   UAV thay đổi chậm so với chu kỳ báo CQI. Giả thuyết trước đây rằng HARQ và CQI cũ góp phần đáng kể là không đúng
   với cấu hình này.
3. **Nhiễu đồng kênh làm giảm năng lực tuyệt đối** (ở cả mô hình lẫn NS-3). So A với B (cùng user, cùng quỹ đạo):
   - SINR trung vị giảm khoảng 22 dB, p10 giảm từ 28 xuống 6 dB;
   - MCS trung bình giảm từ 28 xuống 21.7, hiệu suất phổ mỗi cell giảm khoảng 37%;
   - throughput tổng giảm khoảng 30% (57 so với 81 Mbps), min throughput giảm khoảng 4.5 lần.

   User ở rìa cụm chịu thiệt nhiều nhất.
4. **Dùng chung tần số vẫn hiệu quả hơn tính trên tổng phổ:** A đạt 57 Mbps / 10 MHz = 5.7 bit/s/Hz, còn B đạt
   81 Mbps / 30 MHz = 2.7 bit/s/Hz. Nói cách khác, chia tần số giúp công bằng hơn (min ×4.5), nhưng tốn gấp 3 lần phổ
   để tăng throughput 42%.
5. **Mô hình nhiễu PSD tương đối tốt:** tỷ lệ NS-3/mô hình ở A (0.75) chỉ thấp hơn B (0.78) khoảng 3 điểm phần trăm.
   Mục 14.4 so SINR từng user và xác nhận điều này.
6. **Overhead header** giữa goodput PHY và payload UDP khoảng 2.5–3%.

### 14.4. Kiểm chứng nguyên nhân chênh lệch mô hình–NS-3

**Câu hỏi:** chênh lệch 22–30% giữa mô hình (công thức 36.942) và NS-3 đến từ đâu? Có bốn giả thuyết: (a) kênh
Al-Hourani cài khác nhau ở hai bên, (b) mô hình tính nhiễu sai, (c) HARQ và lỗi truyền, (d) ánh xạ SINR → throughput
của LTE khác công thức.

**Phương pháp:** cô lập từng yếu tố (`uavsim/validate.py`). Nếu giả thuyết đúng, thì căn chỉnh đúng yếu tố đó phải
làm khoảng chênh biến mất.

```bash
.venv/bin/python -m uavsim.validate --runs experiments/results/ns3-interference/A_3uav_chung_tan_so \
    experiments/results/ns3-interference/B_3uav_tan_so_rieng experiments/results/ns3-interference/C_1uav
```

Kết quả: `experiments/results/validation/` (`link_curve.csv`, `calibration.csv`, `fit.json`, `validation.png`).

**Kiểm chứng 1: đường cong một liên kết** (`link_point`). Đặt 1 UAV ở (500, 500, 100 m), 1 user cách ngang 100 m,
không nhiễu. User nhận UDP 200 Mbps (bão hòa) trong 6 khe; khe 0 bị bỏ vì hàng đợi đang lấp đầy. Quét công suất eNB
−40…30 dBm (bước 5) để SINR chạy từ −24 đến 46 dB. Ghi SINR (trace), MCS, lỗi khối và goodput PHY.

| SINR NS-3 (dB) | SNR mô hình (dB) | MCS | Lỗi khối | SE NS-3 (bit/s/Hz) | SE 36.942 | Tỷ lệ |
|---|---|---|---|---|---|---|
| −24.1, −19.1, −14.1 | giống hệt | — | — | 0: UE mất kết nối (`actual_cell = -1`) | 0 | — |
| −9.1 | −9.1 | 0 | 100% | 0 | 0.10 | 0 |
| −4.1 | −4.1 | 0 | 0 | 0.12 | 0.28 | 0.43 |
| 0.9 | 0.9 | 6 | 0 | 0.50 | 0.69 | 0.72 |
| 5.9 | 5.9 | 10 | 0 | 0.75 | 1.37 | 0.55 |
| 10.9 | 10.9 | 16 | 0 | 1.47 | 2.23 | 0.66 |
| 15.9 | 15.9 | 22 | 0 | 2.21 | 3.18 | 0.69 |
| 20.9 | 20.9 | 28 | 0 | 3.51 | 4.16 | 0.84 |
| 25.9 … 45.9 | giống hệt | 28 | 0 | 3.51 | 4.40 | 0.80 |

Khớp `SE = min(α·log₂(1+SINR), trần)` (`fit_alpha_cap`: trần = SE lớn nhất đo được; α bình phương tối thiểu trên các
điểm SINR > −5 dB chưa bão hòa) cho **α = 0.401, trần = 3.514 bit/s/Hz**.

Nhận xét:
- SINR NS-3 = SNR mô hình tới 0.1 dB ở mọi điểm, nên **giả thuyết (a) bị bác bỏ**.
- NS-3 thấp hơn 36.942 ở *mọi* SINR, không chỉ ở vùng trần:
  - **Độ dốc thấp hơn** (α 0.40 so với 0.6): bảng CQI/MCS rời rạc. Lỗi khối luôn 0% trong khi BLER mục tiêu của AMC là
    10%, cho thấy mô hình AMC của NS-3 giữ biên an toàn, tức chọn MCS thấp hơn mức kênh chịu được. Đây là suy luận từ
    BLER, chưa đối chiếu với mã nguồn AMC.
  - **Trần thấp hơn** (3.51 so với 4.4): MCS 28, 50 RB, SISO, bảng TBS đã trừ vùng điều khiển và tín hiệu tham chiếu.
  - **Ngưỡng mất kết nối:** dưới khoảng −10 dB không giải mã được (36.942 cũng dùng ngưỡng −10 dB).

**Kiểm chứng 2: hiệu chỉnh mô hình** (`analyze_run`). Chạy lại mô hình (tất định) cho đúng 9 run A/B/C ở mục 14.3,
cùng seed và quỹ đạo, với `lte_alpha = 0.401`, `lte_se_max = 3.514`. NS-3 không chạy lại.

| | A. chung tần số | B. tần số riêng | C. 1 UAV |
|---|---|---|---|
| Mô hình 36.942 (Mbps) | 76.3 | 103.9 | 43.4 |
| Mô hình hiệu chỉnh (Mbps) | 56.0 | 81.9 | 33.6 |
| NS-3 payload UDP (Mbps) | 57.0 | 80.8 | 33.7 |
| NS-3 / mô hình 36.942 | 0.750 | 0.778 | 0.777 |
| **NS-3 / mô hình hiệu chỉnh** | **1.019** | **0.988** | **1.004** |

Chỉ thay hai hằng số của đường cong *một liên kết*, mô hình dự đoán đúng throughput NS-3 của cả mạng nhiều UAV, có
nhiễu và handover, với sai số ±2%. Như vậy **giả thuyết (d) được xác nhận** và nó giải thích toàn bộ khoảng chênh.

**Kiểm chứng 3: SINR từng (khe, user)** (`ns3_sinr_per_slot`). Lấy SINR trung vị mỗi (khe, user) từ trace NS-3, so với
SINR mô hình tính (`Network.sinr`) cùng khe, cùng user.

| | A. chung tần số | B. tần số riêng | C. 1 UAV |
|---|---|---|---|
| Sai lệch trung vị (NS-3 − mô hình) | 0.07 dB | −0.02 dB | 0.22 dB |
| Sai lệch tuyệt đối trung bình | 0.34 dB | 0.33 dB | 0.42 dB |

Ngay cả khi có nhiễu đồng kênh (A), SINR mô hình khớp LTE PHY trong khoảng 0.5 dB, nên **giả thuyết (b) bị bác bỏ**.
Lưu ý: SINR trong trace là SINR đo trên tín hiệu tham chiếu. Ở trạng thái bão hòa, mọi eNB phát trên mọi RB, nên
SINR này đại diện được cho SINR của kênh dữ liệu.

**Giả thuyết (c):** lỗi khối < 0.1% ở mọi run (mục 14.3), và 0% ở mọi điểm của kiểm chứng 1, nên **bị bác bỏ**.

**Kết luận:**

| Giả thuyết | Kết quả | Bằng chứng |
|---|---|---|
| (a) Kênh cài khác nhau | Bác bỏ | SINR NS-3 = SNR mô hình (±0.1 dB) |
| (b) Mô hình nhiễu sai | Bác bỏ | Sai lệch SINR trung vị ≤ 0.22 dB, MAE ≤ 0.42 dB |
| (c) HARQ, lỗi truyền | Bác bỏ | Lỗi khối < 0.1% |
| (d) Ánh xạ SINR → throughput của LTE thấp hơn 36.942 | **Xác nhận** | α 0.40 / trần 3.51 so với 0.6 / 4.4; hiệu chỉnh xong thì NS-3/mô hình = 0.99–1.02 |
| Overhead header | Nhỏ | Goodput PHY cao hơn payload UDP khoảng 3% |

Muốn mô hình Python dự đoán sát NS-3 LTE 10 MHz SISO, dùng `--set lte_alpha=0.401 --set lte_se_max=3.514`. Giá trị
mặc định vẫn là 3GPP (0.6, 4.4), để so sánh được với paper. Bộ hằng số hiệu chỉnh chỉ đúng cho cấu hình này (10 MHz,
SISO, AMC mặc định của NS-3, kênh không fading). Đổi băng thông, antenna hay bật fading thì phải khớp lại.

### 14.5. Vì sao NS-3 khác lý thuyết của paper: giải thích theo từng cơ chế

**Nguyên tắc thiết lập.**
- Tầng lý thuyết giữ đúng cách paper làm: rate Shannon `B·log₂(1+SINR)` (`rate_model="shannon"`, mặc định), kênh
  Al-Hourani, năng lượng Zeng. Không hiệu chỉnh gì.
- Tầng NS-3 mô phỏng chi tiết LTE: PHY, AMC, MAC scheduler, RLC, EPC, UDP.
- Mục này giải thích, bằng số liệu và bằng mã nguồn NS-3, vì sao con số NS-3 thấp hơn lý thuyết.
- Hai hằng số hiệu chỉnh ở 14.4 chỉ là công cụ *kiểm chứng*; mô hình mặc định không dùng chúng.

**Phân rã.** `uavsim/validate.py` tính lại mô hình cho đúng các run NS-3 (cùng seed, quỹ đạo, liên kết), mỗi lần
thêm một cơ chế của LTE. Chênh lệch giữa hai bậc liền nhau là phần do cơ chế đó gây ra.

```bash
.venv/bin/python -m uavsim.validate --glob '*_load1_seed*' --runs \
    experiments/results/ns3-interference/A_3uav_chung_tan_so experiments/results/ns3-interference/B_3uav_tan_so_rieng \
    experiments/results/ns3-interference/C_1uav experiments/results/ns3-matrix
```

Kết quả: `experiments/results/validation/calibration.csv`, `decomposition.png`. Throughput tổng (Mbps), trung bình
qua seed, load 1.0 (bão hòa):

| Bậc | A. 3 UAV chung tần số | B. 3 UAV tần số riêng | C. 1 UAV | Ma trận: hover-equal | Ma trận: kmeans-equal | Ma trận: kmeans-maxmin |
|---|---|---|---|---|---|---|
| ① Shannon (lý thuyết paper) | 146.9 | 321.2 | 121.7 | 80.3 | 132.6 | 129.9 |
| ② 3GPP 36.942 (α 0.6, trần 4.4) | 76.3 | 103.9 | 43.4 | 45.3 | 74.3 | 73.0 |
| ③ + trần LTE 3.51 bit/s/Hz | 66.2 | 83.2 | 35.1 | 42.1 | 68.1 | 67.2 |
| ④ + độ dốc LTE α 0.40 | 56.0 | 81.9 | 33.6 | 31.5 | 52.1 | 51.1 |
| ⑤ NS-3 goodput PHY (đo) | 58.6 | 83.0 | 34.6 | — | — | — |
| ⑥ NS-3 payload UDP (đo) | 57.0 | 80.8 | 33.7 | 31.6 | 52.8 | 52.7 |
| **⑥ / ①** | **0.39** | **0.25** | **0.28** | **0.39** | **0.40** | **0.41** |
| ⑥ / ④ | 1.02 | 0.99 | 1.00 | 1.00 | 1.01 | 1.03 |

Ma trận chỉ có số đo UDP vì các run đó không bật trace. Hằng số ở bậc ③④ được khớp từ thí nghiệm một liên kết (14.4),
không khớp từ các run trong bảng; các run ma trận là kiểm chứng ngoài mẫu.

**Giải thích từng bậc:**

**① → ②: Shannon là giới hạn thông tin, không phải tốc độ của một hệ thống thật** (mất 44–68%).
- Shannon giả định mã dài vô hạn, tín hiệu Gauss, không giới hạn bậc điều chế, biết kênh hoàn hảo và không có overhead.
- Tốc độ theo Shannon tăng mãi theo SINR: 13 bit/s/Hz ở 40 dB. Hệ thống thật thì có trần.
- Công thức 3GPP TR 36.942 là cách chuẩn hóa để mô tả hệ thống thật: nhân 0.6 cho tổn hao triển khai, chặn ở
  4.4 bit/s/Hz.
- Bậc này mất nhiều nhất ở cấu hình **B, C** (không nhiễu, SINR trung vị ≈ 40 dB), đúng nơi Shannon tăng vượt xa mọi
  hệ thống thật.

**② → ③: trần thực của LTE 10 MHz SISO là 3.51 bit/s/Hz, không phải 4.4** (mất 7–20%).
- **MCS cao nhất** là MCS 28 (64QAM, chỉ số TBS 26). Theo bảng TBS 3GPP TS 36.213 (`lte-amc.cc: TransportBlockSizeTable`),
  khối truyền tối đa cho 50 RB là **36696 bit mỗi ms**, tức 3.67 bit/s/Hz trên 10 MHz. Con số này đã gồm các phần tài
  nguyên không mang dữ liệu: 50 RB × 180 kHz = 9 MHz (10% là băng bảo vệ), vùng điều khiển PDCCH, tín hiệu tham chiếu
  CRS, cyclic prefix.
- **Scheduler PF của NS-3 chỉ dùng 48/50 RB.** Với 50 RB, kích thước nhóm RB (RBG) là 3 (`PfType0AllocationRbg`:
  26 ≤ 50 < 63). Số nhóm là `50 / 3 = 16` theo phép chia nguyên (`pf-ff-mac-scheduler.cc`), tức 48 RB. Ở MCS 28, TBS
  cho 48 RB là **35160 bit/ms = 3.516 bit/s/Hz**, trùng với trần đo được 3.514. Đây là chi tiết hiện thực của NS-3
  (mất 4%), không phải giới hạn của chuẩn LTE.
- Không có MIMO (SISO). LTE thương mại 2×2 có thể gấp đôi.

**③ → ④: LTE không đạt đường cong liên tục mà đi theo bậc, và NS-3 làm tròn MCS xuống hai lần** (mất 1–25%).
- LTE chỉ có 29 MCS và 16 CQI, nên tốc độ tăng theo bậc thang thay vì liên tục.
- Mô hình AMC mặc định của NS-3 (`LteAmc::MiErrorModel`, `lte-amc.cc`) làm như sau:
  1. UE tìm MCS cao nhất có tỷ lệ lỗi khối ≤ 10% trên mỗi RBG.
  2. Đổi MCS đó sang CQI để báo về eNB, chọn CQI có hiệu suất phổ **nhỏ hơn hẳn** (`<`) hiệu suất của MCS.
  3. eNB đổi CQI ngược ra MCS (`GetMcsFromCqi`), chọn MCS có hiệu suất **≤** CQI.
- Hai lần làm tròn xuống làm mất 1–2 bậc MCS. Ví dụ: kênh chịu được MCS 16 (2.41 bit/s/Hz) → CQI 8 (1.91) → eNB dùng
  MCS 14 (1.91), mất 21%.
- Hệ quả đo được: tỷ lệ lỗi khối luôn ≈ 0% dù ngưỡng là 10%, và độ dốc hiệu dụng chỉ ≈ 0.40 so với 0.6 của 36.942.
- Bậc này mất nhiều ở **A và ma trận** (có nhiễu, nhiều user ở SINR 5–25 dB) và gần như không mất ở **B, C** (đa số
  user đã ở vùng trần MCS 28).

**④ → ⑤: phần còn lại ±4%.** Gồm scheduler PF (không chia đều băng như mô hình), mỗi lần đổi rate thì hàng đợi cần
thời gian lấp đầy, và vị trí UAV được nội suy bên trong khe.

**⑤ → ⑥: header giao thức** (mất 2.5–3%). Gói UDP payload 1200 byte được bọc thêm header IP/UDP 28 byte (2.3%), cộng
header PDCP/RLC/MAC.

**Yếu tố không gây chênh lệch:**
- **Kênh truyền:** SINR NS-3 = mô hình ±0.1 dB (14.4, kiểm chứng 1).
- **Cách mô hình tính nhiễu:** sai lệch SINR trung vị ≤ 0.22 dB (14.4, kiểm chứng 3). Nhiễu làm giảm tốc độ ở *cả hai
  bên*. Nhiễu chỉ gián tiếp làm khoảng chênh lớn hơn, vì nó đẩy user xuống vùng SINR trung bình, nơi bậc ③ → ④ gây mất
  nhiều nhất.
- **HARQ:** tỷ lệ lỗi khối < 0.1%.

**Những thứ lý thuyết không có, chỉ NS-3 cho thấy:**
- **Delay và mất gói khi tải vượt năng lực:** hàng đợi RLC tích tụ, delay cỡ giây (14.2).
- **Scheduler quyết định chia tài nguyên,** nên cấp phát ở tầng ứng dụng như maxmin mất tác dụng (14.2).
- **Sai lệch từng user:** ±5–8% trung vị, người kém nhất bị lý thuyết đánh giá cao 11–19% ngay cả sau hiệu chỉnh.

**Tóm lại cho báo cáo:**

> Throughput NS-3 LTE chỉ đạt khoảng 25–40% giá trị Shannon mà paper dùng. Khoảng chênh được giải thích hoàn toàn
> bởi ba cơ chế của hệ thống thật, theo thứ tự đóng góp:
> 1. Shannon không có trần, còn hệ thống thật thì có (công thức 3GPP 36.942);
> 2. trần thực của LTE 10 MHz SISO là 3.51 bit/s/Hz (bảng TBS ở MCS 28, scheduler NS-3 dùng 48/50 RB);
> 3. AMC rời rạc và làm tròn MCS xuống hai lần (độ dốc hiệu dụng 0.40).
>
> Kênh truyền và mô hình nhiễu được kiểm chứng là khớp (±0.3 dB). Khi đưa ba cơ chế này vào, mô hình dự đoán đúng
> NS-3 trong ±3% (trung bình mỗi cấu hình) và ±6% (từng run) trên 24 run, gồm 15 run ngoài mẫu.

### 14.6. Delay và mất gói: lý thuyết như paper so với NS-3

> Số lý thuyết trong mục này dùng delay FIFO chính xác và định nghĩa mất gói chung với NS-3 (mục 3.6). Thí nghiệm đã
> chạy lại vào `experiments/results/ns3-demand-lte` và `ns3-demand-wpf-lte`; số đo NS-3 LTE trùng từng chữ số với lần
> chạy trước trên cả 105 run, vì các thay đổi chỉ nằm ở phía lý thuyết.

**Mục đích:** chạy lý thuyết đúng như paper (Shannon, chia tĩnh, nhiễu tối đa, hàng đợi mục 3.6) để có throughput,
delay, mất gói; phát lại trong NS-3 với cùng lưu lượng; rồi giải thích khoảng chênh.

**Thiết kế:**
- 3 thuật toán × lưu lượng mỗi user {0.5, 1, 1.5, 2, 2.5, 3, 4} Mbps CBR × seed 0–2 × 60 khe = 63 run, scheduler PF;
- NS-3 gửi đúng `demand_mbps` cho mỗi UE theo liên kết của kế hoạch;
- bộ đệm 1 MiB ở cả hai bên.

```bash
.venv/bin/python -m uavsim.ns3 --algos hover-equal kmeans-equal kmeans-maxmin --set demand_mbps=1 \
    --load 0.5 1 1.5 2 2.5 3 4 --seeds 3 --set slots=60 --parallel 10 --out experiments/results/ns3-demand-lte
.venv/bin/python -m uavsim.validate --demand-run experiments/results/ns3-demand-lte --fit experiments/results/validation/fit.json
```

Kết quả: `experiments/results/ns3-demand-lte/` (`summary_ns3.csv`, `aggregate_ns3.csv`, `ns3_matrix.png`,
`theory_variants.csv`, `theory_vs_ns3.png`). Thời gian chạy khoảng 25 phút với 10 run song song.

**Bảng** (trung bình 3 seed). Cột "LTE" là lý thuyết dùng ánh xạ LTE (α 0.401, trần 3.514); cột "LTE+" là thêm cả chia
linh hoạt và nhiễu theo tải.

| Thuật toán | Mbps/user | Thr paper | Thr LTE | Thr LTE+ | **Thr NS-3** | Delay paper | Delay LTE | Delay LTE+ | **Delay NS-3** | Mất paper | Mất LTE | Mất LTE+ | **Mất NS-3** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hover-equal | 0.5 | 10.0 | 9.1 | 10.0 | **10.0** | 6 | 1996 | 20 | **10** | 0.0 | 9.3 | 0.0 | **0.0** |
| | 1 | 18.9 | 14.8 | 18.2 | **18.5** | 1202 | 4574 | 1700 | **1267** | 5.5 | 25.9 | 8.8 | **7.4** |
| | 2 | 32.4 | 21.2 | 23.7 | **22.6** | 2094 | 5403 | 4688 | **4663** | 19.1 | 47.1 | 40.7 | **43.4** |
| | 4 | 47.5 | 28.1 | 29.0 | **27.8** | 2634 | 5601 | 5458 | **5491** | 40.6 | 64.9 | 63.8 | **65.2** |
| kmeans-equal | 0.5 | 10.0 | 10.0 | 10.0 | **10.0** | 2 | 69 | 20 | **7** | 0.0 | 0.0 | 0.0 | **0.0** |
| | 1 | 20.0 | 19.6 | 20.0 | **19.6** | 17 | 614 | 131 | **152** | 0.0 | 2.0 | 0.0 | **2.2** |
| | 2 | 39.5 | 34.3 | 36.0 | **33.9** | 279 | 1782 | 1288 | **1397** | 1.3 | 14.2 | 10.0 | **15.2** |
| | 4 | 71.6 | 49.9 | 51.0 | **49.9** | 749 | 2477 | 2339 | **2173** | 10.5 | 37.6 | 36.2 | **37.6** |
| kmeans-maxmin | 1 | 20.0 | 19.7 | 20.0 | **19.6** | 7 | 520 | 131 | **152** | 0.0 | 1.7 | 0.0 | **2.2** |
| | 4 | 72.3 | 49.4 | 51.0 | **49.9** | 754 | 2664 | 2339 | **2173** | 9.6 | 38.3 | 36.2 | **37.6** |

Throughput tính bằng Mbps, delay bằng ms, mất gói bằng %. Đủ 7 mức lưu lượng có trong `theory_variants.csv`.

**Sai số trên toàn bộ 63 run:**

| Biến thể lý thuyết | Sai số throughput | Sai số mất gói | Delay: trung vị lệch |
|---|---|---|---|
| Paper (Shannon, tĩnh, nhiễu tối đa) | 27.3% | 15.1 điểm % | ×3.7 |
| + ánh xạ LTE | 3.5% | 2.7 điểm % | ×1.21 |
| + ánh xạ LTE + chia linh hoạt | 4.9% | 3.6 điểm % | ×1.23 |
| + ánh xạ LTE + nhiễu theo tải | 4.4% | 3.2 điểm % | ×1.16 |
| + cả ba | 5.9% | 4.2 điểm % | ×1.26 |

**Nhận xét:**

1. **Lý thuyết paper quá lạc quan về QoS.** Ở mọi mức lưu lượng, nó dự đoán nghẽn muộn hơn, delay thấp hơn 3–9 lần
   và mất gói thấp hơn nhiều (kmeans 4 Mbps/user: 10.5% so với 37.6%). Xếp hạng thì đúng: kmeans tốt hơn hover ở mọi
   mức, cả trong lý thuyết lẫn NS-3.
2. **Ánh xạ SINR → rate của LTE** (đã kiểm chứng ở 14.4) giải thích phần lớn chênh lệch. Thay đúng hai hằng số
   α và trần là sai số throughput giảm từ 27% xuống 3.5%, mất gói từ 15 xuống 2.7 điểm phần trăm, delay từ ×3.7 xuống
   ×1.2. Ở tải cao (≥ 2 Mbps/user), mất gói của biến thể này lệch NS-3 trung bình 0.2 điểm %, delay lệch trung vị ×1.13.
3. **Nhiễu theo tải giải thích các trường hợp tải nhẹ.** Hover ở 0.5 Mbps/user: lý thuyết LTE với nhiễu tối đa dự đoán
   delay 2 s và mất 9.3%, vì user ở rìa có SINR thấp, không đủ năng lực trên phần băng cố định. Tính nhiễu theo tải
   thì còn 8 ms, 0% (bảng chỉ ghi biến thể "cả ba", 20 ms), khớp NS-3 (10 ms, 0%). Cơ chế: eNB LTE chỉ phát trên RB
   được cấp, nên khi tải nhẹ nhiễu thực rất thấp. Phép so SINR ở 14.4 đo khi bão hòa, nơi mọi RB đều bận, nên không
   thấy được điều này.
4. **Chia linh hoạt giải thích tải trung bình và hành vi của maxmin.** kmeans ở 1 Mbps/user: chia linh hoạt đưa delay
   từ 614 xuống 263 ms, thêm nhiễu theo tải thì 131 ms (NS-3 152 ms). Với chia linh hoạt, kmeans-maxmin và
   kmeans-equal cho kết quả trùng nhau, giống NS-3, nơi số đo của hai thuật toán giống hệt nhau vì chúng chỉ khác
   cách chia băng mà NS-3 giao cho scheduler PF. Lý thuyết paper với chia tĩnh thì cho rằng maxmin giảm delay từ 17
   xuống 7 ms; mục 14.9 cho thấy điều đó đúng ở mức gói tin, nên khác biệt trên LTE là do scheduler PF.
5. **Bật thêm cơ chế không làm sai số tổng nhỏ đi:** ở tải cao, chia linh hoạt và nhiễu theo tải làm lý thuyết lạc
   quan thêm 1–2 Mbps. Giá trị của chúng nằm ở chỗ giải thích đúng vùng tải nhẹ và trung bình, nơi lý thuyết chỉ hiệu
   chỉnh LTE vẫn sai cả bậc độ lớn về delay.

**Phần chưa giải thích:**
- **Tải cao:** trước khi dùng chung định nghĩa mất gói, NS-3 mất gói nhiều hơn mọi biến thể 3–8 điểm %; phần lớn
  khoảng chênh đó chỉ do cách đếm (NS-3 tính gói còn trong hàng đợi lúc kết thúc là mất). Còn lại: delay của biến thể
  ánh xạ LTE cao hơn NS-3 khoảng 13% (trung vị), từng run lệch từ −11% đến +50%. Ứng viên: header PDCP/RLC/MAC chiếm
  một phần năng lực; gói mất khi handover; scheduler PF không phải max-min thuần. Chưa kiểm chứng.
- **Delay nền khi tải rất nhẹ:** NS-3 6–14 ms, lý thuyết chỉ có thời gian truyền gói 1.5–9 ms. Phần chênh là độ trễ xử
  lý LTE (TTI 1 ms, chu kỳ lập lịch, RLC/PDCP) và đường lõi 1 ms trong kịch bản, mà lý thuyết không mô hình.

**Biểu đồ ba tầng:** `experiments/results/three_tier_pf.png` (bảng sai số từng tầng: `three_tier_pf.csv`).

### 14.7. Áp cấp phát băng thông ở tầng MAC: scheduler Weighted PF

**Vấn đề (14.2 và 14.6):** khi b_k chỉ áp ở tầng ứng dụng, scheduler PF của LTE tự chia lại resource block, nên maxmin và
equal cho số đo NS-3 giống hệt nhau.

**Giải pháp:** scheduler mới `WpfFfMacScheduler` (`ns3/scratch/uav_lte/wpf-ff-mac-scheduler.{h,cc}`).
- Đây là bản sao scheduler PF của NS-3 3.47, chỉ sửa một dòng: chỉ số chọn UE cho mỗi nhóm RB là
  `w_k · tốc độ tức thời / tốc độ trung bình`, với **w_k = b_k** của thuật toán (Weighted Proportional Fair). Về lâu
  dài, phần tài nguyên của UE tỷ lệ với w_k. HARQ, CQI và uplink giữ nguyên như PF.
- Kịch bản đặt trọng số cho RNTI hiện tại của mỗi UE trên eNB đang phục vụ nó, hai lần mỗi khe (RNTI đổi sau handover).
- Bật bằng `--scheduler wpf`.

**Kiểm chứng scheduler** (test `test_wpf_scheduler_shares_resources_by_weight`):
- trọng số bằng nhau thì số đo **trùng từng byte** với PF gốc;
- 2 UE cùng vị trí, trọng số 0.8 / 0.2, bão hòa: throughput 27.3 / 6.9 Mbps, tỷ lệ **3.93** (mong đợi 4), tổng bằng PF.

**Thí nghiệm:**

```bash
.venv/bin/python -m uavsim.ns3 --algos hover-maxmin kmeans-maxmin --scheduler wpf --link lte --set demand_mbps=1 \
    --load 0.5 1 1.5 2 2.5 3 4 --seeds 3 --set slots=60 --parallel 10 --out experiments/results/ns3-demand-wpf-lte
```

So với `*-equal` trong `experiments/results/ns3-demand-lte` (scheduler PF, trùng với `wpf` vì trọng số bằng nhau trong
mỗi cell), cùng seed và cùng lưu lượng. 42 run, khoảng 20 phút. Min throughput là trung bình theo khe của throughput
nhỏ nhất trong khe, giống các thí nghiệm khác.

| | Mbps/user | Min thr equal → maxmin (lý thuyết dự đoán) | Thr tổng | Mất gói | Delay |
|---|---|---|---|---|---|
| hover | 1 | 0.57 → **0.67**: +18%, 3/3 seed (+18%) | 18.5 → 19.0 | 7.4% → 5.1% | 1267 → 883 ms |
| hover | 2 | 0.30 → **0.35**: +16%, 3/3 (+18%) | 22.6 → 22.4 | 43.4% → 43.9% | 4663 → 5142 ms |
| hover | 4 | 0.26 → **0.30**: +16%, 3/3 (+18%) | 27.8 → 26.5 | 65.2% → 66.9% | 5491 → 5851 ms |
| kmeans | 1 | 0.84 → 0.85: +1%, 3/3 (+2%) | 19.6 → 19.6 | 2.2% → 2.0% | 152 → 156 ms |
| kmeans | 2 | 0.72 → **0.79**: +10%, 3/3 (+3%) | 33.9 → 34.0 | 15.2% → 15.0% | 1397 → 1524 ms |
| kmeans | 4 | 0.67 → **0.74**: +11%, 3/3 (+11%) | 49.9 → 49.7 | 37.6% → 37.9% | 2173 → 2354 ms |

**Kết luận:**
1. **Cấp phát băng thông không vô dụng: nó cần được áp ở đúng tầng.** Áp ở tầng MAC thì maxmin nâng user kém nhất ở
   cả 18 cặp (thuật toán, lưu lượng, seed): +16–18% với hover, đúng như lý thuyết dự đoán (+18%). Áp ở tầng ứng dụng
   thì hoàn toàn không có tác dụng.
2. **Hiệu quả phụ thuộc mức chênh lệch kênh giữa các user.** Với hover, user trong một cell có SINR rất khác nhau, nên
   maxmin có tác dụng ngay từ tải nhẹ. Với kmeans, UAV đã ở giữa cụm, SINR các user gần nhau hơn, nên maxmin chỉ tạo
   khác biệt khi mạng đã nghẽn (+10–11% từ 2 Mbps/user). Lý thuyết cũng dự đoán xu hướng này.
3. **Đánh đổi ở tải cao mạnh hơn lý thuyết nói.** Lý thuyết cho rằng tổng throughput còn tăng nhẹ (+2%), nhưng NS-3
   giảm tới 5% và delay tăng, vì tài nguyên dồn cho user có hiệu suất phổ thấp. Ở tải vừa (1 Mbps/user) maxmin với
   hover tốt hơn mọi mặt: min +18%, mất gói 7.4% → 5.1%, delay giảm 30%.
4. **Hướng của lý thuyết đúng, con số tuyệt đối vẫn lạc quan** như các mục trước.

### 14.8. Mô hình và NS-3: kết luận nào đứng vững

| Kết luận từ mô hình (14.1) | Kết quả NS-3 (14.2) |
|---|---|
| Di chuyển UAV về tâm cụm cải thiện mạnh rate và công bằng | **Đúng.** Min throughput khoảng 2.2×, Jain khoảng 1.5× (5/5 seed) |
| Nhiễu đồng kênh có thể làm giảm lợi ích khi thêm UAV | **Phù hợp.** 1/5 seed hover có tổng throughput cao hơn kmeans |
| Giá trị rate tuyệt đối | **Lạc quan.** LTE chỉ đạt 75–78% công thức 36.942. Đã kiểm chứng (14.4): nguyên nhân là ánh xạ SINR → throughput của LTE (α 0.40, trần 3.51 so với 0.6, 4.4). Hiệu chỉnh hai hằng số này thì mô hình khớp NS-3 ±2% |
| maxmin tăng min rate, đổi lại giảm nhẹ sum rate | **Phụ thuộc tầng áp dụng.** Chỉ áp ở tầng ứng dụng: gần như không còn đúng (min +6% ở tải thấp nhưng delay ×2.3; ở tải cao trùng equal). Áp ở tầng MAC bằng `wpf` (14.7): **đúng**, min +15–21% (3/3 seed) (min tính trên throughput trung bình của từng user; nếu tính theo khe như báo cáo thì +16–18%) khớp dự đoán +18%; ở tải cao tổng giảm tới 5%, nhiều hơn lý thuyết nói |
| (mô hình không có) delay, mất gói | NS-3 cho thấy cần hệ số an toàn khoảng 0.5–0.6 để delay giữ ở mức chục ms |
| Delay, mất gói theo hàng đợi Lyapunov (14.6, lý thuyết paper) | **Quá lạc quan:** delay thấp hơn 3–8 lần, mất gói thấp hơn nhiều; xếp hạng kmeans > hover vẫn đúng. Thêm ánh xạ LTE thì sai số mất gói còn khoảng 4 điểm %, delay ×1.3 |
| (đề xuất) chia băng theo SE LTE có nhiễu + tinh chỉnh vị trí (14.10) | **Đứng vững:** min throughput ×1.92–2.03 ở tải ≥ 2 Mbps/user (3/3 seed), throughput tổng giữ trong ±4% |
| maxmin giảm delay so với equal (lý thuyết paper, chia tĩnh) | Với PF: **không đứng vững** (số đo giống hệt). Với `wpf`: delay giảm 30% ở 1 Mbps/user (hover), nhưng tăng ở tải cao |

Tóm lại: mô hình giải tích đủ tốt để **xếp hạng** các chiến lược di chuyển, nhưng không đủ để dự đoán **giá trị
tuyệt đối**, **delay**, hay hiệu quả của **cấp phát không gắn với scheduler MAC**. Ba cơ chế của LTE giải thích phần
lớn khoảng chênh: ánh xạ SINR → rate (luôn quan trọng), nhiễu theo tải (tải nhẹ), scheduler chia linh hoạt (tải trung
bình, thuật toán chia băng). Mục 14.9 xác nhận rằng bản thân mô hình hàng đợi không góp phần vào khoảng chênh.

### 14.9. Ba tầng: lý thuyết khớp NS-3 liên kết lý tưởng

**Thí nghiệm:** đúng cấu hình của 14.6 và 14.7 (3 UAV, 20 user, 60 khe, 3 seed, lưu lượng 0.5–4 Mbps/user, bộ đệm
1 MiB), chạy với `--link ideal`. 63 + 42 run, mỗi run khoảng 14 s.

```bash
.venv/bin/python -m uavsim.ns3 --link ideal --algos hover-equal kmeans-equal kmeans-maxmin --seeds 3 --set slots=60 \
    --set demand_mbps=1 --load 0.5 1 1.5 2 2.5 3 4 --parallel 10 --out experiments/results/ns3-demand-ideal
.venv/bin/python -m uavsim.ns3 --link ideal --algos hover-maxmin kmeans-maxmin --scheduler wpf --seeds 3 --set slots=60 \
    --set demand_mbps=1 --load 0.5 1 1.5 2 2.5 3 4 --parallel 10 --out experiments/results/ns3-demand-wpf-ideal
```

**Sai số lớn nhất trên từng run** (105 run):

| Chỉ số | Sai số lớn nhất, lý thuyết so với NS-3 lý tưởng |
|---|---|
| Throughput tổng | 0.02% |
| Min throughput | 2.1% (tải 0.5 Mbps/user: lệch pha gói đầu khe; từ 1 Mbps/user trở lên < 0.8%) |
| Delay | 1.0% |
| Mất gói | 0.014 điểm % |

**Trung bình 3 seed** (thr Mbps, delay ms, mất gói %; lý thuyết / NS-3 lý tưởng):

| Thuật toán | Mbps/user | Throughput | Delay | Mất gói |
|---|---|---|---|---|
| hover-equal | 0.5 | 10.00 / 10.00 | 5.6 / 5.6 | 0.00 / 0.01 |
| | 1 | 18.90 / 18.90 | 1202.5 / 1201.6 | 5.49 / 5.50 |
| | 2 | 32.35 / 32.35 | 2094.4 / 2092.5 | 19.12 / 19.12 |
| | 4 | 47.54 / 47.54 | 2634.0 / 2631.1 | 40.58 / 40.58 |
| kmeans-equal | 0.5 | 10.00 / 10.00 | 2.3 / 2.3 | 0.00 / 0.00 |
| | 1 | 20.00 / 20.00 | 17.3 / 17.5 | 0.00 / 0.00 |
| | 2 | 39.49 / 39.49 | 278.6 / 278.5 | 1.27 / 1.27 |
| | 4 | 71.63 / 71.63 | 749.2 / 748.4 | 10.46 / 10.47 |
| kmeans-maxmin | 1 | 20.00 / 20.00 | 7.2 / 7.2 | 0.00 / 0.00 |
| | 4 | 72.29 / 72.29 | 754.0 / 753.1 | 9.64 / 9.64 |
| hover-maxmin | 1 | 19.34 / 19.34 | 773.5 / 773.9 | 3.30 / 3.31 |
| | 4 | 48.26 / 48.26 | 2668.7 / 2665.7 | 39.67 / 39.68 |

Đủ 7 mức lưu lượng trong `aggregate_ns3.csv` của hai thư mục.

**Ba lần sửa để đạt mức khớp này:**
1. **Định nghĩa mất gói:** NS-3 tính cả gói còn trong hàng đợi lúc kết thúc là mất; lý thuyết trước đó thì không.
   Chênh tới 6 điểm %. Sửa: dùng cùng định nghĩa (mục 3.6).
2. **Delay:** công thức Little với Q̄ = (Q đầu + Q cuối)/2 lệch NS-3 1–25%, lớn nhất ở tải cao. Sửa: delay FIFO chính
   xác (`fifo_delay`).
3. **Bộ đệm:** thiết bị NS-3 đếm cả header 30 byte mỗi gói, mô hình chỉ đếm payload. Sửa: nâng kích thước hàng đợi
   DropTail theo tỷ lệ header.

**Ý nghĩa:**
- Mô hình hàng đợi, pipeline xuất kế hoạch và cách đo của NS-3 đúng ở mức gói tin. Mọi khoảng chênh giữa lý thuyết
  và NS-3 LTE (14.4–14.7) là do giao thức LTE, không do mô hình hàng đợi hay pipeline.
- Ở tầng lý tưởng, maxmin khác equal rõ rệt (kmeans 1 Mbps/user: delay 17.3 → 7.2 ms; hover: min 0.71 → 0.84 Mbps),
  đúng như lý thuyết. Trong NS-3 LTE với PF hai thuật toán cho số đo giống hệt (14.6), nên việc kết luận này không
  đứng vững trên LTE là do scheduler PF chia lại tài nguyên, không phải do lý thuyết tính sai.
- Chế độ lý tưởng không phụ thuộc scheduler: `kmeans-maxmin` cho số giống hệt nhau trong `ns3-demand-ideal` và
  `ns3-demand-wpf-ideal`.

**Biểu đồ ba tầng:** `experiments/plot_three_tier.py` vẽ lý thuyết, NS-3 lý tưởng và NS-3 LTE trên cùng hình (mục 11.5):
`experiments/results/three_tier_pf.png` (scheduler PF) và `three_tier_wpf.png` (scheduler WPF), kèm bảng sai số từng
tầng `three_tier_*.csv`. Mỗi hình là lưới 4 hàng (throughput, min throughput, delay thang log, mất gói) × một cột cho mỗi thuật toán, trục ngang là
lưu lượng mỗi user. Màu theo tầng: đường xanh dương = lý thuyết, vòng cam = NS-3 liên kết lý tưởng (đè lên đường lý
thuyết), đường xanh lá có dải mờ = NS-3 LTE ± độ lệch chuẩn. Ở mọi ô, vòng cam nằm đúng trên đường xanh dương, còn
đường xanh lá tách ra.

---

### 14.10. Thuật toán đề xuất `calib-ifair` đo bằng NS-3 LTE

Thí nghiệm dùng đúng cấu hình của 14.6–14.7 (3 UAV, 20 user, 60 khe, lưu lượng 0.5–4 Mbps/user, seed 0–2). Thuật toán
mới và hai bản tách thành phần chạy với scheduler WPF; kmeans-equal (PF) và kmeans-maxmin (WPF) lấy từ các lần đo đã
có, cùng seed và cùng lưu lượng nên ghép cặp được. 63 run NS-3 LTE và 63 run liên kết lý tưởng.

```bash
.venv/bin/python -m uavsim.ns3 --link lte --algos calib-ifair kmeans-ifair calib-equal --scheduler wpf --seeds 3 \
    --set slots=60 --set demand_mbps=1 --load 0.5 1 1.5 2 2.5 3 4 --parallel 10 --out experiments/results/ns3-proposed-lte
.venv/bin/python experiments/compare_proposed.py experiments/results/proposed
```

Ở tầng liên kết lý tưởng, mô hình vẫn khớp NS-3 như các thuật toán cũ (sai số throughput lớn nhất 0.016%, độ trễ
1.2%, mất gói 0.014 điểm %), nên khác biệt đo trên LTE là do thuật toán và giao thức.

Kết quả đo bằng NS-3 LTE (trung bình 3 seed; "×" là tỷ lệ min throughput so với kmeans-equal trên cùng seed, trong ngoặc
là số seed thắng):

| Mbps/user | kmeans-equal | kmeans-maxmin | kmeans-ifair | calib-equal | **calib-ifair** |
|---|---|---|---|---|---|
| Min throughput (Mbps), 1 | 0.84 | 0.85 (×1.01) | 0.92 (×1.11) | 0.90 (×1.09) | **0.95 (×1.16, 3/3)** |
| 2 | 0.72 | 0.79 (×1.10) | 1.29 (×1.77) | 0.80 (×1.10) | **1.37 (×1.92, 3/3)** |
| 4 | 0.67 | 0.74 (×1.11) | 1.27 (×1.87) | 0.75 (×1.09) | **1.37 (×2.03, 3/3)** |
| Throughput tổng (Mbps), 1 | 19.6 | 19.6 | 19.8 | 19.8 | 19.9 |
| 2 | 33.9 | 34.0 | 33.4 | 35.3 | 34.8 |
| 4 | 49.9 | 49.7 | 46.1 | 52.2 | 48.2 |
| Độ trễ (ms), 1 | 152 | 156 | 165 | 57 | 72 |
| 2 | 1397 | 1524 | 2174 | 1152 | 1837 |
| Mất gói (%), 1 | 2.2 | 2.0 | 1.3 | 1.2 | 0.5 |
| 2 | 15.2 | 15.0 | 16.6 | 11.8 | 13.1 |
| 4 | 37.6 | 37.9 | 42.3 | 34.8 | 39.7 |

Đầy đủ 7 mức lưu lượng: `experiments/results/proposed.csv`, hình `proposed.png`.

**Nhận xét:**
1. calib-ifair nâng min throughput gần gấp đôi so với kmeans-equal khi tải từ 2 Mbps/user trở lên (×1.92–2.03, cả
   3/3 seed), trong khi maxmin của baseline (dùng SNR không nhiễu và Shannon không trần) chỉ được ×1.10. Throughput
   tổng gần như giữ nguyên (+2.5% ở 2 Mbps, −3.5% ở 4 Mbps).
2. Ở tải vừa (1 Mbps/user), calib-ifair tốt hơn baseline ở mọi chỉ số: min ×1.16, độ trễ 152 → 72 ms, mất gói
   2.2% → 0.5%.
3. Tách thành phần: phần lớn lợi ích về công bằng đến từ cách chia băng `ifair` (kmeans-ifair đã được ×1.77–1.87);
   phần di chuyển `calib` thêm khoảng 0.08–0.1 Mbps vào min throughput, đồng thời bù lại phần throughput tổng và mất
   gói mà `ifair` làm giảm (kmeans-ifair ở 4 Mbps: 46.1 Mbps, mất 42.3%; calib-ifair: 48.2 Mbps, 39.7%). calib-equal
   cho throughput tổng cao nhất và mất gói thấp nhất ở tải cao, tức phần di chuyển tự nó có ích cho hiệu quả tổng.
4. Đánh đổi: ở tải cao, độ trễ trung bình của các biến thể `ifair` cao hơn baseline vì băng thông dồn cho user kênh
   yếu, hàng đợi của user kênh tốt dài hơn. Đây là đánh đổi công bằng và hiệu quả quen thuộc, nay được đo ở mức gói tin.
5. Khác với maxmin ở 14.6–14.7, cải thiện ở đây đứng vững trên NS-3 vì hai lý do đã rút ra từ các mục trước: quyết định
   dựa trên ánh xạ SINR → tốc độ đo được của LTE (có nhiễu, có trần), và được áp ở tầng MAC qua WPF.

---

### 14.11. Ba nhóm user đo bằng NS-3 LTE

Lệnh (42 run mới; baseline và calib-ifair-noclass dùng lại run của mục 14.10 và E5/E6 vì nhóm không làm đổi vị trí user):

```bash
.venv/bin/python -m uavsim.ns3 --algos calib-ifair calib-ifair-shannon --seeds 3 --scheduler wpf \
    --set slots=60 --set demand_mbps=1 --set important_frac=0.25 --set critical_frac=0.15 \
    --load 0.5 1 1.5 2 2.5 3 4 --parallel 10 --out experiments/results/ns3-classes-lte
.venv/bin/python experiments/compare_classes.py experiments/results/classes
```

`compare_classes.py` tính chỉ số từng nhóm từ `ns3_slots.csv` (byte, gói, độ trễ của từng user từng khe), với nhóm lấy
từ `user_classes(cfg)` cùng seed. Số chính (trung bình 3 seed):

| Mbps/user | Chỉ số | kmeans-equal | kmeans-maxmin | noclass | kmeans-wmaxmin | shannon | calib-ifair |
|---|---|---|---|---|---|---|---|
| 2 | Critical đạt QoS | 69% | 69% | 65% | 87% | 98% | 97% |
| 2 | Min throughput critical (Mbps) | 1.27 | 1.30 | 1.52 | 1.80 | 1.96 | 1.97 |
| 2 | Throughput tổng (Mbps) | 33.9 | 34.0 | 34.8 | 31.8 | 32.5 | 32.4 |
| 4 | Critical đạt QoS | 69% | 66% | 59% | 86% | 96% | 96% |
| 4 | Min throughput critical (Mbps) | 1.64 | 1.67 | 1.63 | 2.79 | 3.24 | 3.25 |
| 4 | Min throughput normal (Mbps) | 0.68 | 0.76 | 1.40 | 0.49 | 0.94 | 0.95 |
| 4 | Throughput tổng (Mbps) | 49.9 | 49.7 | 48.2 | 44.3 | 44.2 | 44.1 |

`kmeans-wmaxmin` (`Heuristic("kmeans", "wmaxmin")`): như kmeans-maxmin nhưng b_k ∝ w_k / log2(1+SNR_k), baseline biết
nhóm; 21 run ở `experiments/results/ns3-wmaxmin-lte` (lệnh như trên với `--algos kmeans-wmaxmin`).

Nhận xét: trọng số nhóm nâng tỷ lệ critical đạt QoS lên 96–97% và giảm độ trễ nhóm critical (2 Mbps/user: 1084 → 41
ms), đổi lại throughput tổng giảm 4.4% (2 Mbps) đến 11.6% (4 Mbps). Bản Shannon trùng bản LTE trong 1–2% trên mọi seed,
tức hằng số LTE hiệu chỉnh không phải nguồn gốc của cải thiện. Cùng biết nhóm, calib-ifair vẫn hơn max-min có
trọng số: critical đạt QoS 96–97% so với 86–87%, min throughput normal gần gấp đôi, throughput tổng như nhau. Đầy đủ: `experiments/results/classes.csv`, hình
`classes.png`.

## 15. Giới hạn và hướng mở rộng

### 15.1. Giới hạn hiện tại

| Giới hạn | Ảnh hưởng |
|---|---|
| Độ cao cố định | Chưa tối ưu 3D; độ cao là đánh đổi quan trọng trong mô hình Al-Hourani |
| Al-Hourani dùng suy hao **trung bình** | Không lấy mẫu LoS/NLoS ngẫu nhiên từng khe, nên kênh "mượt" hơn thực tế |
| Nhiễu xấp xỉ PSD | Không mô hình gán subcarrier cụ thể; có xu hướng *ước lượng trung bình* nhiễu |
| Liên kết luôn max-gain ở baseline | Không cân bằng tải |
| Không backhaul, pin, tránh va chạm | UAV có thể bay sát nhau; không có giới hạn năng lượng episode |
| Chỉ downlink, chỉ OFDMA | Chưa có uplink, NOMA, RSMA |
| Chưa có UAV cánh cố định | Mô hình Zeng–Zhang 2017 (P = c₁V³ + c₂/V) chưa cài |
| Chưa có baseline tối ưu lồi | Chưa có BCD/SCA để làm mốc "gần tối ưu" |
| Chưa huấn luyện DRL | Môi trường có sẵn nhưng chưa có agent |
| NS-3 phát lại offline; b_k áp qua trọng số PF, p_k chưa áp | Xem mục 12.6 và 14.7 |
| Điều khiển thời gian thực chỉ dùng mô hình | Số trên dashboard là số tính; Gazebo không có PX4 hay động lực học bay (mục 11.4) |
| Liên kết lý tưởng chỉ kiểm chứng phần hàng đợi | Tốc độ liên kết lấy từ mô hình, nên tầng này không kiểm chứng công thức kênh hay SINR; phần đó do NS-3 LTE và mục 14.4 đảm nhận |
| Ma trận NS-3 chỉ có một cấu hình | Mới chạy scheduler PF, 60 khe, 5 seed, 3 UAV / 20 user / urban; chưa có RR, chưa thay đổi topology |

### 15.2. Hướng mở rộng, theo thứ tự đề xuất

1. **Mở rộng ma trận NS-3:** scheduler RR, số UAV (2, 3, 5), môi trường, số user; thêm seed.
2. **Huấn luyện agent DRL** trên `UavBsEnv` (PPO/TD3 qua stable-baselines3), so với `kmeans-equal`.
3. **Liên kết cân bằng tải** (ví dụ matching, hoặc max-gain có giới hạn số user mỗi UAV).
4. **Quản lý nhiễu:** chia băng giữa các UAV (reuse > 1), hoặc điều khiển công suất.
5. **Baseline BCD + SCA** (cần cài `cvxpy`) với `channel=los`, đúng như Wu–Zeng–Zhang 2018.
6. **Ràng buộc năng lượng hay pin** và chỉ số thời gian sống của mạng.
7. **Tối ưu độ cao** (thêm thành phần z vào vận tốc).
8. **Áp cả công suất p_k** ở tầng MAC/PHY (đã áp b_k bằng scheduler `wpf`, mục 14.7); thử scheduler cấp RB đúng tỷ lệ từng TTI thay vì trọng số PF.
9. Nối lại dashboard web cũ (đang ở Trash) với `uavsim` làm backend.

---

## 16. Tài liệu tham khảo

1. A. Al-Hourani, S. Kandeepan, S. Lardner, "Optimal LAP Altitude for Maximum Coverage," *IEEE Wireless
   Communications Letters*, vol. 3, no. 6, 2014.
2. Q. Wu, Y. Zeng, R. Zhang, "Joint Trajectory and Communication Design for Multi-UAV Enabled Wireless Networks,"
   *IEEE Transactions on Wireless Communications*, vol. 17, no. 3, 2018.
3. Y. Zeng, J. Xu, R. Zhang, "Energy Minimization for Wireless Communication With Rotary-Wing UAV," *IEEE
   Transactions on Wireless Communications*, vol. 18, no. 4, 2019.
4. Y. Zeng, R. Zhang, "Energy-Efficient UAV Communication With Trajectory Optimization," *IEEE Transactions on
   Wireless Communications*, vol. 16, no. 6, 2017 (mô hình cánh cố định, chưa cài).
5. R. Jain, D. Chiu, W. Hawe, "A Quantitative Measure of Fairness and Discrimination for Resource Allocation in
   Shared Computer Systems," DEC Research Report TR-301, 1984.
6. Gymnasium documentation, Farama Foundation, phiên bản 1.0.
7. 3GPP TR 36.942, "E-UTRA Radio Frequency (RF) system scenarios", Phụ lục A.1 (Shannon cắt ngọn).
8. ns-3 Model Library, LTE Module (LENA), phiên bản 3.47.

> Thông tin xuất bản (tập, số, năm) ghi theo trí nhớ, chưa đối chiếu lại với bản gốc. Hãy kiểm tra trước khi
> trích dẫn trong báo cáo.
