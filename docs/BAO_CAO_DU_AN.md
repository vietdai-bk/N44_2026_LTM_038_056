# Cấp phát tài nguyên cho mạng nhiều UAV làm trạm gốc trên không: mô hình giải tích, kiểm chứng ba tầng bằng NS-3 và điều khiển thời gian thực

Báo cáo tóm tắt dự án cuối kỳ môn Lập trình mạng. Bố cục theo tám mục của tiêu chí đánh giá. Số liệu lấy từ các lần
chạy lưu trong `experiments/results/`; chi tiết kỹ thuật đầy đủ hơn nằm trong `docs/THIET_KE_MO_PHONG.md`. Phần gợi
ý cho việc viết báo cáo dài và làm slide được để riêng ở Phụ lục D.

## Mục lục

1. [Đóng góp của các thành viên](#1-đóng-góp-của-các-thành-viên)
2. [Tính cấp thiết và ý nghĩa](#2-tính-cấp-thiết-và-ý-nghĩa)
3. [Kiến trúc và thiết kế hệ thống](#3-kiến-trúc-và-thiết-kế-hệ-thống)
4. [Mô hình toán học và phát biểu bài toán](#4-mô-hình-toán-học-và-phát-biểu-bài-toán)
5. [Triển khai hệ thống và giải thuật](#5-triển-khai-hệ-thống-và-giải-thuật)
6. [Phân tích và đánh giá hiệu năng](#6-phân-tích-và-đánh-giá-hiệu-năng)
7. [Kết luận và hướng phát triển](#7-kết-luận-và-hướng-phát-triển)
8. [Tài liệu tham khảo](#8-tài-liệu-tham-khảo)
- [Phụ lục A. Bảng ký hiệu](#phụ-lục-a-bảng-ký-hiệu)
- [Phụ lục B. Danh mục hình](#phụ-lục-b-danh-mục-hình)
- [Phụ lục C. Tái lập kết quả](#phụ-lục-c-tái-lập-kết-quả)
- [Phụ lục D. Ghi chú cho người viết báo cáo và làm slide](#phụ-lục-d-ghi-chú-cho-người-viết-báo-cáo-và-làm-slide)

---

## 1. Đóng góp của các thành viên

Nhóm gồm hai thành viên, cùng tham gia mọi hạng mục và thống nhất chia đều đóng góp: mỗi người 50%.

| Hạng mục | Sản phẩm | Thành viên | Tỷ lệ |
|---|---|---|---|
| Khảo sát tài liệu, chọn mô hình | Chương 2, danh mục tài liệu tham khảo | Thái Viết Đại, Nguyễn Quang Phúc | 50% / 50% |
| Mô hình Python `uavsim` | Kênh, rate, năng lượng, hàng đợi, 6 thuật toán baseline, môi trường DRL | Thái Viết Đại, Nguyễn Quang Phúc | 50% / 50% |
| Thuật toán đề xuất | `calib-ifair` có ba nhóm user, bốn bản so sánh cùng mục tiêu, đo bằng NS-3 LTE | Thái Viết Đại, Nguyễn Quang Phúc | 50% / 50% |
| Kịch bản NS-3 LTE | `uav-lte.cc`, mô hình kênh Al-Hourani trong NS-3, đo theo khe | Thái Viết Đại, Nguyễn Quang Phúc | 50% / 50% |
| Scheduler Weighted PF | `wpf-ff-mac-scheduler` | Thái Viết Đại, Nguyễn Quang Phúc | 50% / 50% |
| Liên kết lý tưởng, kiểm chứng ba tầng | Chế độ `--link ideal`, delay FIFO, biểu đồ ba tầng | Thái Viết Đại, Nguyễn Quang Phúc | 50% / 50% |
| Phân tích nguyên nhân chênh lệch | `validate.py`, thí nghiệm một liên kết, phân rã | Thái Viết Đại, Nguyễn Quang Phúc | 50% / 50% |
| Điều khiển thời gian thực | Server WebSocket, dashboard, tích hợp Gazebo | Thái Viết Đại, Nguyễn Quang Phúc | 50% / 50% |
| Chạy và phân tích thí nghiệm | Các bảng, hình ở chương 6 | Thái Viết Đại, Nguyễn Quang Phúc | 50% / 50% |
| Kiểm thử | 42 test tự động | Thái Viết Đại, Nguyễn Quang Phúc | 50% / 50% |
| Báo cáo, slide | Báo cáo, slide, kịch bản thuyết trình | Thái Viết Đại, Nguyễn Quang Phúc | 50% / 50% |
| **Tổng** | | Thái Viết Đại / Nguyễn Quang Phúc | **50% / 50%** |

| Thành viên | Tỷ lệ đóng góp |
|---|---|
| Thái Viết Đại | 50% |
| Nguyễn Quang Phúc | 50% |
| **Tổng** | **100%** |

---

## 2. Tính cấp thiết và ý nghĩa

### 2.1. Bối cảnh

Sau thiên tai, trong các sự kiện đông người hay ở vùng xa, trạm gốc mặt đất thường bị hỏng, quá tải hoặc không có.
Một hướng đang được nghiên cứu nhiều là gắn trạm gốc lên UAV. UAV triển khai nhanh, bay được tới chỗ có người dùng,
và nhờ bay cao nên có đường truyền nhìn thẳng (LoS) tới mặt đất tốt hơn trạm cố định.

Khi có nhiều UAV, ở mỗi thời điểm phải quyết định cùng lúc bốn việc: user nào gắn vào UAV nào, mỗi UAV chia băng thông
và công suất cho user ra sao, và UAV bay tới đâu. Bài toán cấp phát tài nguyên này xuất hiện rất thường xuyên trên các
tạp chí IEEE như TWC, TVT, IoT-J, JSAC.

### 2.2. Hạn chế của cách làm hiện tại

Phần lớn các bài báo đánh giá thuật toán bằng mô phỏng số: tốc độ được tính theo công thức Shannon B·log₂(1+SINR).
Công thức này là giới hạn lý thuyết, không có trần và không tính tới giao thức, nên kết quả thường lạc quan và không
cho biết độ trễ hay mất gói thật. Ngược lại, khi dùng trình mô phỏng mạng như NS-3, người ta thường đặt trạm cố định
hoặc cho bay theo quỹ đạo định sẵn, không gắn với thuật toán tối ưu nào. Nếu kết quả khác lý thuyết thì cũng khó biết
là do mô hình sai hay do giao thức. Các trình mô phỏng bay như Gazebo hay PX4 thì có hình ảnh và động lực học nhưng
không có mô hình kênh và mạng.

| Cách làm | Hạn chế |
|---|---|
| Mô phỏng số kiểu bài báo (Shannon) | Quá lạc quan, không có delay và mất gói thật |
| NS-3 với trạm cố định hoặc quỹ đạo định sẵn | Không gắn với thuật toán; không tách được lỗi mô hình và ảnh hưởng của giao thức |
| Gazebo, PX4 | Không có mô hình kênh, mạng |

Nhóm chưa thấy một khung làm việc nào cho phép vừa chạy thuật toán trên mô hình giải tích như bài báo, vừa đo lại đúng
quyết định đó ở mức gói tin, giải thích được bằng số vì sao hai kết quả khác nhau, và quan sát, can thiệp trực quan.

### 2.3. Mục tiêu

Dự án đặt ra sáu mục tiêu:

1. Xây khung mô phỏng số theo đúng cách các bài báo làm (kênh Al-Hourani, Shannon có nhiễu đồng kênh, năng lượng bay
   Zeng 2019, hàng đợi theo khe), cắm được thuật toán bất kỳ và tái lập được kết quả.
2. Phát lại quyết định của thuật toán trong NS-3 LTE với eNB bay, handover và lưu lượng UDP thật, đo throughput, độ
   trễ và mất gói.
3. Dựng phép kiểm chứng ba tầng để tách lỗi của mô hình khỏi ảnh hưởng của giao thức, và giải thích bằng số mọi khoảng
   chênh.
4. Áp quyết định chia băng thông ở tầng MAC bằng một scheduler có trọng số.
5. Dùng chính những gì đo được từ NS-3 để cải tiến một heuristic cấp phát tài nguyên có ưu tiên theo ba nhóm user
   (normal, important, critical), và chứng minh cải tiến bằng phép đo gói tin chứ không chỉ bằng công thức.
6. Xây trạm điều khiển thời gian thực trên web: lái tay từng UAV, đổi tham số khi đang chạy, đo NS-3 theo lệnh, hiển thị
   3D trong Gazebo.

### 2.4. Ý nghĩa

Về nghiên cứu, dự án cho con số cụ thể về khoảng cách giữa kết quả tính của bài báo và kết quả đo trên giao thức thật:
throughput NS-3 LTE chỉ bằng 25–40% giá trị Shannon. Khoảng cách này được phân rã thành từng nguyên nhân, nên biết
được kết luận nào của lý thuyết đáng tin (thứ hạng giữa các thuật toán) và kết luận nào không (giá trị tuyệt đối, độ
trễ, hiệu quả của việc chia băng thông khi không gắn với MAC).

Về ứng dụng, kết quả cho một hệ số an toàn khi lập kế hoạch lưu lượng (chỉ nên gửi khoảng 50–60% tốc độ tính được) và
một bộ hằng số hiệu chỉnh để mô hình nhanh dự đoán đúng LTE trong khoảng ±2%.

Với môn Lập trình mạng, dự án có phần lập trình mạng ở nhiều tầng: socket UDP và đo độ trễ từng gói trong NS-3,
scheduler ở tầng MAC, giao tiếp WebSocket giữa trình duyệt và server, và gz-transport (protobuf) giữa server và Gazebo.

---

## 3. Kiến trúc và thiết kế hệ thống

### 3.1. Sơ đồ tổng thể

```
┌──────────────────────────── uavsim (Python) ────────────────────────────┐
│ SimConfig ──► Network: kênh A2G, SINR, rate, hàng đợi, năng lượng       │
│                  ▲            │                                         │
│      Action      │            │ trạng thái (vị trí, độ lợi kênh)        │
│                  │            ▼                                         │
│        Thuật toán: hover/kmeans/random × equal/maxmin, DRL (Gymnasium)  │
│                                                                         │
│  ┌─────────── run.py ──────────┐   ┌──────────── ns3.py ──────────────┐ │
│  │ so sánh thuật toán, CSV,    │   │ ghi kế hoạch plan/uavs.csv,      │ │
│  │ biểu đồ, animation          │   │ users.csv; gọi NS-3; đọc số đo   │ │
│  └─────────────────────────────┘   └──────────────┬───────────────────┘ │
│  ┌─────────── live.py ─────────────────────┐      │                     │
│  │ vòng lặp thời gian thực, lái tay, ghi    │      │                     │
│  └───┬───────────────────────┬──────────────┘      │                     │
└──────┼───────────────────────┼─────────────────────┼─────────────────────┘
       │ WebSocket (JSON)      │ gz-transport        │ subprocess + CSV
       ▼                       ▼ (protobuf)          ▼
 Dashboard web           Gazebo Harmonic        NS-3 3.47 (C++): uav-lte
 (bản đồ 2D, chỉ số,     (hiển thị 3D trên      link=lte:   eNB bay, UE, EPC,
  biểu đồ, lái tay)       bãi thảm họa)                     handover X2, UDP
                                                link=ideal: liên kết điểm-điểm,
                                                            tốc độ = rate lý thuyết
                                                      │
                                                      ▼
                                       ns3_slots.csv: gói gửi/nhận, byte,
                                       delay từng khe từng user; trace PHY/MAC
```

### 3.2. Các thành phần

| Thành phần | Công nghệ | Vai trò |
|---|---|---|
| `config.py` | Python dataclass | Chứa toàn bộ tham số, kiểm tra hợp lệ, đọc JSON |
| `channel.py`, `energy.py` | NumPy | Mô hình kênh Air-to-Ground, công suất bay |
| `network.py` | NumPy | Trạng thái mạng, ràng buộc, SINR và rate, hàng đợi và delay FIFO, bước thời gian |
| `algorithms.py` | NumPy | 6 thuật toán baseline và giao diện chung để thêm thuật toán |
| `env.py` | Gymnasium 1.0 | Môi trường cho học tăng cường |
| `run.py`, `animate.py` | Matplotlib | Chạy thí nghiệm, xuất CSV, vẽ biểu đồ, GIF |
| `ns3.py` | subprocess | Ghi kế hoạch, chạy NS-3 song song, đọc số đo, phát lại phiên đã ghi |
| `validate.py` | NumPy | Phân tích nguyên nhân chênh lệch |
| `uav-lte.cc` | C++, NS-3 3.47 (module LTE) | Kịch bản mô phỏng mức gói tin với hai chế độ liên kết |
| `wpf-ff-mac-scheduler` | C++ | Scheduler Weighted Proportional Fair |
| `live.py`, `web/index.html` | asyncio, websockets, HTML canvas | Điều khiển thời gian thực và dashboard |
| `gazebo.py` | gz-transport 13, gz-msgs 10, Gazebo Sim 8 | Hiển thị 3D |

### 3.3. Luồng dữ liệu

Khi chạy thí nghiệm, thuật toán chạy trên mô hình từ khe đầu đến khe cuối và mỗi khe cho ra một quyết định. Toàn bộ
quyết định được ghi thành một *kế hoạch*: vị trí UAV, vị trí user, UAV phục vụ, tốc độ gửi, tỷ lệ băng thông và tốc
độ phục vụ lý thuyết của từng user ở từng khe. NS-3 đọc kế hoạch, dựng mạng, phát lại đúng kế hoạch đó và ghi số đo
theo khe. Cuối cùng `ns3.py` đặt số đo cạnh số tính của mô hình, gộp nhiều seed và vẽ biểu đồ.

Khi điều khiển thời gian thực, cứ 0.5 giây server chạy một khe của mô hình (một khe dài 1 giây, tức mô phỏng nhanh gấp
đôi thời gian thực). Ở mỗi khe, thuật toán ra quyết định như bình thường, nhưng vận tốc của UAV đang được lái tay bị
thay bằng lệnh gửi từ trình duyệt. Trạng thái mới được gửi tới mọi trình duyệt đang mở qua WebSocket, đồng thời vị trí
được gửi sang Gazebo bằng một lần gọi service. Khi người dùng bấm "Ghi", phiên được lưu thành kế hoạch cùng định dạng
với thí nghiệm, nên có thể phát lại trong NS-3.

### 3.4. Thiết kế kiểm chứng ba tầng

```
Tầng 1: Lý thuyết            Tầng 2: NS-3 liên kết lý tưởng      Tầng 3: NS-3 LTE
công thức Shannon,     ──►   gói UDP thật, tốc độ liên kết  ──►  eNB/UE/EPC, PHY, AMC,
hàng đợi theo khe            = rate lý thuyết từng khe,          scheduler, HARQ, RLC,
                             hàng đợi DropTail 1 MiB             handover
        └──── khớp < 1% ────┘         └─────── chênh lệch ──────┘
```

Nếu chỉ so lý thuyết với NS-3 LTE thì khi hai bên khác nhau, ta không biết là do mô hình tính sai hay do LTE. Tầng
giữa giải quyết chuyện này: nó giữ nguyên mọi thứ của lý thuyết (tốc độ phục vụ, bộ đệm, lưu lượng) và chỉ thay công
thức bằng gói tin thật. Nếu tầng 1 và tầng 2 khớp thì mô hình hàng đợi và toàn bộ đường ống xử lý là đúng, và phần chênh
còn lại giữa tầng 2 và tầng 3 chỉ có thể đến từ giao thức LTE.

### 3.5. Các lựa chọn thiết kế

Thuật toán chạy trên mô hình Python, còn NS-3 chỉ phát lại. Lý do là mô hình nhanh hơn NS-3 khoảng ba bậc (khoảng 1 ms
so với khoảng 4 s cho một khe) và dễ cắm các thuật toán tối ưu hay học tăng cường. Cái giá phải trả là liên kết chỉ
một chiều: NS-3 không phản hồi lại cho thuật toán trong lúc chạy.

Mô hình kênh Al-Hourani được viết lại thành một lớp `PropagationLossModel` trong C++ để hai bên dùng đúng một công
thức; phép so SINR sau này cho thấy hai bên lệch nhau không quá 0.1 dB. NS-3 được gọi qua subprocess và trao đổi bằng
file CSV, vì Python bindings của NS-3 đang tắt trong bản build, và CSV thì dễ kiểm tra, dễ lưu lại. Bộ phát UDP được
viết riêng thay vì dùng `UdpClient`, vì `UdpClient` chỉ đổi khoảng cách gửi sau khi gói đang chờ đã đi, không đổi tốc
độ đúng đầu khe được.

Khi một quyết định vi phạm ràng buộc, mô hình báo lỗi thay vì tự sửa, để lỗi của thuật toán lộ ra ngay. Riêng vận tốc
thì được co về giới hạn, vì đó là giới hạn vật lý và các thuật toán học tăng cường thường xuất vận tốc thô. Gazebo chỉ
dùng để hiển thị, không chạy PX4: quỹ đạo nhờ đó khớp tuyệt đối với mô hình và tránh được việc cài đặt PX4 vốn phức
tạp, đổi lại không có động lực học bay thật.

### 3.6. So sánh với các hệ thống hiện có

| Tiêu chí | Mô phỏng số kiểu bài báo | Chỉ dùng NS-3 | Phiên bản cũ của nhóm (dashboard, NS-3 Wi-Fi, Gazebo) | Dự án này |
|---|---|---|---|---|
| Kênh UAV chuẩn (Al-Hourani) | Có | Thường không | Không | Có, ở cả hai phía |
| Thuật toán cấp phát và quỹ đạo | Có | Không | Chia ngân sách lưu lượng đơn giản | 6 baseline, giao diện thêm thuật toán, môi trường DRL |
| Đo mức gói tin | Không | Có | Có (Wi-Fi) | Có (LTE và liên kết lý tưởng) |
| Tách lỗi mô hình và ảnh hưởng giao thức | Không | Không | Không | Có (ba tầng) |
| Giải thích chênh lệch bằng số | Không | Không | Không | Có (phân rã, sai số ±3%) |
| Áp cấp phát ở tầng MAC | Không áp dụng | Ít khi | Không | Có (WPF) |
| Điều khiển thời gian thực, 3D | Không | Không | Có | Có, đồng bộ với mô hình |
| Kiểm thử tự động, tái lập | Tùy | Tùy | Ít | 42 test, tái lập từng bit |

So với phiên bản trước, nhóm thay NS-3 Wi-Fi bằng LTE, thay cách chia lưu lượng đơn giản bằng bài toán cấp phát đầy đủ,
và thêm phần kiểm chứng. Phần dashboard và Gazebo được làm lại để đồng bộ với mô hình thay vì chạy độc lập.

---

## 4. Mô hình toán học và phát biểu bài toán

### 4.1. Kịch bản

Xét M UAV (mặc định 3) bay ở độ cao cố định H = 100 m, mỗi UAV là một trạm gốc phát đường xuống. Có K user mặt đất
(mặc định 20) trong một vùng vuông cạnh L = 1000 m, đứng yên hoặc đi bộ ngẫu nhiên. Mỗi user được đúng một UAV phục vụ,
hoặc không được UAV nào phục vụ. Trong cùng một UAV, các user chia băng thông theo kiểu OFDMA nên không gây nhiễu cho
nhau. Các UAV dùng chung một băng tần (tái sử dụng tần số bằng 1), vì vậy tín hiệu của UAV này là nhiễu đối với user
của UAV khác. Thời gian chia thành N khe, mỗi khe dài Δt = 1 s, và trong một khe vị trí và kênh được coi là không đổi.

### 4.2. Đầu vào, đầu ra và biến quyết định

Đầu vào gồm vị trí ban đầu của UAV, vị trí user theo thời gian, các tham số hệ thống ở mục 4.3 và lưu lượng đến (nếu
xét hàng đợi). Đầu ra là tốc độ của từng user, throughput, độ trễ, mất gói, năng lượng bay và các chỉ số tổng hợp ở mục
4.9. Ở mỗi khe n, thuật toán chọn bốn nhóm biến:

| Biến | Ký hiệu | Miền | Ý nghĩa |
|---|---|---|---|
| Liên kết | a_k[n] | {0, …, M−1} ∪ {∅} | UAV phục vụ user k |
| Băng thông | b_k[n] | [0, 1] | Tỷ lệ băng thông của UAV phục vụ dành cho k |
| Công suất | p_k[n] | ≥ 0 (W) | Công suất phát dành cho k |
| Vận tốc | v_m[n] | ℝ², ‖v_m‖ ≤ V_max | Vận tốc ngang của UAV m |

### 4.3. Tham số

| Tham số | Ký hiệu | Giá trị | Ghi chú |
|---|---|---|---|
| Số UAV, số user | M, K | 3, 20 | Các bài báo thường dùng M = 2–6, K = 10–50 |
| Cạnh vùng | L | 1000 m | |
| Độ cao | H | 100 m | Dưới giới hạn 120 m của nhiều quy định bay |
| Số khe, độ dài khe | N, Δt | 200, 1 s | |
| Vận tốc tối đa | V_max | 20 m/s | |
| Tần số sóng mang | f_c | 2 GHz | Băng LTE/5G dưới 6 GHz |
| Băng thông mỗi UAV | B | 10 MHz | |
| Mật độ nhiễu | N₀ | −169 dBm/Hz | −174 dBm/Hz nhiễu nhiệt cộng hệ số nhiễu 5 dB |
| Công suất tối đa | P_max | 1 W | |
| Ngưỡng QoS | r_min | 1 Mbps | |
| Môi trường | | urban | a = 9.61, b = 0.16, η_LoS = 1 dB, η_NLoS = 20 dB |
| Gói, bộ đệm | | 1200 byte, 1 MiB | Giống NS-3 |
| Phân bố user | | theo cụm | M tâm cụm trong khoảng 15–85% vùng, độ lệch chuẩn 80 m |

### 4.4. Giả thiết

Mô hình dựa trên các giả thiết sau. Độ cao UAV cố định, chỉ tối ưu vị trí ngang. Kênh dùng suy hao trung bình theo xác
suất LoS chứ không lấy mẫu LoS/NLoS ở từng khe; fading nhỏ Rician là tùy chọn. Mỗi UAV được coi là trải công suất đều
trên toàn băng khi tính nhiễu. Chỉ xét đường xuống và chỉ tính năng lượng bay, vì công suất phát (không quá 1 W) nhỏ hơn
công suất bay hai bậc. Không xét backhaul, pin hay tránh va chạm. Tốc độ của khe n được tính tại vị trí đầu khe, còn vận
tốc chọn ở khe n chỉ có tác dụng từ khe n+1.

### 4.5. Mô hình kênh

UAV m ở q_m = (x_m, y_m, H), user k ở w_k = (x_k, y_k, 0). Khoảng cách ngang, khoảng cách ba chiều và góc nâng là

$$r_{mk} = \|q_m - w_k\|,\qquad d_{mk} = \sqrt{r_{mk}^2 + H^2},\qquad \theta_{mk} = \frac{180}{\pi}\arctan\frac{H}{r_{mk}}.$$

Nhóm dùng mô hình của Al-Hourani và cộng sự (2014), mô hình được dùng nhiều nhất cho bài toán đặt vị trí UAV. Xác suất
có đường nhìn thẳng tăng theo góc nâng

$$P_{LoS}(\theta) = \frac{1}{1 + a\,\exp\!\big(-b(\theta - a)\big)},$$

và suy hao trung bình (dB) bằng suy hao không gian tự do cộng phần suy hao thêm, có trọng số theo xác suất LoS:

$$PL_{mk} = 20\log_{10}\!\Big(\frac{4\pi f_c d_{mk}}{c}\Big) + P_{LoS}\,\eta_{LoS} + (1-P_{LoS})\,\eta_{NLoS}.$$

| Môi trường | a | b | η_LoS (dB) | η_NLoS (dB) |
|---|---|---|---|---|
| suburban | 4.88 | 0.43 | 0.1 | 21 |
| urban (mặc định) | 9.61 | 0.16 | 1.0 | 20 |
| dense urban | 12.08 | 0.11 | 1.6 | 23 |
| highrise | 27.23 | 0.08 | 2.3 | 34 |

Có thể thay bằng mô hình chỉ có LoS của Wu, Zeng và Zhang (2018), g_mk = β₀/d_mk² với β₀ = −60 dB, và có thể nhân thêm
fading Rician h = √(K/(K+1)) + √(1/(K+1))·h̃ với h̃ ~ CN(0,1). Độ lợi kênh cuối cùng là g_mk = 10^(−PL_mk/10)·|h|².

Bảng dưới tính bằng chính mô hình (urban, 2 GHz, H = 100 m, 1 W trên 10 MHz, nhiễu −99 dBm). Khi user ra xa từ 100 m
tới 300 m, suy hao tăng gần 20 dB, và phần lớn là do mất đường nhìn thẳng chứ không phải do khoảng cách. Đây là lý do
việc đưa UAV lại gần cụm user có lợi rất lớn.

| Khoảng cách ngang | Góc nâng | P_LoS | Suy hao | SNR | Tốc độ trên cả 10 MHz |
|---|---|---|---|---|---|
| 0 m | 90° | 1.00 | 79.5 dB | 49.5 dB | 164.5 Mbps |
| 100 m | 45° | 0.97 | 83.1 dB | 45.9 dB | 152.5 Mbps |
| 200 m | 26.6° | 0.61 | 93.9 dB | 35.1 dB | 116.8 Mbps |
| 300 m | 18.4° | 0.30 | 102.8 dB | 26.2 dB | 87.1 Mbps |
| 500 m | 11.3° | 0.12 | 110.3 dB | 18.7 dB | 62.2 Mbps |

### 4.6. SINR và tốc độ

Với user k được UAV m = a_k phục vụ, mật độ công suất tín hiệu nhận là S_k = p_k g_mk / (b_k B). Mật độ nhiễu đồng kênh
từ các UAV khác là

$$I_k = \sum_{j \ne m} \frac{P_j}{B}\, g_{jk},\qquad P_j = \sum_{k':\,a_{k'}=j} p_{k'},$$

trong đó P_j là tổng công suất UAV j phát. Theo Shannon, như các bài báo vẫn dùng,

$$r_k = b_k B \log_2\!\left(1 + \frac{S_k}{I_k + N_0}\right).$$

Để gần với LTE hơn, nhóm dùng thêm công thức Shannon có cắt ngọn trong 3GPP TR 36.942 (Phụ lục A.1):

$$SE_k = \begin{cases} 0 & SINR_k < -10\text{ dB}\\ \min\big(\alpha\log_2(1+SINR_k),\ SE_{max}\big) & \text{trường hợp còn lại}\end{cases},\qquad r_k = b_k B\cdot SE_k,$$

với α = 0.6 và SE_max = 4.4 bit/s/Hz theo chuẩn. Đo trên NS-3 LTE 10 MHz SISO, nhóm thu được α = 0.401 và
SE_max = 3.514 (mục 6.4).

### 4.7. Năng lượng bay

Công suất bay của UAV cánh quay theo Zeng, Xu và Zhang (2019):

$$P(V) = P_0\Big(1+\frac{3V^2}{U_{tip}^2}\Big) + P_i\Big(\sqrt{1+\frac{V^4}{4v_0^4}}-\frac{V^2}{2v_0^2}\Big)^{1/2} + \tfrac12 d_0\rho s A V^3,$$

với P₀ = 79.86 W, P_i = 88.63 W, U_tip = 120 m/s, v₀ = 4.03 m/s, d₀ = 0.6, ρ = 1.225 kg/m³, s = 0.05, A = 0.503 m².
Ba số hạng lần lượt là công suất thắng ma sát cánh quạt, công suất tạo lực nâng và công suất thắng lực cản thân máy.
Khi hover, UAV tiêu thụ 168.5 W; công suất nhỏ nhất là 126.0 W ở 10.2 m/s, tức bay vừa phải còn tiết kiệm hơn đứng yên;
ở 20 m/s là 178.3 W. Năng lượng một khe là E_m[n] = P(‖v_m[n]‖)·Δt.

### 4.8. Di chuyển, lưu lượng và hàng đợi

Sau khi co vận tốc về V_max, vị trí UAV được cập nhật q_m[n+1] = q_m[n] + v_m[n]·Δt rồi giới hạn trong vùng. User đứng
yên, hoặc mỗi khe đi một bước theo hướng ngẫu nhiên.

Khi xét lưu lượng, mỗi user nhận lưu lượng tốc độ không đổi λ, tức A = λΔt bit mỗi khe, xếp vào một hàng đợi riêng tại
UAV với bộ đệm Q_max = 1 MiB:

$$Q_k[n+1] = \min\Big(\max\big(Q_k[n] + A - r_k[n]\,\Delta t,\ 0\big),\ Q_{max}\Big).$$

Số bit được phục vụ trong khe là S_k[n] = min(Q_k[n] + A, r_k[n]Δt), số bit bị bỏ do tràn bộ đệm là
D_k[n] = max(Q_k[n] + A − S_k[n] − Q_max, 0).

Độ trễ được tính chính xác theo thứ tự FIFO. Gọi A_k(t) là số bit đã vào hàng đợi tính đến thời điểm t (không kể bit
bị bỏ) và S_k(t) là số bit đã được phục vụ. Bit thứ x vào hàng đợi lúc A_k⁻¹(x) và rời đi lúc S_k⁻¹(x), nên thời gian
chờ của nó là S_k⁻¹(x) − A_k⁻¹(x). Độ trễ của user k trong khe n là trung bình thời gian chờ của các bit được phục vụ
trong khe, cộng thời gian phát một gói:

$$D^{\text{delay}}_k[n] = \frac{1}{S_k[n]}\int_{\text{bit phục vụ trong khe } n}\big(S_k^{-1}(x) - A_k^{-1}(x)\big)\,dx \;+\; \frac{8\cdot 1200}{r_k[n]}.$$

Độ trễ của cả mạng là trung bình theo số bit được phục vụ. Tích phân được tính số bằng cách chia mỗi khe thành 200 bước
nhỏ. Ban đầu nhóm dùng định luật Little với độ dài hàng đợi trung bình (Q đầu khe + Q cuối khe)/2, nhưng cách này sai
khi hàng đợi cạn hoặc đầy giữa khe, hoặc khi bit được phục vụ trong khe đã đến từ các khe trước; sai số so với NS-3 lên
tới 25%. Với công thức FIFO, sai số còn dưới 1% (mục 6.8).

Mất gói được định nghĩa giống cách NS-3 đo (1 − gói nhận/gói gửi), tức tính cả phần còn nằm trong hàng đợi khi kết thúc:

$$\text{loss} = \frac{\sum_{n,k} D_k[n] + \sum_k Q_k[N]}{\sum_{n,k} A}.$$

Mô hình còn có hai tùy chọn mô phỏng hành vi của LTE, mặc định tắt để giữ đúng giả thiết của các bài báo. Với tùy chọn
chia băng linh hoạt, trong mỗi UAV băng thông được chia lại theo nhu cầu thực (Q + A) bằng water-filling max-min. Với
tùy chọn nhiễu theo tải, nhiễu từ UAV j được nhân với tỷ lệ băng thông UAV j thực sự dùng ở khe trước.

### 4.9. Chỉ số đánh giá

| Chỉ số | Công thức | Ý nghĩa |
|---|---|---|
| Sum rate | Σ_k r_k | Hiệu quả tổng |
| Min rate | min_k r_k | User kém nhất |
| Chỉ số Jain | (Σ r_k)² / (K·Σ r_k²) | Mức công bằng, bằng 1 khi mọi user có tốc độ như nhau |
| Coverage | (1/K)·#{k : r_k ≥ r_min} | Tỷ lệ user đạt QoS |
| Năng lượng | Σ_m P(‖v_m‖)·Δt | J mỗi khe |
| Hiệu suất năng lượng | Tổng bit / tổng J | bit/J |
| Throughput, độ trễ, mất gói | Mục 4.8; NS-3 đo trực tiếp | QoS ở mức gói tin |

### 4.10. Phát biểu bài toán

**Bài toán của đề tài.** Phân bổ liên kết, băng thông và quỹ đạo cho M UAV-BS sao cho người dùng được phục vụ công bằng
mà không làm giảm hiệu quả tổng, và kết quả phải đúng khi đo trên mạng LTE (NS-3), không chỉ đúng trên công thức Shannon.
Trong kịch bản cứu hộ, người dùng không quan trọng như nhau, nên mỗi user k thuộc một trong ba nhóm c(k):

| Nhóm | Ví dụ | Trọng số w_c | Tốc độ tối thiểu mong muốn r_min,c | Tỷ lệ trong thí nghiệm |
|---|---|---|---|---|
| normal | Người dân | 1 | 0.5 Mbps | 60% (12/20) |
| important | Điều phối, camera giám sát | 2 | 1 Mbps | 25% (5/20) |
| critical | Đội cứu hộ, y tế | 4 | 2 Mbps | 15% (3/20) |

Nhóm của user được bốc ngẫu nhiên theo seed, độc lập với vị trí. Mục tiêu "công bằng có ưu tiên mà không giảm hiệu quả"
được viết thành tiện ích công bằng tỷ lệ có trọng số (weighted proportional fairness):

$$\max_{\{a,b,p,v\}}\ \sum_{n=1}^{N}\sum_{k=1}^{K} w_{c(k)}\,\log\big(r_k[n] + r_0\big)$$

$$\text{s.t.}\quad \sum_{k:\,a_k[n]=m} b_k[n] \le 1,\quad \sum_{k:\,a_k[n]=m} p_k[n] \le P_{max},\quad \|v_m[n]\| \le V_{max},\quad q_m[n] \in [0,L]^2,\quad \forall m, n,$$

với r_0 = 1 kbit/s để tránh log của 0. Ngưỡng r_min,c không đưa vào ràng buộc cứng, vì khi kênh quá xấu hoặc quá tải
thì không có nghiệm thỏa mọi ngưỡng. Thay vào đó nó dùng để chấm QoS từng nhóm: user đạt QoS trong một khe khi
throughput ≥ min(r_min,c, 0.9·λ), với λ là lưu lượng gửi tới user (user không thể nhận nhiều hơn phần được gửi).
Trọng số w_c là cách mềm để đẩy user nhóm cao qua ngưỡng: user có w lớn hơn được nhận nhiều tài nguyên hơn (mục 4.11
nêu cách chia cụ thể). Khi mọi w = 1 (một nhóm), bài toán trở về tổng log thông thường.

Nhóm chọn tổng log vì nó nằm giữa hai mục tiêu quen thuộc. Tối đa tổng tốc độ
Σ r_k dồn băng thông cho user kênh tốt, user ở rìa gần như không được phục vụ. Tối đa tốc độ nhỏ nhất min r_k thì ngược
lại, phải cho user kém nhất rất nhiều băng thông nên tổng tốc độ giảm mạnh. Tổng log phạt nặng user có tốc độ gần 0
nhưng vẫn thưởng cho việc tăng tổng.

**Hai câu hỏi tách biệt.** Bài toán này không lồi và có biến nguyên: a_k rời rạc, vị trí UAV nằm trong cả độ lợi kênh
lẫn nhiễu, và nhiễu lại phụ thuộc vào quyết định của mọi UAV. Vì vậy mọi thuật toán, kể cả thuật toán đề xuất, đều chỉ
giải xấp xỉ. Khi so sánh cần tách hai câu hỏi:

1. *Thuật toán tối ưu cái gì (mục tiêu)?* Mỗi baseline có mục tiêu riêng của nó (bảng dưới).
2. *Kết quả được chấm bằng gì (đánh giá)?* Mọi thuật toán, không phân biệt mục tiêu, được chấm bằng cùng một bộ chỉ số
   ở mục 4.9, đo bằng NS-3 ở mức gói tin: tổng throughput, min throughput, chỉ số Jain, độ trễ, mất gói.

| Thuật toán | Mục tiêu nội tại | Mô hình tốc độ dùng để quyết định | Vai trò |
|---|---|---|---|
| `*-equal` | Gần với max Σ r_k (chia đều băng) | Không cần | Baseline hiệu quả |
| `*-maxmin` | max min r_k trong từng UAV | Shannon, bỏ qua nhiễu | Baseline công bằng |
| `kmeans-wmaxmin` | max min r_k/w_k trong từng UAV (max-min có trọng số) | Shannon, bỏ qua nhiễu | Baseline biết nhóm |
| DRL (PPO) | max Σ r_k, phạt r_k < r_min | Shannon | Baseline học máy |
| `kmeans-ifair` | Σ w log r (chỉ khối chia băng) | LTE hiệu chỉnh, có nhiễu | Bản tách thành phần |
| `calib-equal` | Σ w log r (chỉ khối di chuyển) | LTE hiệu chỉnh, có nhiễu | Bản tách thành phần |
| `calib-ifair-noclass` | Σ log r (mọi w = 1) | LTE hiệu chỉnh, có nhiễu | Cùng mục tiêu, bỏ qua nhóm |
| `calib-ifair-shannon` | Σ w log r | Shannon, có nhiễu, không trần | Cùng mục tiêu, mô hình như bài báo |
| **`calib-ifair`** | **Σ w log r (cả hai khối)** | **LTE hiệu chỉnh, có nhiễu** | **Đề xuất** |

Các baseline `equal`, `maxmin`, DRL không biết nhóm user: chúng coi mọi user như nhau. Baseline `kmeans-wmaxmin` biết
nhóm, để so sánh công bằng với thuật toán đề xuất trên cùng thông tin.

Các baseline có mục tiêu khác với thuật toán đề xuất. Đây là cách so sánh thường gặp: chúng đại diện cho các lựa chọn
có sẵn (tối đa hiệu quả, tối đa công bằng) và được chấm bằng cùng chỉ số. Để biết thuật toán đề xuất thắng vì *phương
pháp* chứ không chỉ vì *mục tiêu khác*, nhóm thêm bốn bản cùng mục tiêu. `kmeans-ifair` và `calib-equal` bỏ bớt một
khối. `calib-ifair-noclass` giữ nguyên thuật toán nhưng cho mọi w = 1, để thấy trọng số nhóm đổi được gì và mất gì.
`calib-ifair-shannon` giữ nguyên mục tiêu và cách tìm kiếm nhưng tính tốc độ bằng Shannon, đúng cách các bài báo làm,
để tách phần lợi ích do đường cong LTE hiệu chỉnh.

### 4.11. Những điều chỉnh so với mô hình chuẩn

So với mô hình thường thấy trong các bài báo, nhóm có năm điều chỉnh: tính độ trễ FIFO chính xác thay cho định luật
Little (sai số từ 1–25% xuống dưới 1%); định nghĩa mất gói thống nhất với phép đo gói tin; bộ hằng số LTE đo được
(α = 0.401, SE_max = 3.514) giúp mô hình dự đoán NS-3 trong khoảng ±2%; hai tùy chọn mô phỏng hành vi LTE (chia băng
linh hoạt, nhiễu theo tải) để giải thích chênh lệch; và việc cùng một kế hoạch chạy được ở cả ba tầng.

Phần cải tiến chính là heuristic `calib-ifair` (mục 5.5). Đây không phải một thuật toán mới về nguyên lý: các thành
phần của nó đều dựa trên kỹ thuật đã có (tiện ích công bằng tỷ lệ có trọng số, max-min có trọng số, đặt UAV theo
k-means, tìm kiếm cục bộ, scheduler PF có trọng số). Điểm cải tiến nằm ở cách kết hợp và cách kiểm chứng: heuristic giải
xấp xỉ bài toán Σ w log r ở mục 4.10 với ba nhóm user, tính SINR có nhiễu từ mọi UAV khi chia băng (các baseline bỏ qua
nhiễu), tinh chỉnh vị trí UAV theo cùng mục tiêu, áp quyết định ở tầng MAC qua scheduler WPF, và được kiểm chứng ở mức
gói tin bằng NS-3 LTE. Tốc độ dự đoán dùng ánh xạ SINR → tốc độ đo được từ
NS-3; tuy vậy, mục 6.12 cho thấy thay ánh xạ này bằng Shannon gần như không đổi kết quả, nên lợi ích đến từ việc tính
nhiễu, áp ở MAC và trọng số nhóm. Hàm nó tối ưu là

$$U = \sum_k w_k\log\big(\hat r_k + r_0\big),\qquad \hat r_k = \frac{B\,w_k}{\sum_{k':a_{k'}=a_k} w_{k'}/\widehat{SE}_{k'}},\qquad \widehat{SE}_k = \min\big(0.401\log_2(1+SINR_k),\ 3.514\big),$$

trong đó w_k = w_{c(k)} là trọng số nhóm, \hat r_k là tốc độ dự đoán của user k khi UAV chia băng b_k ∝ w_k/ŜE_k (tốc
độ các user trong một UAV tỷ lệ với trọng số), và r_0 = 1 kbit/s tránh log của 0.

Phát biểu đầy đủ, giải lại ở mỗi khe n (bài toán theo từng khe, không nhìn trước cả chu kỳ):

$$\max_{\{a_k[n]\},\ \{b_k[n]\},\ \{q_m[n+1]\}}\ \sum_{k=1}^{K}w_k\log\big(\hat r_k[n] + r_0\big)$$

$$\text{với}\quad \hat r_k[n] = b_k[n]\,B\,\widehat{SE}_k[n],\qquad
\widehat{SE}_k[n] = \begin{cases}\min\big(\alpha\log_2(1+SINR_k(q[n+1])),\ SE_{max}\big) & SINR_k \ge 0.1\\ 0 & SINR_k < 0.1\end{cases},
\quad \alpha=0.401,\ SE_{max}=3.514$$

$$SINR_k(q) = \frac{p_{a_k}\,g_{a_k k}(q_{a_k})}{\sum_{j\ne a_k} p_j\,g_{jk}(q_j) + \sigma^2}$$

$$\text{s.t.}\quad
\begin{aligned}
&\text{(C1)}\ a_k[n] = \arg\max_m g_{mk}(q_m[n]) && \text{(user nối UAV có độ lợi lớn nhất)}\\
&\text{(C2)}\ \textstyle\sum_{k:\,a_k[n]=m} b_k[n] \le 1,\ \ b_k[n]\ge 0 && \forall m\\
&\text{(C3)}\ \|q_m[n+1]-q_m[n]\| \le V_{max}\,\Delta t,\ \ q_m[n+1]\in[0,L]^2 && \forall m\\
&\text{(C4)}\ p_k[n] = b_k[n]\,P_{max} && \text{(mật độ công suất phẳng } P_{max}/B\text{, không tối ưu)}\\
&\text{(C5)}\ \#\{m : \exists k,\ a_k[n]=m\}\ \text{không giảm} && \text{(không tắt UAV nào)}
\end{aligned}$$

Bài toán được tách làm hai khối và giải xấp xỉ:

- **Chia băng (ifair), với vị trí cố định.** Với mỗi UAV m, bài toán con max Σ_{k∈m} w_k log(b_k B ŜE_k) với
  Σ b_k ≤ 1 có nghiệm b_k = w_k / Σ_{k'∈m} w_{k'} (băng thông tỷ lệ với trọng số, không phụ thuộc kênh). Nhóm chọn
  b_k ∝ w_k / max(ŜE_k, 0.05) thay vì nghiệm đó, để *tốc độ* dự đoán tỷ lệ với trọng số,
  r̂_k = B·w_k / Σ_{k'∈m} w_{k'}/ŜE_{k'}. Công thức rút gọn này chỉ đúng khi mọi user trong UAV có ŜE ≥ 0.05; khi đó
  trong một UAV, user critical có tốc độ gấp 4 lần user normal dù kênh của nó xấu hơn (user có ŜE = 0 vẫn có tốc độ 0). Đây là max-min có trọng số trong từng UAV, ưu tiên user kém nhất của mỗi nhóm hơn nghiệm tổng
  log thuần; hàm Σ w log r được dùng ở khối di chuyển bên dưới để đánh giá vị trí.
- **Di chuyển (calib), với cách chia băng ở trên.** UAV còn cách tâm cụm k-means quá một bước thì bay thẳng về tâm
  cụm. Khi đã tới, ở mỗi khe lần lượt từng UAV (UAV sau thấy vị trí mới của UAV trước, tức tối ưu theo từng tọa độ)
  thử đứng yên hoặc đi theo 8 hướng với 2 cỡ bước (V_max·Δt và V_max·Δt/4), giữ nước đi làm U lớn nhất và thỏa
  (C3), (C5). Khối này không đảm bảo tìm được tối ưu toàn cục vì U không lõm theo q (nhiễu phụ thuộc vị trí mọi UAV).
  Chi phí mỗi khe là M × 17 lần tính U, mỗi lần O(MK).

So với bài toán ở mục 4.10, có ba điểm khác. Thứ nhất, bài toán cả chu kỳ được giải tham lam theo từng khe. Thứ hai, tốc
độ được tính bằng đường cong LTE đo được từ NS-3 thay cho Shannon. Thứ ba, công suất không được tối ưu (C4) và quyết định
chia băng được áp ở tầng MAC bằng scheduler WPF với trọng số b_k.

---

## 5. Triển khai hệ thống và giải thuật

### 5.1. Công nghệ

| Lớp | Công nghệ | Phiên bản |
|---|---|---|
| Hệ điều hành | Ubuntu | 22.04 |
| Mô hình | Python, NumPy, Matplotlib, Gymnasium | 3.10, 2.2, 3.9, 1.0 |
| Mô phỏng mạng | NS-3 (LTE/LENA, EPC, FlowMonitor) | 3.47 |
| Điều khiển thời gian thực | asyncio, websockets, HTML5 canvas | websockets 16.1 |
| Hiển thị 3D | Gazebo Sim, gz-transport, gz-msgs | 8 (Harmonic), 13, 10 |
| Kiểm thử | pytest | 8.4 |

### 5.2. Quá trình triển khai

Nhóm bắt đầu bằng mô hình kênh, tốc độ và năng lượng, kiểm tra bằng các giá trị đã biết (chẳng hạn kênh LoS phải đúng
bằng β₀/d², công suất hover phải bằng 168.49 W). Tiếp theo là vòng lặp mô phỏng, phần kiểm tra ràng buộc, sáu thuật toán
baseline và môi trường Gymnasium.

Sau đó nhóm viết kịch bản NS-3 LTE: lớp kênh Al-Hourani bằng C++, eNB bay theo các điểm mốc, handover X2 theo kế hoạch,
bộ phát UDP đổi tốc độ đúng đầu khe và phần đo theo khe. Lần chạy ma trận đầu tiên (90 run) cho thấy NS-3 chỉ đạt khoảng
70% so với mô hình. Để tìm nguyên nhân, nhóm bật trace PHY/MAC, làm thí nghiệm tách nhiễu, thí nghiệm một liên kết và
phân rã khoảng chênh.

Tiếp đó nhóm thêm lưu lượng và hàng đợi vào mô hình để so độ trễ và mất gói (63 run), rồi viết scheduler Weighted PF để
áp quyết định chia băng thông ở tầng MAC (42 run). Chế độ liên kết lý tưởng được thêm vào sau cùng; trong quá trình so
tầng 1 với tầng 2, nhóm phát hiện và sửa ba chỗ lệch (định nghĩa mất gói, công thức độ trễ, đơn vị bộ đệm) cho tới khi
sai số dưới 1% (105 run). Cuối cùng là hệ thống điều khiển thời gian thực gồm server, dashboard và Gazebo.

### 5.3. Vòng lặp mô phỏng

```
Thủ tục MÔ_PHỎNG(cấu hình, thuật toán):
    khởi tạo vị trí UAV, user theo seed; tính ma trận độ lợi kênh g[M×K]
    thuật toán.khởi_tạo(mạng)
    với n = 0 … N−1:
        quyết_định ← thuật toán.quyết_định(mạng)          // a, b, p, v
        kiểm tra ràng buộc; vi phạm thì báo lỗi
        r ← TỐC_ĐỘ(quyết_định)                           // tại vị trí đầu khe
        nếu có lưu lượng: cập nhật hàng đợi, độ trễ FIFO, mất gói
        v ← co ‖v‖ về V_max;  E ← P(‖v‖)·Δt
        ghi chỉ số của khe
        q ← giới hạn trong vùng(q + v·Δt);  di chuyển user nếu có
        tính lại g cho khe sau
```

Mọi số ngẫu nhiên đi qua một bộ sinh có seed. Thuật toán ngẫu nhiên dùng bộ sinh riêng (seed + 1), nên dù thuật toán có
dùng số ngẫu nhiên hay không thì mọi thuật toán cùng seed vẫn thấy đúng một kịch bản, và việc so sánh là công bằng.

### 5.4. Thuật toán baseline

Mỗi baseline ghép một chiến lược di chuyển (hover, kmeans, random) với một chiến lược chia băng thông (equal, maxmin),
tổng cộng sáu thuật toán. Cả sáu dùng chung cách liên kết: mỗi user gắn vào UAV có kênh tốt nhất, a_k = argmax_m g_mk.

Trong mỗi UAV, băng thông được chia theo trọng số b_k = w_k / Σ w_k'. Với equal, mọi user có w_k = 1. Với maxmin,
w_k = 1/SE_k, trong đó SE_k = log₂(1 + P_max g_{a_k k} / (B N₀)). Lý do: công suất được chia tỷ lệ với băng thông,
p_k = b_k P_max, nên mật độ công suất trên phần băng của user nào cũng là P_max/B. Khi không có nhiễu, r_k = b_k B SE_k,
và muốn mọi user trong một UAV có tốc độ bằng nhau thì b_k phải tỷ lệ nghịch với SE_k.

Với hover, UAV đứng yên ở vị trí xuất phát. Với random, mỗi khe UAV chọn một hướng ngẫu nhiên và bay với tốc độ tối đa.
Với kmeans, UAV bay về tâm cụm user gần nó nhất:

```
Thủ tục KMEANS_DI_CHUYỂN(vị trí user w, vị trí UAV q):
    c ← q                                    // tâm khởi tạo bằng vị trí UAV, nên cụm j luôn ứng với UAV j
    lặp 20 lần:
        gán mỗi user vào tâm gần nhất
        với mỗi cụm j:
            nếu cụm j có user: c_j ← trung bình vị trí user trong cụm
            nếu không: c_j ← vị trí user đang xa tâm của nó nhất
    trả về v_m = (c_m − q_m)/Δt              // mô hình tự co về V_max
```

Đặt UAV ở tâm cụm làm tổng bình phương khoảng cách tới user nhỏ nhất, nên gần như làm độ lợi kênh trung bình lớn nhất;
đây là cách đặt vị trí kinh điển trong các bài báo về UAV làm trạm gốc. Bước xử lý cụm rỗng được thêm sau khi nhóm thấy
trên animation có UAV đứng yên ở góc suốt cả chu kỳ vì không có user nào gần nó.

### 5.5. Heuristic cải tiến `calib-ifair`

`calib-ifair` là một heuristic: nó tìm nhanh một nghiệm đủ tốt cho bài toán ở mục 4.10 (mỗi khe vài mili giây) nhưng
không đảm bảo nghiệm tối ưu, vì bài toán không lồi và có biến nguyên. Nhóm cải tiến từ các heuristic có sẵn (k-means,
max-min) dựa trên hai điều các phép đo ở chương 6 cho thấy mà các baseline bỏ qua: nhiễu đồng kênh làm thay đổi user nào
thật sự yếu, và việc chia băng thông chỉ có tác dụng khi áp ở tầng MAC. Heuristic gồm hai phần.

Phần chia băng `ifair` tính SINR thật của từng user (có nhiễu từ mọi UAV đang phục vụ), đổi ra hiệu suất phổ dự đoán
theo đường cong LTE, rồi chia b_k ∝ w_k / ŜE_k, với w_k là trọng số nhóm của user (1, 2, 4 cho normal, important,
critical) và sàn 0.05 bit/s/Hz để user gần như mất sóng không hút hết băng. Khi mọi user cùng nhóm, cách chia này làm
tốc độ các user trong một UAV bằng nhau; khi có nhóm, user critical nhận tốc độ gấp 4 lần user normal cùng UAV (khi ŜE của các user không thấp hơn sàn). So với maxmin của baseline (dùng SNR không nhiễu và Shannon không trần), `ifair` biết user nào đang chịu
nhiễu và không phí băng cho user đã chạm trần LTE. Trọng số b_k được áp ở tầng MAC qua scheduler WPF.

Phần di chuyển `calib` có hai pha. Khi UAV còn cách tâm cụm k-means hơn một bước bay, nó bay thẳng về tâm như kmeans.
Khi đã tới nơi, mỗi khe nó thử đứng yên và 8 hướng với hai cỡ bước, giữ nước đi làm tăng tiện ích U ở mục 4.11 nhiều
nhất; các UAV được xét lần lượt. Trong pha tìm kiếm này (không áp cho pha bay về tâm cụm), nước đi làm giảm số UAV có user bị loại: khi chưa có ràng buộc này, tìm kiếm cục bộ
hay "tắt" một UAV để giảm nhiễu tức thời và rơi vào nghiệm kém.

```
Thủ tục CALIB_DI_CHUYỂN(w, q):
    c ← KMEANS(w, q)
    với mỗi UAV j:
        nếu ‖c_j − q_j‖ > V_max·Δt: q_j ← q_j + bước về phía c_j; tiếp tục
        tốt_nhất ← U(q); số_UAV_có_user ← N(q)
        với mỗi nước đi d trong {8 hướng} × {V_max·Δt, V_max·Δt/4}:
            q' ← q với q'_j = q_j + d
            nếu N(q') ≥ số_UAV_có_user và U(q') > tốt_nhất: ghi nhận d
        q_j ← q_j + nước đi tốt nhất (hoặc đứng yên)
    trả về (q − q_cũ)/Δt
```

Ở đây U là Σ w_k log(r̂_k + r_0), nên UAV tự kéo về phía nơi có nhiều user critical. Mỗi khe tốn O(M·17·M·K) phép
tính, đo được 5.5 ms với 3 UAV, 20 user và 13.6 ms với 8 UAV, 60 user.

Để biết phần nào mang lại cải thiện, nhóm chạy thêm bốn bản so sánh, cả bốn đều cùng mục tiêu Σ w log r hoặc là trường
hợp riêng của nó:

| Bản | Khác `calib-ifair` ở đâu | Trả lời câu hỏi |
|---|---|---|
| `kmeans-ifair` | Không tinh chỉnh vị trí | Khối di chuyển đóng góp bao nhiêu |
| `calib-equal` | Chia đều băng | Khối chia băng đóng góp bao nhiêu |
| `calib-ifair-noclass` | Mọi w_k = 1 (bỏ qua nhóm) | Trọng số nhóm đổi được gì, mất gì |
| `calib-ifair-shannon` | Tính tốc độ bằng Shannon, không trần | Dùng đường cong LTE thay Shannon có ích không |

### 5.6. Tính độ trễ FIFO

```
Thủ tục ĐỘ_TRỄ_FIFO(hàng đợi Q, lưu lượng A, khả năng phục vụ C, bộ đệm B_max, lịch sử đến H):
    chia khe thành n_s bước nhỏ
    với mỗi bước i:
        phục_vụ_i ← min(Q + A/n_s, C/n_s)
        Q ← Q + A/n_s − phục_vụ_i
        bỏ_i ← max(Q − B_max, 0);  Q ← Q − bỏ_i
        đến_i ← A/n_s − bỏ_i
    với mỗi user:
        nối đường đến tích lũy vào H
        với mỗi bước có phục vụ: lấy bit ở giữa phần được phục vụ,
            tìm thời điểm nó đến bằng nội suy ngược trên H,
            cộng (thời điểm phục vụ − thời điểm đến) × lượng phục vụ vào tổng độ trễ
        bỏ phần lịch sử đã phục vụ hết
    trả về tổng độ trễ của từng user
```

Hàm được kiểm tra bằng một trường hợp giải tay: lưu lượng đến 2 bit/s, phục vụ 1 bit/s trong một khe rồi ngừng đến.
Độ trễ trung bình đúng bằng 0.25 s ở khe đầu và 0.75 s ở khe sau, sai số dưới 0.1%.

### 5.7. Kịch bản NS-3

Bảng dưới cho thấy từng thành phần của mô hình được dựng lại trong NS-3 ra sao (chế độ LTE).

| Mô hình | NS-3 |
|---|---|
| UAV m | Nút eNB dùng WaypointMobilityModel, điểm mốc ở mỗi đầu khe |
| User k | Nút UE |
| Kênh Al-Hourani | Lớp `AlHouraniPropagationLossModel` do nhóm viết, cùng công thức |
| B = 10 MHz, cùng tần số | 50 resource block, mọi eNB cùng tần số (có tùy chọn tần số riêng) |
| P_max = 1 W, N₀ | Công suất phát 30 dBm, hệ số nhiễu 5 dB |
| Liên kết | Attach ở khe đầu; khi kế hoạch đổi UAV thì handover X2 (tắt handover tự động) |
| Lưu lượng | Một luồng UDP đường xuống từ remote host cho mỗi UE, tốc độ đổi đúng đầu khe |
| Chia băng thông | Scheduler PF, RR hoặc WPF (trọng số bằng b_k) |
| Bộ đệm | RLC UM 1 MiB |

Mạng IP đầy đủ gồm remote host, đường lõi 10 Gb/s trễ 1 ms, PGW, EPC, eNB và UE. Mỗi gói UDP mang 1200 byte dữ liệu
kèm số thứ tự và thời điểm gửi để tính độ trễ từng gói. Cuối mỗi khe, kịch bản ghi lại số gói gửi, số gói nhận, số byte
nhận, tổng độ trễ và cell mà UE đang thực sự gắn vào, rồi đặt lại bộ đếm. Có thể bật trace PHY/MAC để lấy SINR, MCS,
tỷ lệ lỗi khối và số lần truyền lại.

Ở chế độ liên kết lý tưởng, toàn bộ LTE được bỏ đi. Remote host nối với mỗi UE bằng một liên kết điểm-điểm riêng không
có trễ truyền. Đầu mỗi khe, tốc độ liên kết được đặt bằng tốc độ phục vụ lý thuyết của user đó, nhân thêm
(1200 + 30)/1200 để bù phần header UDP/IP/PPP. Hàng đợi DropTail chứa đúng 1 MiB dữ liệu, và hàng đợi mặc định của
lớp traffic-control được gỡ bỏ để chỉ còn một hàng đợi như trong mô hình.

```
Lưu đồ phát lại một kế hoạch:
đọc uavs.csv, users.csv → dựng EPC, eNB, UE, remote host → đặt điểm mốc → attach
→ với mỗi khe: đầu khe đặt tốc độ UDP, handover nếu đổi UAV, đặt trọng số WPF;
               cuối khe ghi số đo và đặt lại bộ đếm
→ ghi ns3_slots.csv, flowmon.xml
```

### 5.8. Scheduler Weighted Proportional Fair

Scheduler PF của LTE chọn UE cho mỗi nhóm resource block dựa trên tỷ số giữa tốc độ tức thời và tốc độ trung bình. Nhóm
nhân thêm một trọng số:

$$\text{chỉ số}_k = w_k \cdot \frac{R_k^{\text{tức thời}}}{\bar R_k},\qquad w_k = b_k,$$

nhờ đó về lâu dài phần tài nguyên của mỗi UE tỷ lệ với b_k. Scheduler được làm bằng cách sao scheduler PF của NS-3 3.47
và sửa một dòng logic; HARQ, CQI và đường lên giữ nguyên. Vì định danh RNTI của UE thay đổi sau handover, kịch bản đặt
lại trọng số hai lần mỗi khe. Khi các trọng số bằng nhau, số đo trùng từng byte với PF gốc. Với hai UE đặt cùng chỗ,
trọng số 0.8 và 0.2, mạng bão hòa, throughput đo được là 27.3 và 6.9 Mbps, tỷ lệ 3.93 so với 4 mong đợi.

### 5.9. Trạm điều khiển thời gian thực: dashboard web và Gazebo

Phần này cho phép quan sát và can thiệp vào kịch bản trong lúc nó chạy, rồi đo kết quả bằng NS-3 ngay trên web. Giao diện
được thiết kế theo phong cách trạm điều khiển mặt đất (tham khảo giao diện GCS của dự án UAV quan trắc không khí của
nhóm): nền sáng, viền mảnh, số liệu font đơn cách để không nhảy chữ khi cập nhật, trạng thái thể hiện bằng pill và badge
có cả chữ lẫn màu.

```
Trình duyệt (dashboard)  ◄── WebSocket (JSON) ──►  Server (asyncio)
  vẽ 60 Hz, nội suy             lái tay, bay tới,          │ mỗi khe 0.25 s
  bản đồ, chỉ số, biểu đồ       đổi thuật toán, tốc độ,    ▼
  tham số, đo NS-3              tham số, đo NS-3      thuật toán → quyết định → mô hình
                                                       (Shannon và LTE dự đoán)
                                                            │ gz-transport, 20 Hz    │ đủ khe
                                                            ▼                        ▼
                                                     Gazebo (hiển thị)        NS-3 (luồng riêng)
```

Mô hình chạy đúng thời gian thực với khe 0.25 s và có thể tăng tốc 0.5× đến 4×. Phiên bản đầu dùng khe 1 s chạy nhanh
gấp đôi, nên UAV nhảy từng bước 20 m; nay trình duyệt vẽ lại 60 lần mỗi giây và nội suy vị trí giữa hai khe, còn server
gửi vị trí nội suy sang Gazebo 20 lần mỗi giây, nên chuyển động liền mạch ở cả hai nơi.

Giao diện gồm ba cột. Cột trái là danh sách UAV (vị trí, tốc độ, số user, trạng thái tự động, lái tay hoặc đang bay
tới), khối lái tay (phím W A S D, phím mũi tên hoặc nút trên màn hình, thanh tốc độ) và khối tham số kịch bản. Cột giữa
là bản đồ: UAV, user tô theo UAV phục vụ hoặc theo SINR, đường liên kết, đường bay tới đích, tùy chọn nền bản đồ SINR
tính trên lưới 48 × 48; di chuột lên user để xem SINR và tốc độ, nhấp lên bản đồ để UAV đang chọn bay tới điểm đó rồi
dừng. Bên dưới là ba biểu đồ theo thời gian. Cột phải đặt tốc độ theo Shannon và tốc độ LTE dự đoán cạnh nhau, khối
"Đo bằng NS-3", bảng nhóm user (số user, min tốc độ LTE dự đoán và tỷ lệ đạt QoS của từng nhóm) và bảng user xếp
critical trước, trong mỗi nhóm user yếu nhất lên đầu. Trên bản đồ, nhóm user được phân biệt bằng hình dạng: normal là
hình tròn, important hình vuông, critical hình thoi; màu vẫn là màu UAV phục vụ. Dải chỉ số trên cùng luôn hiện tổng rate, min rate, coverage, throughput,
độ trễ, mất gói và công suất bay.

Người dùng đổi được số UAV (1–8), số user (1–60), độ cao, công suất phát, lưu lượng, vận tốc tối đa, tốc độ đi bộ của
user, seed, môi trường, phân bố user, bật tắt nhiễu, và tỷ lệ user important, critical (mặc định 25% và 15%). Bấm "Áp dụng" thì kịch bản dựng lại từ khe 0; giá trị ngoài
khoảng cho phép bị server từ chối. Gazebo cập nhật ngay mà không phải khởi động lại, vì world được dựng sẵn một bể 8 UAV
và 60 người; model chưa dùng được giấu dưới mặt đất.

Khối "Đo bằng NS-3" cho chọn thời lượng ghi, loại liên kết (lý tưởng hoặc LTE) và scheduler (WPF, PF, RR). Bấm "Ghi &
đo" thì server đặt lại kịch bản về khe 0, ghi đủ số khe (người dùng vẫn lái tay được trong lúc ghi), chạy NS-3 trong một
luồng riêng để mô phỏng không bị dừng, rồi trả bảng mô hình so với NS-3 về web. Một phép thử 10 giây với liên kết lý
tưởng cho throughput 30.0 Mbps theo mô hình và 29.99 Mbps theo NS-3, chạy hết 0.9 giây.

Khi một UAV được lái tay, vận tốc người dùng nhập (hoặc vận tốc hướng tới điểm đến) thay cho vận tốc thuật toán tính; mô
hình vẫn co về vận tốc tối đa và giữ UAV trong vùng. Liên kết, băng thông và công suất vẫn do thuật toán quyết định, nên
khi UAV lái tay bay xa, user của nó tự chuyển sang UAV có kênh tốt hơn. Server có các cơ chế an toàn: thả phím thì UAV
đứng yên, mất kết nối với mọi trình duyệt thì UAV lái tay dừng, lệnh hay tham số sai chỉ bị từ chối, server chỉ nhận
kết nối từ máy cục bộ.

Gazebo dùng bãi thảm họa có sẵn trong dự án `multi_uav` của nhóm làm nền và vẽ đúng kịch bản của mô hình. Tỷ lệ là 1 m
trong Gazebo ứng với 10 m trong mô hình. Gazebo chỉ hiển thị, các model không chịu trọng lực và không va chạm.

Ở tỷ lệ 1:10 một UAV thật (0.5 m) và một người (1.7 m) gần như không nhìn thấy, nên hình vẽ được phóng to (vị trí vẫn
đúng tỷ lệ). UAV là một quadrotor dựng từ khối cơ bản, sải khoảng 7 m Gazebo, thân và tay mang màu của UAV trên
dashboard, kèm một tia cùng màu chiếu thẳng xuống đất để thấy UAV đang đứng trên điểm nào. User là hình người đơn giản
cao khoảng 3.6 m, áo mang màu của UAV đang phục vụ, đỏ khi không được phục vụ. Gazebo làm mất lệnh đổi màu
(`material_color`) khi đang nhận lệnh đặt vị trí, nên áo không đổi màu mà hình người được đổi: mỗi màu có sẵn một bể
hình người, hình đúng màu được đặt vào chỗ user, hình cũ cất xuống dưới đất. User important có thêm vòng vàng dưới
chân, user critical vòng đỏ, user normal không có vòng. Dùng hình khối đơn giản thay cho mô hình
người chi tiết của bãi cũng giúp Gazebo nhẹ hơn nhiều (tốc độ mô phỏng tăng từ khoảng 5% lên 70–95% thời gian thực).
Camera mặc định nhìn chéo từ phía nam, thấy trọn vùng 1000 × 1000 m.

### 5.10. Cấu hình thử nghiệm

Các thí nghiệm chạy trên máy 12 nhân, 19 GB RAM, GPU RTX 3050 Laptop (chỉ dùng cho Gazebo). NS-3 chạy 10 run song song.
Mô hình dùng cấu hình mặc định ở mục 4.3 với 3 seed; NS-3 dùng 3 đến 5 seed, mỗi run 60 khe, thời gian khởi động
0.5 s, scheduler mặc định là PF.

### 5.11. Kiểm thử

Dự án có 42 test tự động. Các test kiểm tra công thức kênh và năng lượng với giá trị đã biết, công thức Shannon và LTE,
việc từ chối quyết định sai, tính hợp lệ và khả năng tái lập của mọi baseline, việc maxmin cho tốc độ bằng nhau khi
không có nhiễu, môi trường Gymnasium qua bộ kiểm tra chuẩn, và hàng đợi. Các test có chạy NS-3 kiểm tra rằng ở tải 30%
mạng nhận đủ lưu lượng (sai số 10%), mất gói dưới 2% và UE gắn đúng cell 100%; trace hợp lệ; scheduler WPF chia tài
nguyên theo tỷ lệ 4:1; và NS-3 lý tưởng khớp mô hình hàng đợi. Phần thời gian thực được kiểm tra rằng UAV lái tay đi
đúng vận tốc lệnh, phiên ghi ra đúng định dạng kế hoạch và world Gazebo đi theo kịch bản của mô hình.

---

## 6. Phân tích và đánh giá hiệu năng

Trong chương này, số liệu của mô hình là số *tính*, số liệu NS-3 là số *đo*. Vì mỗi seed sinh ra một bản đồ user khác
nhau nên độ lệch chuẩn giữa các seed khá lớn; khi so sánh hai thuật toán, nhóm so theo cặp trên cùng seed và ghi kèm số
seed mà thuật toán thứ nhất tốt hơn.

### 6.1. Các kịch bản thí nghiệm

| # | Kịch bản | Quy mô | Câu hỏi |
|---|---|---|---|
| E1 | Mô hình, 6 thuật toán | 6 × 3 seed × 200 khe | Theo lý thuyết, thuật toán nào tốt? |
| E2 | Ma trận NS-3 LTE | 3 thuật toán × 6 mức tải × 5 seed = 90 run | Đo ở mức gói tin thì sao, mạng chịu tải tới đâu? |
| E3 | Tách nhiễu, có trace | 3 cấu hình × 3 seed | Vì sao LTE chỉ đạt khoảng 70%? |
| E4 | Một liên kết, hiệu chỉnh, phân rã | 15 mức công suất; 24 run kiểm chứng | Nguyên nhân chênh lệch là gì? |
| E5 | Lưu lượng và hàng đợi | 3 × 7 mức lưu lượng × 3 seed = 63 run | Độ trễ và mất gói lý thuyết so với LTE |
| E6 | Scheduler WPF | 2 × 7 × 3 = 42 run | Chia băng thông ở tầng MAC có tác dụng không? |
| E7 | Ba tầng | 63 + 42 = 105 run | Mô hình có đúng ở mức gói tin không? |
| E8 | Thời gian chạy | | Chi phí tính toán |
| E9 | Điều khiển thời gian thực | 14 khe, 23 model | Dashboard và Gazebo có đồng bộ không? |
| E10 | Thuật toán đề xuất | 3 thuật toán × 7 × 3 = 63 run LTE + 63 run lý tưởng | Thiết kế dựa trên số đo NS-3 có tốt hơn không? |
| E11 | Ba nhóm user | 3 thuật toán × 7 × 3 = 63 run LTE (baseline không biết nhóm dùng lại E5, E6, E10) | Ưu tiên được user critical không, hơn max-min có trọng số không, giá phải trả là gì, LTE hay Shannon? |

### 6.2. Kết quả của mô hình (E1)

Cấu hình mặc định, Shannon, 200 khe, trung bình 3 seed:

| Thuật toán | Sum rate (Mbps) | Min rate (Mbps) | Jain | Coverage | Năng lượng (J/khe) | Hiệu suất (kbit/J) |
|---|---|---|---|---|---|---|
| hover-equal | 87 ± 38 | 0.71 ± 0.06 | 0.47 | 77% | 505.5 | 173 |
| hover-maxmin | 76 ± 30 | 0.84 ± 0.11 | 0.51 | 80% | 505.5 | 151 |
| kmeans-equal | 145 ± 22 | 1.85 ± 0.52 | 0.71 | 99.4% | 507.8 | 285 |
| kmeans-maxmin | 143 ± 22 | 1.90 ± 0.55 | 0.72 | 99.6% | 507.8 | 281 |
| random-equal | 97 ± 33 | 1.01 ± 0.24 | 0.64 | 89% | 534.9 | 181 |
| random-maxmin | 89 ± 31 | 1.25 ± 0.29 | 0.69 | 93% | 534.9 | 166 |

Yếu tố quyết định là di chuyển có định hướng. So với đứng yên, kmeans tăng sum rate khoảng 1.7 lần, min rate khoảng 2.6
lần và coverage từ 77% lên khoảng 99%, trong khi năng lượng gần như không đổi vì UAV chỉ bay khoảng 15 khe đầu rồi
hover. Chia băng theo maxmin đổi một ít sum rate lấy min rate và chỉ số Jain cao hơn, đúng với đánh đổi quen thuộc. Bay
ngẫu nhiên tốn năng lượng nhất mà vẫn kém kmeans nhiều. Một quan sát đáng chú ý là thêm UAV không phải lúc nào cũng tốt
hơn khi các UAV dùng chung băng tần: sau khi sửa lỗi cụm rỗng, UAV thứ ba bay vào phục vụ nhưng gây nhiễu cho UAV bên
cạnh, và sum rate của kmeans giảm từ 169 xuống 145 Mbps.

### 6.3. Đo bằng NS-3 LTE (E2)

Ba thuật toán được chạy với sáu mức tải từ 0.5 tới 1.0 (tải là hệ số nhân với tốc độ kế hoạch tính theo 3GPP 36.942),
năm seed, mỗi run 60 khe. Cả 90 run đều thành công, mọi handover đều hoàn tất và UE luôn gắn đúng cell theo kế hoạch.

| Thuật toán | Tải | Gửi (Mbps) | NS-3 (Mbps) | Chuyển được | Độ trễ | Mất gói | Min (Mbps) | Jain |
|---|---|---|---|---|---|---|---|---|
| hover-equal | 0.5 | 22.6 | 22.6 | 100% | 11 ms | 0.03% | 0.23 | 0.52 |
| | 0.6 | 27.2 | 27.0 | 99.6% | 130 ms | 0.5% | 0.25 | 0.51 |
| | 0.7 | 31.7 | 30.0 | 94% | 1.5 s | 5.8% | 0.26 | 0.50 |
| | 1.0 | 45.3 | 31.6 | 69% | 4.5 s | 31% | 0.26 | 0.49 |
| kmeans-equal | 0.5 | 37.1 | 37.1 | 100% | 9 ms | 0.02% | 0.48 | 0.71 |
| | 0.6 | 44.6 | 44.4 | 99.6% | 80 ms | 0.4% | 0.55 | 0.70 |
| | 0.7 | 52.0 | 50.0 | 96% | 0.8 s | 4.1% | 0.57 | 0.69 |
| | 1.0 | 74.3 | 52.8 | 71% | 2.6 s | 29% | 0.57 | 0.68 |
| kmeans-maxmin | 0.5 | 36.5 | 36.5 | 99.9% | 20 ms | 0.12% | 0.51 | 0.72 |
| | 1.0 | 73.0 | 52.7 | 72% | 2.5 s | 28% | 0.57 | 0.68 |

So sánh theo cặp trên cùng seed (trong ngoặc là số seed mà thuật toán đứng trước cao hơn):

| So sánh | Tải | Throughput | Min | Jain | Độ trễ | Mất gói |
|---|---|---|---|---|---|---|
| kmeans-equal / hover-equal | 0.5 | 1.95× (4/5) | 2.20× (5/5) | 1.47× (5/5) | 0.83× | 1.20× |
| | 1.0 | 2.06× (4/5) | 2.24× (5/5) | 1.52× (5/5) | 0.67× | 0.94× |
| kmeans-maxmin / kmeans-equal | 0.5 | 0.98× | 1.06× (4/5) | 1.01× | 2.26× (5/5) | 5.5× (5/5) |
| | 1.0 | 1.00× | 1.00× | 1.00× | 0.96× | 0.96× |

LTE chỉ chuyển được khoảng 70% so với công thức 3GPP: throughput bão hòa ở khoảng 32 Mbps với hover và 53 Mbps với
kmeans. Đường độ trễ có một điểm gãy rõ giữa tải 0.6 và 0.7, đúng dạng của một hệ thống hàng đợi khi tải tiến gần năng
lực phục vụ. Ở tải 0.5, mạng chuyển được gần như toàn bộ với độ trễ 9–20 ms; từ 0.7 trở đi độ trễ lên tới hàng giây.
Vì vậy khi lập kế hoạch nên chỉ gửi khoảng 50–60% tốc độ tính được.

NS-3 xác nhận lợi ích của việc di chuyển: kmeans hơn hover khoảng 2.2 lần về min throughput và khoảng 1.5 lần về chỉ số
Jain ở cả năm seed. Riêng throughput tổng, kmeans chỉ thắng ở bốn trên năm seed; ở seed còn lại hover hơn khoảng 10%,
khớp với nhận xét về nhiễu ở mục 6.2. Ngược lại, kết luận về maxmin không còn đúng: khi chỉ chia ở tầng ứng dụng, maxmin
làm độ trễ tăng 2.3 lần và mất gói tăng 5.5 lần ở tải thấp, còn ở tải cao thì cho kết quả trùng với equal vì scheduler
PF của LTE chia lại tài nguyên theo cách riêng.

### 6.4. Tìm nguyên nhân chênh lệch (E3, E4)

Để biết vì sao LTE chỉ đạt khoảng 70%, nhóm chạy kmeans-equal ở tải 1.0 với ba cấu hình: A gồm 3 UAV dùng chung tần số,
B gồm 3 UAV mỗi UAV một tần số riêng, và C chỉ có 1 UAV.

| | A. chung tần số | B. tần số riêng | C. 1 UAV |
|---|---|---|---|
| Mô hình 3GPP 36.942 (Mbps) | 76.3 | 103.9 | 43.4 |
| NS-3 dữ liệu UDP (Mbps) | 57.1 | 80.8 | 33.7 |
| NS-3 / mô hình | 0.75 | 0.78 | 0.78 |
| SINR p10 / trung vị / p90 (dB) | 5.7 / 19.7 / 29.0 | 28.3 / 42.0 / 48.8 | 23.0 / 38.7 / 48.6 |
| MCS trung bình | 21.7 | 28.0 | 27.8 |
| Lỗi khối lần đầu | 0.06% | 0.02% | 0.05% |
| Hiệu suất phổ mỗi cell (bit/s/Hz) | 2.19 | 3.16 | 3.46 |
| Min throughput (Mbps) | 0.65 | 2.91 | 1.57 |

Khi không có nhiễu (B và C), gần như mọi khối truyền đều ở MCS 28, mức cao nhất, và hiệu suất phổ chạm khoảng
3.5 bit/s/Hz mỗi cell. Tỷ lệ lỗi khối dưới 0.1% nên HARQ không phải nguyên nhân. Nhiễu đồng kênh làm SINR trung vị giảm
khoảng 22 dB, throughput giảm khoảng 30% và min throughput giảm khoảng 4.5 lần, nhưng tỷ lệ NS-3/mô hình ở A chỉ thấp
hơn B ba điểm phần trăm, tức mô hình xử lý nhiễu khá đúng.

Nhóm đặt bốn giả thuyết: (a) kênh được cài khác nhau ở hai bên, (b) mô hình tính nhiễu sai, (c) do HARQ và lỗi truyền,
(d) cách LTE đổi SINR ra tốc độ khác với công thức. Để kiểm tra, nhóm làm thí nghiệm một liên kết: một UAV, một user cách
100 m, không nhiễu, quét công suất phát từ −40 đến 30 dBm.

| SINR NS-3 (dB) | MCS | Hiệu suất phổ NS-3 | Theo 36.942 | Tỷ lệ |
|---|---|---|---|---|
| −9.1 | 0 | 0 | 0.10 | 0 |
| 0.9 | 6 | 0.50 | 0.69 | 0.72 |
| 10.9 | 16 | 1.47 | 2.23 | 0.66 |
| 20.9 | 28 | 3.51 | 4.16 | 0.84 |
| 25.9 … 45.9 | 28 | 3.51 | 4.40 | 0.80 |

SINR do NS-3 đo trùng với SNR của mô hình tới 0.1 dB, nên giả thuyết (a) bị loại. Khớp đường cong
SE = min(α log₂(1+SINR), trần) cho α = 0.401 và trần 3.514 bit/s/Hz. Khi thay hai hằng số này vào mô hình và tính lại
cho đúng các run A, B, C, tỷ lệ NS-3/mô hình thành 1.02, 0.99 và 1.00, nghĩa là giả thuyết (d) giải thích toàn bộ khoảng
chênh. So SINR theo từng khe và từng user, sai lệch trung vị không quá 0.22 dB, sai lệch tuyệt đối trung bình không quá
0.42 dB, nên giả thuyết (b) cũng bị loại; giả thuyết (c) bị loại vì tỷ lệ lỗi khối quá thấp.

### 6.5. Phân rã khoảng cách từ Shannon tới NS-3

Bảng dưới tính lại throughput cho cùng các run, mỗi bậc thêm vào một đặc điểm của hệ thống thật (tải 1.0, Mbps):

| Bậc | A | B | C | hover-equal | kmeans-equal | kmeans-maxmin |
|---|---|---|---|---|---|---|
| ① Shannon (như bài báo) | 146.9 | 321.2 | 121.7 | 80.3 | 132.6 | 129.9 |
| ② 3GPP 36.942 | 76.3 | 103.9 | 43.4 | 45.3 | 74.3 | 73.0 |
| ③ thêm trần LTE 3.51 | 66.2 | 83.2 | 35.1 | 42.1 | 68.1 | 67.2 |
| ④ thêm độ dốc LTE 0.40 | 56.0 | 81.9 | 33.6 | 31.5 | 52.1 | 51.1 |
| ⑥ NS-3 đo được | 57.0 | 80.8 | 33.7 | 31.6 | 52.8 | 52.7 |
| ⑥ / ① | 0.39 | 0.25 | 0.28 | 0.39 | 0.40 | 0.41 |
| ⑥ / ④ | 1.02 | 0.99 | 1.00 | 1.00 | 1.01 | 1.03 |

Từ ① sang ② mất 44–68%. Shannon là giới hạn thông tin, giả định mã dài vô hạn, điều chế không giới hạn và không có
overhead, nên không có trần; công thức 3GPP nhân thêm hệ số 0.6 và chặn ở 4.4 bit/s/Hz. Từ ② sang ③ mất thêm 7–20% vì
trần thật của LTE 10 MHz SISO thấp hơn: ở MCS 28, bảng TBS trong 3GPP TS 36.213 cho 36696 bit mỗi ms với 50 resource
block, nhưng scheduler PF của NS-3 chia resource block theo nhóm 3 nên chỉ dùng 48 trên 50, cho 35160 bit mỗi ms, tức
3.516 bit/s/Hz, trùng với trần đo được. Từ ③ sang ④ mất 1–25% vì LTE chỉ có 29 mức MCS và 16 mức CQI, và cơ chế thích
ứng điều chế của NS-3 làm tròn MCS xuống hai lần (từ MCS sang CQI rồi từ CQI về MCS); tỷ lệ lỗi khối vì thế gần như bằng
0 dù ngưỡng cho phép là 10%. Phần còn lại, khoảng ±4%, đến từ scheduler, thời gian lấp đầy hàng đợi khi đổi tốc độ, nội
suy vị trí trong khe và header giao thức (2.5–3%).

Như vậy, throughput NS-3 LTE chỉ bằng 25–40% giá trị Shannon, và khoảng cách này được giải thích hoàn toàn bằng ba đặc
điểm trên. Khi đưa cả ba vào, mô hình dự đoán NS-3 với sai số khoảng ±3% cho mỗi cấu hình và ±6% cho từng run, trên 24
run trong đó 15 run nằm ngoài tập dùng để khớp hằng số.

### 6.6. Độ trễ và mất gói (E5)

Ở thí nghiệm này mỗi user nhận lưu lượng tốc độ không đổi từ 0.5 đến 4 Mbps, ba thuật toán, ba seed, 60 khe, scheduler
PF, bộ đệm 1 MiB. Lý thuyết dùng công thức Shannon, độ trễ FIFO và định nghĩa mất gói ở mục 4.8. Kết quả của
kmeans-equal:

| Mbps/user | Throughput lý thuyết / NS-3 (Mbps) | Độ trễ lý thuyết / NS-3 (ms) | Mất gói lý thuyết / NS-3 |
|---|---|---|---|
| 0.5 | 10.0 / 10.0 | 2 / 7 | 0% / 0% |
| 1 | 20.0 / 19.6 | 17 / 152 | 0% / 2.2% |
| 1.5 | 30.0 / 27.7 | 137 / 769 | 0.1% / 7.5% |
| 2 | 39.5 / 33.9 | 279 / 1397 | 1.3% / 15.2% |
| 3 | 57.0 / 43.3 | 558 / 1984 | 5.0% / 27.8% |
| 4 | 71.6 / 49.9 | 749 / 2173 | 10.5% / 37.6% |

Lý thuyết theo kiểu bài báo dự đoán nghẽn muộn hơn, độ trễ thấp hơn 3–9 lần và mất gói thấp hơn nhiều, dù thứ hạng
(kmeans tốt hơn hover) vẫn đúng ở mọi mức. Nhóm lần lượt thêm từng đặc điểm của LTE vào lý thuyết rồi so với cả 63 run:

| Lý thuyết | Sai số throughput | Sai số mất gói | Độ trễ, lệch trung vị |
|---|---|---|---|
| Như bài báo (Shannon, chia tĩnh, nhiễu tối đa) | 27.3% | 15.1 điểm % | ×3.7 |
| Thêm cách đổi SINR ra tốc độ của LTE | 3.5% | 2.7 điểm % | ×1.21 |
| Thêm chia băng linh hoạt | 4.9% | 3.6 điểm % | ×1.23 |
| Thêm nhiễu theo tải | 4.4% | 3.2 điểm % | ×1.16 |
| Thêm cả ba | 5.9% | 4.2 điểm % | ×1.26 |

Cách đổi SINR ra tốc độ của LTE giải thích phần lớn chênh lệch; ở tải từ 2 Mbps/user trở lên, mất gói chỉ còn lệch
trung bình 0.2 điểm phần trăm. Nhiễu theo tải giải thích vùng tải nhẹ: với hover ở 0.5 Mbps/user, nếu coi nhiễu luôn tối
đa thì lý thuyết dự đoán độ trễ 2 s và mất 9.3%, tính nhiễu theo tải thì còn 8 ms và 0%, trong khi NS-3 đo được 10 ms và
0%. Nguyên nhân là eNB chỉ phát trên các resource block được cấp, nên khi tải nhẹ nhiễu thực tế thấp hơn nhiều. Chia băng
linh hoạt giải thích vùng tải trung bình: với kmeans ở 1 Mbps/user, độ trễ giảm từ 614 xuống 263 ms, thêm nhiễu theo tải
thì còn 131 ms, gần với 152 ms đo được. Hai phần nhóm chưa giải thích hết là độ trễ ở tải cao vẫn lệch khoảng 13% (trung
vị), và độ trễ nền khi tải rất nhẹ (NS-3 6–14 ms so với lý thuyết 1.5–9 ms), nhiều khả năng do độ trễ xử lý của LTE (TTI
1 ms, chu kỳ lập lịch, RLC/PDCP) và đường lõi 1 ms trong kịch bản.

### 6.7. Chia băng thông ở tầng MAC (E6)

Thí nghiệm này chạy hover-maxmin và kmeans-maxmin với scheduler WPF, rồi so theo cặp với hai thuật toán equal tương ứng
(chạy với PF; khi các trọng số bằng nhau thì WPF và PF như nhau).

| | Mbps/user | Min throughput equal → maxmin | Throughput tổng | Mất gói | Độ trễ |
|---|---|---|---|---|---|
| hover | 1 | 0.58 → 0.70 (+21%, 3/3 seed) | 18.5 → 19.0 | 7.4% → 5.1% | 1267 → 883 ms |
| hover | 2 | 0.30 → 0.36 (+20%, 3/3) | 22.6 → 22.4 | 43.4% → 43.9% | 4663 → 5142 ms |
| hover | 4 | 0.26 → 0.30 (+15%, 3/3) | 27.8 → 26.5 | 65.2% → 66.9% | 5491 → 5851 ms |
| kmeans | 1–4 | thay đổi dưới 2% | gần như không đổi | gần như không đổi | gần như không đổi |

Lý thuyết dự đoán maxmin tăng min throughput khoảng 18%; NS-3 với WPF cho 15–21% ở cả ba seed. Như vậy chia băng thông
có tác dụng, nhưng phải áp ở tầng MAC; nếu chỉ áp ở tầng ứng dụng thì scheduler của LTE xóa mất tác dụng đó (mục 6.3).
Hiệu quả cũng phụ thuộc mức chênh lệch kênh giữa các user: với hover, user trong một cell có SINR rất khác nhau nên
maxmin có tác dụng rõ; với kmeans, UAV đã ở giữa cụm, SINR các user gần nhau và maxmin gần như không khác equal. Ở tải
cao, cái giá phải trả lớn hơn lý thuyết nói: tổng throughput giảm tới 5% thay vì tăng nhẹ.

### 6.8. Kiểm chứng ba tầng (E7)

Cùng 105 run của E5 và E6 được chạy lại với liên kết lý tưởng. Sai số lớn nhất trên từng run giữa lý thuyết và NS-3 lý
tưởng là 0.02% với throughput, 1.0% với độ trễ, 0.014 điểm phần trăm với mất gói và 2.1% với min throughput (dưới 0.8%
khi lưu lượng từ 1 Mbps/user trở lên).

| Thuật toán | Mbps/user | Throughput (Mbps) | Độ trễ (ms) | Mất gói (%) |
|---|---|---|---|---|
| hover-equal | 1 | 18.90 / 18.90 | 1202.5 / 1201.6 | 5.49 / 5.50 |
| | 4 | 47.54 / 47.54 | 2634.0 / 2631.1 | 40.58 / 40.58 |
| kmeans-equal | 1 | 20.00 / 20.00 | 17.3 / 17.5 | 0.00 / 0.00 |
| | 4 | 71.63 / 71.63 | 749.2 / 748.4 | 10.46 / 10.47 |
| kmeans-maxmin | 1 | 20.00 / 20.00 | 7.2 / 7.2 | 0.00 / 0.00 |
| | 4 | 72.29 / 72.29 | 754.0 / 753.1 | 9.64 / 9.64 |

(Mỗi ô ghi lý thuyết / NS-3 lý tưởng, trung bình 3 seed.)

Để đạt mức khớp này, nhóm phải sửa ba chỗ. Thứ nhất, NS-3 tính cả gói còn trong hàng đợi lúc kết thúc là mất, còn lý
thuyết ban đầu thì không, khiến mất gói chênh tới 6 điểm phần trăm. Thứ hai, độ trễ theo định luật Little lệch 1–25% và
được thay bằng độ trễ FIFO. Thứ ba, hàng đợi trong NS-3 đếm cả header 30 byte mỗi gói trong khi mô hình chỉ đếm dữ liệu,
nên kích thước hàng đợi được điều chỉnh cho hai bên chứa cùng 1 MiB dữ liệu.

Kết quả này cho thấy mô hình hàng đợi, đường ống xuất kế hoạch và cách đo đều đúng ở mức gói tin, nên mọi khoảng chênh
giữa lý thuyết và NS-3 LTE ở các mục trước đều do giao thức LTE. Nó cũng làm rõ chuyện maxmin: ở tầng lý tưởng, maxmin
khác equal đúng như lý thuyết (với kmeans ở 1 Mbps/user, độ trễ giảm từ 17.3 xuống 7.2 ms), còn trên LTE với PF thì hai
thuật toán cho số đo giống hệt. Lý thuyết không sai; scheduler PF đã chia lại tài nguyên. Ngoài ra, khi chạy lại NS-3
LTE sau các sửa đổi phía lý thuyết, cả 105 run cho số đo trùng từng chữ số với lần chạy trước.

Hình 13 và 14 (`experiments/results/three_tier_pf.png`, `three_tier_wpf.png`) thể hiện kết quả này. Mỗi hình là một
lưới bốn hàng (throughput, min throughput, độ trễ theo thang log, mất gói) và một cột cho mỗi thuật toán, trục ngang là
lưu lượng mỗi user. Đường xanh dương là lý thuyết, các vòng tròn cam là NS-3 lý tưởng, đường xanh lá có dải mờ là NS-3
LTE kèm độ lệch chuẩn. Ở mọi ô, vòng cam nằm đúng trên đường xanh dương, còn đường xanh lá tách ra.

### 6.9. Thời gian chạy và độ phức tạp (E8)

Thời gian chạy một khe của mô hình (đo trên máy ở mục 5.10):

| Cấu hình | Thời gian mỗi khe |
|---|---|
| hover-equal, 3 UAV, 20 user, không lưu lượng | 0.23 ms |
| kmeans-equal, kmeans-maxmin, như trên | 0.82–0.83 ms |
| hover-equal, có lưu lượng | 2.32 ms |
| kmeans-equal, có lưu lượng | 3.02 ms |
| kmeans, 5 UAV, 50 user | 1.33 ms |
| kmeans, 10 UAV, 100 user | 2.67 ms |

Thời gian tăng gần tuyến tính theo tích M·K, phù hợp với độ phức tạp của kmeans và phép tính nhiễu. Phần độ trễ FIFO
thêm khoảng 2 ms mỗi khe nhưng mô hình vẫn chạy nhanh hơn thời gian thực khoảng 300 lần. Một run NS-3 60 khe mất 110–343
giây (trung vị 254 giây) ở chế độ LTE và 1–14 giây (trung vị 6 giây) ở chế độ lý tưởng. Mô hình nhanh hơn NS-3 LTE ba
đến bốn bậc, đó là lý do nhóm chọn cách cho thuật toán chạy trên mô hình và chỉ dùng NS-3 để đo.

| Thành phần | Thời gian | Bộ nhớ |
|---|---|---|
| Liên kết theo kênh tốt nhất | O(MK) | O(MK) |
| Chia băng equal, maxmin | O(K) | O(K) |
| SINR và tốc độ có nhiễu | O(MK) | O(MK) |
| kmeans, I vòng lặp | O(I·M·K) | O(M + K) |
| Hàng đợi và độ trễ FIFO | O(n_s·K + Σ h_k) | O(Σ h_k) |

Ở đây n_s = 200 là số bước nhỏ trong một khe và h_k là độ dài phần lịch sử hàng đợi còn lại của user k.

### 6.10. Điều khiển thời gian thực (E9)

Khi ra lệnh 30 m/s cho một UAV lái tay, UAV đi đúng 20 m mỗi khe (giới hạn tốc độ) trong khi các UAV khác vẫn theo thuật
toán. Để kiểm tra đồng bộ, nhóm đọc cùng lúc vị trí server gửi cho dashboard và vị trí các model trong Gazebo trong 14
khe, với 3 UAV và 20 user, trong lúc một UAV đang được lái chéo; sai lệch lớn nhất là 0.00 m. Một phiên được ghi rồi
phát lại trong NS-3 lý tưởng cho throughput 19.99 Mbps so với 20 Mbps của mô hình, mất gói 0.012%. Chu kỳ cập nhật là
0.5 s mỗi khe, trong khi mô hình chỉ cần khoảng 3 ms để tính một khe. Server không dừng khi nhận lệnh sai, UAV lái tay tự
dừng khi mất kết nối, và Gazebo tự đóng khi tắt server.

### 6.11. Thuật toán đề xuất đo bằng NS-3 LTE (E10)

Thí nghiệm này chạy khi chưa có nhóm user (mọi w = 1), nên `calib-ifair` ở đây chính là `calib-ifair-noclass` của
mục 6.12. calib-ifair và hai bản tách thành phần được chạy với scheduler WPF trên đúng cấu hình của E5, E6 (3 UAV, 20 user, 60
khe, 7 mức lưu lượng, 3 seed), tổng cộng 63 run NS-3 LTE và 63 run liên kết lý tưởng. Ở tầng lý tưởng, mô hình vẫn khớp
NS-3 (sai số throughput 0.016%, độ trễ 1.2%), nên khác biệt trên LTE là do thuật toán và giao thức. Bảng dưới so với
kmeans-equal trên cùng seed ("×" là tỷ lệ min throughput, trong ngoặc là số seed thắng):

| Mbps/user | kmeans-equal | kmeans-maxmin | kmeans-ifair | calib-equal | calib-ifair (đề xuất) |
|---|---|---|---|---|---|
| Min throughput (Mbps), 1 | 0.84 | 0.85 (×1.01) | 0.92 (×1.11) | 0.90 (×1.09) | 0.95 (×1.16, 3/3) |
| 2 | 0.72 | 0.79 (×1.10) | 1.29 (×1.77) | 0.80 (×1.10) | 1.37 (×1.92, 3/3) |
| 4 | 0.67 | 0.74 (×1.11) | 1.27 (×1.87) | 0.75 (×1.09) | 1.37 (×2.03, 3/3) |
| Throughput tổng (Mbps), 1 | 19.6 | 19.6 | 19.8 | 19.8 | 19.9 |
| 2 | 33.9 | 34.0 | 33.4 | 35.3 | 34.8 |
| 4 | 49.9 | 49.7 | 46.1 | 52.2 | 48.2 |
| Độ trễ (ms), 1 | 152 | 156 | 165 | 57 | 72 |
| 2 | 1397 | 1524 | 2174 | 1152 | 1837 |
| Mất gói (%), 1 | 2.2 | 2.0 | 1.3 | 1.2 | 0.5 |
| 2 | 15.2 | 15.0 | 16.6 | 11.8 | 13.1 |
| 4 | 37.6 | 37.9 | 42.3 | 34.8 | 39.7 |

Khi tải từ 2 Mbps/user trở lên, calib-ifair nâng min throughput gần gấp đôi so với kmeans-equal (×1.92–2.03, cả ba
seed), trong khi maxmin của baseline chỉ được khoảng ×1.10; throughput tổng giữ trong khoảng ±4%. Ở tải vừa (1 Mbps/user)
thuật toán tốt hơn ở mọi chỉ số: min throughput tăng 16%, độ trễ giảm từ 152 xuống 72 ms, mất gói từ 2.2% xuống 0.5%.
Hai bản tách thành phần cho thấy phần lớn cải thiện về công bằng đến từ cách chia băng `ifair`, còn phần di chuyển
`calib` vừa thêm vào min throughput, vừa bù lại phần throughput tổng và mất gói mà `ifair` làm giảm (ở 4 Mbps/user:
kmeans-ifair 46.1 Mbps và mất 42.3%, calib-ifair 48.2 Mbps và 39.7%). Đánh đổi còn lại là độ trễ trung bình ở tải cao
tăng, vì băng thông dồn cho user kênh yếu khiến hàng đợi của user kênh tốt dài hơn.

Khác với maxmin ở mục 6.3, cải thiện này đứng vững trên NS-3 vì thuật toán tính SINR có nhiễu khi chia băng và áp quyết
định ở tầng MAC. Mục 6.12 cho thấy việc dùng đường cong LTE thay cho Shannon gần như không đổi kết quả, nên lợi ích đến từ
hai điểm này và từ cách đặt mục tiêu, không đến từ hằng số hiệu chỉnh.

Hình 15 (`experiments/results/proposed.png`) vẽ bốn chỉ số theo lưu lượng cho cả năm thuật toán; số liệu đầy đủ ở
`experiments/results/proposed.csv`.

### 6.12. Ba nhóm user đo bằng NS-3 LTE (E11)

Cùng cấu hình E10 (3 UAV, 20 user, 60 khe, 7 mức lưu lượng 0.5–4 Mbps/user, 3 seed, WPF), nay mỗi seed có 3 user
critical, 5 important và 12 normal. Nhóm được bốc bằng rng riêng nên vị trí user không đổi: các run cũ của kmeans-equal,
kmeans-maxmin và calib-ifair-noclass dùng lại được, chỉ số từng nhóm được tính lại từ số đo từng user trong
`ns3_slots.csv`. Chạy mới 63 run: calib-ifair (có trọng số), calib-ifair-shannon, và baseline biết nhóm
**kmeans-wmaxmin**. Baseline này giống kmeans-maxmin (bay về tâm cụm, chia băng theo SNR không nhiễu, Shannon) nhưng chia
b_k ∝ w_k / log₂(1+SNR_k), tức max-min có trọng số: có cùng thông tin về nhóm như thuật toán đề xuất, chỉ khác phương
pháp. "Đạt QoS" là tỷ lệ (user, khe) có throughput ≥ min(r_min nhóm, 0.9·λ); độ trễ tính theo từng nhóm.

| Mbps/user | Chỉ số | kmeans-equal | kmeans-maxmin | calib-ifair-noclass | **kmeans-wmaxmin** | calib-ifair-shannon | **calib-ifair** |
|---|---|---|---|---|---|---|---|
| 1 | Critical đạt QoS | 92% | 91% | 96% | 100% | 100% | **100%** |
| 1 | Độ trễ critical (ms) | 208 | 220 | 65 | 5 | 6 | **6** |
| 1 | Min throughput normal (Mbps) | 0.84 | 0.87 | 0.96 | 0.80 | 0.92 | **0.92** |
| 1 | Throughput tổng (Mbps) | 19.6 | 19.6 | 19.9 | 19.5 | 19.8 | **19.8** |
| 1 | Mất gói (%) | 2.2 | 2.0 | 0.5 | 2.4 | 0.8 | **0.8** |
| 2 | Critical đạt QoS | 69% | 69% | 65% | 87% | 98% | **97%** |
| 2 | Min throughput critical (Mbps) | 1.27 | 1.30 | 1.52 | 1.80 | 1.96 | **1.97** |
| 2 | Độ trễ critical (ms) | 1084 | 1328 | 1569 | 252 | 41 | **41** |
| 2 | Min throughput normal (Mbps) | 0.73 | 0.81 | 1.39 | 0.59 | 1.01 | **1.02** |
| 2 | Throughput tổng (Mbps) | 33.9 | 34.0 | 34.8 | 31.8 | 32.5 | **32.4** |
| 4 | Critical đạt QoS | 69% | 66% | 59% | 86% | 96% | **96%** |
| 4 | Min throughput critical (Mbps) | 1.64 | 1.67 | 1.63 | 2.79 | 3.24 | **3.25** |
| 4 | Độ trễ critical (ms) | 2062 | 2334 | 2344 | 652 | 722 | **720** |
| 4 | Min throughput normal (Mbps) | 0.68 | 0.76 | 1.40 | 0.49 | 0.94 | **0.95** |
| 4 | Throughput tổng (Mbps) | 49.9 | 49.7 | 48.2 | 44.3 | 44.2 | **44.1** |
| 4 | Mất gói (%) | 37.6 | 37.9 | 39.7 | 44.6 | 44.8 | **44.8** |

Bốn điều rút ra:

1. **Biết nhóm là điều kiện cần.** Ba baseline không biết nhóm (equal, maxmin, và cả calib-ifair-noclass) chỉ cho 59–69%
   user critical đạt QoS ở tải từ 2 Mbps/user; hai thuật toán biết nhóm đều vượt 86%.
2. **Cùng biết nhóm, calib-ifair vẫn tốt hơn max-min có trọng số.** So với kmeans-wmaxmin ở tải từ 2 Mbps/user, tỷ lệ
   critical đạt QoS tăng từ 86–87% lên 96–97%; min throughput nhóm critical tăng 9–16% (theo seed ×1.0–1.2 ở 2 Mbps,
   ×1.0–1.36 ở 4 Mbps; một seed hòa); và nhóm normal được đối xử tốt hơn hẳn (min throughput 0.95 so với 0.49 Mbps ở
   4 Mbps/user, gần gấp đôi). Throughput tổng và mất gói của hai thuật toán gần như bằng nhau (lệch dưới 3%). Lý do:
   kmeans-wmaxmin tính SNR không nhiễu nên đánh giá sai user nào thật sự yếu, còn calib-ifair tính SINR có nhiễu và tinh
   chỉnh vị trí UAV theo cùng mục tiêu. Riêng độ trễ nhóm critical ở 4 Mbps/user, kmeans-wmaxmin thấp hơn một chút
   (652 so với 720 ms).
3. **Cái giá so với baseline không biết nhóm là hiệu quả tổng.** Ở 4 Mbps/user, throughput tổng của cả hai thuật toán
   biết nhóm giảm khoảng 11% so với kmeans-equal (44 so với 50 Mbps) và mất gói tăng từ 37.6% lên khoảng 45%; ở
   2 Mbps/user giảm 4–6%. Đây là đánh đổi của việc ưu tiên nhóm, có thể chỉnh bằng trọng số w.
4. **Đường cong LTE hiệu chỉnh không tạo khác biệt.** calib-ifair-shannon cho kết quả gần như trùng calib-ifair: tỷ lệ
   min throughput critical giữa hai bản là 1.00–1.02 trên mọi seed, throughput tổng lệch dưới 1%. Lý do là cả hai cùng
   tính nhiễu, và thứ tự ưu tiên giữa các user gần như giống nhau dù dùng Shannon hay đường cong LTE; trần 3.514
   bit/s/Hz hiếm khi chạm vì SINR thực tế có nhiễu không cao. Như vậy, bộ hằng số LTE có giá trị để *dự đoán* số đo NS-3
   (mục 6.6), nhưng không phải là thứ làm thuật toán tốt hơn. Phần làm thuật toán tốt hơn là tính nhiễu khi chia băng,
   tinh chỉnh vị trí, áp quyết định ở tầng MAC (WPF), và đặt mục tiêu có trọng số theo nhóm.

Hình 16 (`experiments/results/classes.png`) vẽ tỷ lệ critical đạt QoS, min throughput của nhóm critical và nhóm normal,
và throughput tổng theo lưu lượng cho cả sáu thuật toán; số liệu đầy đủ ở `experiments/results/classes.csv`, tạo bằng
`experiments/compare_classes.py`.

### 6.13. Tổng hợp: kết luận nào của lý thuyết đứng vững

| Kết luận của lý thuyết | Trên NS-3 |
|---|---|
| Bay về tâm cụm tốt hơn đứng yên | Đúng: min throughput khoảng 2.2 lần, Jain khoảng 1.5 lần, cả 5 seed |
| Nhiễu đồng kênh làm giảm lợi ích khi thêm UAV | Phù hợp |
| Giá trị tuyệt đối của tốc độ | Lạc quan: NS-3 chỉ đạt 25–40% Shannon, đã giải thích bằng ba nguyên nhân |
| Độ trễ và mất gói | Lạc quan, độ trễ thấp hơn 3–9 lần; thêm cách đổi SINR của LTE thì mất gói lệch khoảng 2.7 điểm % |
| Maxmin tăng min rate | Chỉ đúng khi áp ở tầng MAC (WPF: +15–21%, dự đoán +18%) |
| (đề xuất) calib-ifair tăng min rate mà giữ throughput tổng | Đứng vững: min ×1.92–2.03 ở tải ≥ 2 Mbps/user (3/3 seed), tổng trong ±4% |
| (đề xuất) Trọng số nhóm ưu tiên được user critical | Đứng vững: critical đạt QoS 96–97% so với 59–69%, đổi lại tổng giảm 4–12% |
| (đề xuất) calib-ifair hơn max-min có trọng số cùng biết nhóm | Đứng vững: critical đạt QoS 96–97% so với 86–87%, min normal gần gấp đôi, tổng như nhau |
| Quyết định bằng đường cong LTE tốt hơn bằng Shannon | Không đúng: hai bản cho kết quả trùng nhau trong 1–2% |
| Mô hình hàng đợi | Đúng ở mức gói tin, sai số dưới 1% |

---

## 7. Kết luận và hướng phát triển

### 7.1. Kết quả đạt được

| Mục tiêu | Mức độ | Căn cứ |
|---|---|---|
| Khung mô phỏng số, thêm được thuật toán, tái lập được | Hoàn thành | 6 baseline, môi trường DRL, 42 test |
| Đo lại bằng NS-3 LTE | Hoàn thành | Khoảng 400 run, mọi handover thành công |
| Kiểm chứng ba tầng, giải thích chênh lệch | Hoàn thành | Khớp dưới 1%; phân rã sai số ±3% |
| Chia băng thông ở tầng MAC | Hoàn thành | WPF, min throughput tăng 15–21% |
| Điều khiển thời gian thực, hiển thị 3D | Hoàn thành ở mức cơ bản | Dashboard, Gazebo, lệch 0.00 m |
| Heuristic cải tiến dựa trên số đo NS-3 | Hoàn thành | calib-ifair: min throughput ×1.9–2.0 trên NS-3 LTE |
| Ưu tiên theo ba nhóm user | Hoàn thành | Critical đạt QoS 96–97% (baseline không biết nhóm 59–69%, max-min có trọng số 86–87%), tổng giảm 4–12% |
| Trạm điều khiển web: lái tay, đổi tham số, đo NS-3 | Hoàn thành | Lệnh bay tới, 13 tham số (có tỷ lệ nhóm user), đo NS-3 trả về web |
| Huấn luyện agent học tăng cường | Chưa làm | Môi trường đã sẵn sàng |

Dự án cho thấy mô hình giải tích kiểu bài báo đủ tốt để xếp hạng các chiến lược điều khiển UAV, nhưng không đủ để dự đoán
giá trị tuyệt đối, độ trễ, hay hiệu quả của việc chia băng thông khi không gắn với scheduler. Khoảng cách giữa hai bên đã
được giải thích bằng số và thu hẹp được về khoảng ±3% bằng hai hằng số đo từ NS-3.

### 7.2. Hạn chế

Mô hình giữ độ cao cố định, dùng suy hao trung bình thay vì lấy mẫu LoS/NLoS, xấp xỉ nhiễu theo mật độ phổ và chỉ xét
đường xuống. NS-3 chỉ phát lại kế hoạch mà không phản hồi cho thuật toán; công suất của từng user chưa được áp ở tầng
PHY, và WPF chỉ đảm bảo tỷ lệ tài nguyên về lâu dài. Kịch bản NS-3 dùng anten đẳng hướng, SISO, không fading và không
shadowing. Mới có một cấu hình topology (3 UAV, 20 user, đô thị), chủ yếu với scheduler PF và 3–5 seed. Bộ hằng số LTE
hiệu chỉnh chỉ đúng cho 10 MHz SISO với cơ chế thích ứng điều chế mặc định của NS-3. Dashboard hiển thị số tính từ mô
hình, và Gazebo không có PX4 hay động lực học bay.

Phần lớn baseline không biết nhóm user (mục 4.10). Nhóm đã thêm một baseline biết nhóm (max-min có trọng số), nhưng
đó vẫn là một heuristic; chưa có baseline tối ưu lồi có trọng số (BCD + SCA) để biết thuật toán còn cách nghiệm tốt
bao xa. Ngưỡng
r_min theo nhóm mới chỉ là chỉ số chấm điểm, chưa phải ràng buộc cứng; khi quá tải, khoảng 3–4% (user, khe) của nhóm
critical vẫn dưới ngưỡng. Tỷ lệ và trọng số nhóm (15%/25%, 4/2/1) là giá trị chọn tay, chưa khảo sát độ nhạy.

### 7.3. Hướng phát triển

Theo thứ tự ưu tiên, nhóm đề xuất: mở rộng ma trận NS-3 (scheduler RR, số UAV 2/3/5, các môi trường, số user, từ 20 seed
trở lên); huấn luyện agent học tăng cường (PPO, TD3) trên môi trường có sẵn rồi đo bằng NS-3; thêm liên kết cân bằng tải
và quản lý nhiễu (chia băng giữa các UAV, điều khiển công suất); thêm baseline tối ưu lồi BCD + SCA với kênh LoS như Wu,
Zeng và Zhang (2018); thêm ràng buộc pin và tối ưu độ cao; dùng PX4 SITL cho một UAV, nhận lệnh qua MAVLink và đọc vị trí
thật về để tính tốc độ; và nối vòng kín với NS-3 qua ns3-gym.

Nếu áp dụng cho UAV thật, cần đo kênh thực tế để hiệu chỉnh hằng số Al-Hourani, tính đến backhaul, pin và quy định bay,
và nên dùng hệ số an toàn khoảng 0.5–0.6 khi lập kế hoạch lưu lượng.

---

## 8. Tài liệu tham khảo

1. A. Al-Hourani, S. Kandeepan, S. Lardner, "Optimal LAP Altitude for Maximum Coverage," *IEEE Wireless
   Communications Letters*, vol. 3, no. 6, 2014.
2. Q. Wu, Y. Zeng, R. Zhang, "Joint Trajectory and Communication Design for Multi-UAV Enabled Wireless Networks,"
   *IEEE Transactions on Wireless Communications*, vol. 17, no. 3, 2018.
3. Y. Zeng, J. Xu, R. Zhang, "Energy Minimization for Wireless Communication With Rotary-Wing UAV," *IEEE
   Transactions on Wireless Communications*, vol. 18, no. 4, 2019.
4. Y. Zeng, R. Zhang, "Energy-Efficient UAV Communication With Trajectory Optimization," *IEEE Transactions on
   Wireless Communications*, vol. 16, no. 6, 2017.
5. R. Jain, D. Chiu, W. Hawe, "A Quantitative Measure of Fairness and Discrimination for Resource Allocation in Shared
   Computer Systems," DEC Research Report TR-301, 1984.
6. 3GPP TR 36.942, "E-UTRA Radio Frequency (RF) system scenarios," Phụ lục A.1.
7. 3GPP TS 36.213, "E-UTRA Physical layer procedures."
8. ns-3 Model Library, LTE Module (LENA), phiên bản 3.47.
9. Gymnasium documentation, Farama Foundation, phiên bản 1.0.
10. Gazebo Sim (Harmonic) documentation, Open Robotics.

---

## Phụ lục A. Bảng ký hiệu

| Ký hiệu | Ý nghĩa | Đơn vị |
|---|---|---|
| M, K, N | Số UAV, số user, số khe | |
| Δt | Độ dài khe | s |
| L, H | Cạnh vùng, độ cao UAV | m |
| q_m, w_k | Vị trí UAV m, user k | m |
| r_mk, d_mk, θ_mk | Khoảng cách ngang, khoảng cách 3D, góc nâng | m, m, độ |
| f_c, c | Tần số sóng mang, tốc độ ánh sáng | Hz, m/s |
| a, b, η_LoS, η_NLoS | Hằng số Al-Hourani | —, —, dB, dB |
| PL, g_mk | Suy hao, độ lợi kênh | dB, tuyến tính |
| a_k, b_k, p_k, v_m | Liên kết, tỷ lệ băng thông, công suất, vận tốc | —, —, W, m/s |
| B, N₀, P_max | Băng thông, mật độ nhiễu, công suất tối đa | Hz, W/Hz, W |
| S_k, I_k | Mật độ tín hiệu, mật độ nhiễu | W/Hz |
| SINR_k, SE_k, r_k | Tỷ số tín hiệu trên nhiễu, hiệu suất phổ, tốc độ | —, bit/s/Hz, bit/s |
| α, SE_max | Hằng số của công thức tốc độ kiểu LTE | —, bit/s/Hz |
| P(V), E_m | Công suất bay, năng lượng một khe | W, J |
| V_max | Vận tốc tối đa | m/s |
| λ, A | Tốc độ lưu lượng đến, số bit đến mỗi khe | bit/s, bit |
| Q_k, Q_max | Hàng đợi, bộ đệm | bit |
| S_k[n], D_k[n] | Số bit được phục vụ, số bit bị bỏ | bit |
| A_k(t), S_k(t) | Số bit đến, số bit đã phục vụ tích lũy | bit |
| r_min | Ngưỡng QoS | bit/s |

## Phụ lục B. Danh mục hình

| Hình | Nội dung | Nguồn |
|---|---|---|
| 1 | Kịch bản nhiều UAV, ba nhóm user, tín hiệu và nhiễu | `docs/figures/kich_ban.png` (sửa: `kich_ban.drawio`) |
| 2 | Kiến trúc tổng thể | `docs/figures/kien_truc.png` (`.drawio`) |
| 3 | Ba tầng kiểm chứng | `docs/figures/ba_tang.png` (`.drawio`) |
| 4 | Lưu đồ phát lại kế hoạch trong NS-3 | Mục 5.7, cần vẽ |
| 4b | Lưu đồ thuật toán đề xuất calib-ifair | `docs/figures/calib_ifair.png` (`.drawio`) |
| 5 | Kiến trúc điều khiển thời gian thực | `docs/figures/thoi_gian_thuc.png` (`.drawio`) |
| 6 | Dashboard (thuật toán calib-ifair, ba nhóm user) | `docs/figures/dashboard.png` |
| 7 | Gazebo toàn cảnh | `docs/figures/gazebo.png` |
| 8 | Kết quả mô hình | `experiments/results/demo/compare.png` |
| 9 | Ma trận NS-3 theo tải | `experiments/results/ns3-matrix/ns3_matrix.png` |
| 10 | Đường cong một liên kết | `experiments/results/validation/validation.png` |
| 11 | Phân rã từ Shannon tới NS-3 | `experiments/results/validation/decomposition.png` |
| 12 | Độ trễ, mất gói: lý thuyết và NS-3 | `experiments/results/ns3-demand-lte/theory_vs_ns3.png` |
| 13 | Ba tầng, scheduler PF | `experiments/results/three_tier_pf.png` |
| 14 | Ba tầng, scheduler WPF | `experiments/results/three_tier_wpf.png` |
| 15 | Thuật toán đề xuất so với baseline, NS-3 LTE | `experiments/results/proposed.png` |
| 16 | Ba nhóm user: critical đạt QoS, min throughput theo nhóm, throughput tổng, NS-3 LTE | `experiments/results/classes.png` |

Ảnh động (dùng khi thuyết trình, trong báo cáo dùng một khung hình): `experiments/results/anim.gif` (hover, kmeans,
random), `experiments/results/anim_classes.gif` (kmeans-equal, calib-ifair-noclass, calib-ifair với ba nhóm user; tạo
bằng `python -m uavsim.animate --algos kmeans-equal calib-ifair-noclass calib-ifair --set slots=60 --set demand_mbps=2
--set rate_model=lte --set lte_alpha=0.401 --set lte_se_max=3.514 --set important_frac=0.25 --set critical_frac=0.15
--set seed=1 --every 1 --out experiments/results/anim_classes.gif`). Sơ đồ draw.io sinh lại bằng
`python docs/figures/make_diagrams.py docs/figures` rồi `drawio -x -f png -s 2 -o <tên>.png <tên>.drawio`. Bộ slide
LaTeX ở `slides/main.tex` (biên dịch `cd slides && latexmk -xelatex main.tex`).

## Phụ lục C. Tái lập kết quả

Các lệnh chạy từ thư mục dự án với Python trong `.venv`; NS-3 cần được build trước bằng `ns3/install.sh`. Phần này dùng
để kiểm tra lại số liệu, không đưa vào báo cáo nộp.

| Kết quả | Lệnh | Thời gian |
|---|---|---|
| E1 | `python -m uavsim.run` | dưới 5 s |
| E2 | `python -m uavsim.ns3 --algos hover-equal kmeans-equal kmeans-maxmin --load 0.5 0.6 0.7 0.8 0.9 1.0 --seeds 5 --set slots=60` | khoảng 36 phút |
| E3, E4 | `python -m uavsim.validate --runs …` (xem tài liệu thiết kế, mục 14.3–14.5) | |
| E5 | `python -m uavsim.ns3 --link lte --set demand_mbps=1 --load 0.5 1 1.5 2 2.5 3 4 --seeds 3 --set slots=60` | khoảng 30 phút |
| E6 | Như E5, thêm `--scheduler wpf --algos hover-maxmin kmeans-maxmin` | khoảng 20 phút |
| E7 | Như E5, E6 với `--link ideal`, rồi `python experiments/plot_three_tier.py <thư mục ideal> <thư mục lte> <hình>` | vài phút |
| E9 | `python -m uavsim.live --gazebo`, mở `http://localhost:8000` | |
| E10 | `python -m uavsim.ns3 --link lte --algos calib-ifair kmeans-ifair calib-equal --scheduler wpf --set demand_mbps=1 --load 0.5 1 1.5 2 2.5 3 4 --seeds 3 --set slots=60`, rồi `python experiments/compare_proposed.py experiments/results/proposed` | khoảng 40 phút |
| E11 | `python -m uavsim.ns3 --algos calib-ifair calib-ifair-shannon --scheduler wpf --set demand_mbps=1 --set important_frac=0.25 --set critical_frac=0.15 --load 0.5 1 1.5 2 2.5 3 4 --seeds 3 --set slots=60 --out experiments/results/ns3-classes-lte`; lệnh tương tự với `--algos kmeans-wmaxmin --out experiments/results/ns3-wmaxmin-lte`; rồi `python experiments/compare_classes.py experiments/results/classes` | khoảng 25 phút |
| Kiểm thử | `python -m pytest -q tests` | khoảng 1 phút |

Kết quả đã chạy có sẵn trong `experiments/results/`, mỗi thư mục kèm `config.json` để chạy lại đúng cấu hình.

## Phụ lục D. Ghi chú cho người viết báo cáo và làm slide

### D.1. Yêu cầu của tiêu chí cần nhớ

Báo cáo không quá 100 trang A4 và không chứa code; dùng mã giả, lưu đồ, công thức và bảng. Các dòng lệnh ở Phụ lục C
và tên hàm, tên file trong tài liệu này là để người viết tra cứu, không chép vào báo cáo; trong báo cáo chỉ cần nói
"kết quả tái lập được, mỗi thí nghiệm lưu kèm cấu hình". Kết luận cải tiến phải có số
liệu hoặc lập luận có căn cứ, và nên có ít nhất một phương pháp tham chiếu để so sánh (ở đây là hover-equal và lý thuyết
theo kiểu bài báo). Khi dùng giải pháp có sẵn (kmeans, scheduler PF, mô hình Al-Hourani) cần nêu lý do chọn và ưu,
nhược điểm.

### D.2. Phân bổ số trang gợi ý

| Chương | Điểm | Số trang | Hình, bảng nên có |
|---|---|---|---|
| 1. Đóng góp | 5 | 1 | Bảng phân công |
| 2. Cấp thiết | 10 | 5–7 | Hình 1, bảng so sánh cách làm hiện có |
| 3. Kiến trúc | 15 | 10–12 | Hình 2, 3, 5; bảng so sánh hệ thống |
| 4. Mô hình toán | 15 | 12–15 | Bảng tham số, bảng hằng số, ví dụ số |
| 5. Triển khai | 20 | 15–18 | Mã giả 5.3–5.6, lưu đồ 5.7, hình 4, 6, 7 |
| 6. Hiệu năng | 25 | 25–30 | Hình 8–16 và các bảng chương 6 |
| 7. Kết luận | 5 | 2–3 | Bảng mức độ hoàn thành |
| Tài liệu tham khảo, phụ lục | 5 | 3–5 | |

### D.3. Những điểm nên nhấn mạnh

Năm ý chính xuyên suốt: (0) thuật toán đề xuất calib-ifair với ba nhóm user: nâng min throughput gần gấp đôi trên NS-3
LTE mà giữ throughput tổng, và khi có nhóm thì đưa tỷ lệ user critical đạt QoS từ 59–69% lên 96–97% với giá throughput
tổng giảm 4–12%, và hơn cả max-min có trọng số cùng biết nhóm. Đây là phần cải tiến chính; nên gọi là "heuristic cải
tiến", không gọi là "thuật toán mới" hay "thuật toán tối ưu", vì các thành phần đều dựa trên kỹ thuật đã có. Cần nói
trung thực rằng lợi ích đến từ việc tính nhiễu, tinh chỉnh vị trí, áp ở MAC và trọng số nhóm; bản dùng Shannon thay đường cong LTE cho kết quả như nhau (mục 6.12); (1) kết quả đo bằng giao thức thật chỉ bằng 25–40% con số Shannon mà các bài báo dùng; (2) nhờ
tầng liên kết lý tưởng, nhóm chứng minh được mô hình đúng (sai số dưới 1%), nên khoảng chênh là do LTE và đã được giải
thích bằng ba nguyên nhân; (3) thứ hạng giữa các thuật toán vẫn đúng, còn việc chia băng thông chỉ có tác dụng khi áp ở
tầng MAC; (4) hệ thống điều khiển thời gian thực đồng bộ hoàn toàn với mô hình và ghi phiên lại để đo được.

Khi viết chương 6, nên nói rõ số liệu là tính hay đo, ghi đơn vị và số seed, và so sánh thuật toán theo cặp trên cùng
seed. Các sơ đồ ASCII trong tài liệu này nên được vẽ lại bằng draw.io. Thông tin xuất bản của tài liệu tham khảo cần đối
chiếu lại với bản gốc, và nên bổ sung vài bài báo gần đây (2021–2025) về UAV làm trạm gốc dùng học tăng cường hoặc tối
ưu cho chương 2.

### D.4. Dàn ý slide (khoảng 20 slide, 15–20 phút)

| # | Slide | Nội dung | Hình |
|---|---|---|---|
| 1 | Tiêu đề | Tên đề tài, nhóm, giảng viên | |
| 2 | Bối cảnh | Thiên tai, sự kiện đông người, UAV mang trạm gốc | Ảnh minh họa |
| 3 | Vấn đề | Bài báo chỉ tính bằng Shannon; con số thật là bao nhiêu? | |
| 4 | Mục tiêu | Sáu mục tiêu ở mục 2.3 | |
| 5 | Kịch bản | M UAV, K user, nhiễu, khe thời gian | Hình 1 |
| 6 | Mô hình kênh | Al-Hourani; từ 100 m lên 300 m mất 20 dB | |
| 7 | Tốc độ, năng lượng, hàng đợi | Ba công thức chính, độ trễ FIFO | |
| 8 | Bài toán tối ưu | Ba nhóm user, max Σ w log r, ràng buộc mỗi UAV, tính không lồi; mục tiêu và cách chấm điểm tách riêng | |
| 9 | Kiến trúc | | Hình 2 |
| 10 | Ba tầng kiểm chứng | Vai trò của tầng giữa | Hình 3 |
| 11 | Thuật toán | Sáu baseline, kmeans, maxmin | |
| 12 | NS-3 và WPF | Ánh xạ mô hình sang NS-3, scheduler có trọng số | Hình 4 |
| 13 | Kết quả mô hình | kmeans tăng sum rate 1.7 lần, min rate 2.6 lần | Hình 8 |
| 14 | NS-3 chịu tải | Đạt khoảng 70% công thức 3GPP; nên gửi 50–60% | Hình 9 |
| 15 | Vì sao chênh lệch | Shannon → 3GPP → trần → AMC; NS-3 bằng 25–40% Shannon | Hình 11 |
| 16 | Độ trễ, mất gói | Lý thuyết lạc quan 3–9 lần; ba nguyên nhân | Hình 12 |
| 17 | Ba tầng | Lý thuyết khớp NS-3 lý tưởng dưới 1% | Hình 13 |
| 18 | Chia băng ở tầng MAC | WPF tăng min throughput 15–21% | |
| 18b | Thuật toán đề xuất | Tính nhiễu khi chia băng, áp ở MAC; min ×2 trên NS-3 LTE | Hình 15 |
| 18c | Ba nhóm user | Critical đạt QoS 96–97% so với 59–69% (không biết nhóm) và 86–87% (max-min có trọng số); tổng giảm 4–12%; LTE hay Shannon như nhau | Hình 16 |
| 19 | Demo | Dashboard và Gazebo, lái tay | Hình 6, 7 |
| 20 | Kết luận, hạn chế, hướng phát triển | Bảng 6.13, mục 7.2 | |

Nếu demo trực tiếp: chạy `python -m uavsim.live --gazebo`, bật lái tay cho UAV 1 và lái ra khỏi cụm; các user của nó
chuyển màu hoặc hiện dấu ×, min rate trên biểu đồ tụt xuống; tắt lái tay thì kmeans kéo UAV về và tốc độ hồi lại.
