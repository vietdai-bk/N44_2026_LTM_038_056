# Mô tả dự án: cấp phát tài nguyên cho mạng nhiều UAV làm trạm gốc, kiểm chứng bằng NS-3

Phần này giới thiệu ngắn gọn dự án: nhóm giải bài toán gì, làm theo hướng nào, hệ thống gồm những phần nào, kết quả ra
sao và còn thiếu gì. Công thức, thông số và chi tiết cài đặt có trong [`THIET_KE_MO_PHONG.md`](THIET_KE_MO_PHONG.md);
cách cài đặt và chạy có trong [`HUONG_DAN_CHAY.md`](HUONG_DAN_CHAY.md).

---

## 1. Bài toán

Một số UAV bay ở độ cao cố định, mỗi chiếc mang một trạm gốc và phát đường xuống cho user mặt đất trong vùng 1 × 1 km.
Cứ mỗi khe thời gian (1 s), hệ thống phải quyết định user nào gắn vào UAV nào, mỗi UAV chia băng thông và công suất cho
các user của nó ra sao, và mỗi UAV bay theo vận tốc nào. Các UAV dùng chung băng tần nên gây nhiễu cho nhau, và việc bay
tốn năng lượng. Đây là dạng bài toán gặp rất nhiều trong các bài báo IEEE về UAV (TWC, TVT, IoT-J, JSAC).

**Ba nhóm user.** Trong kịch bản cứu hộ, người dùng không quan trọng như nhau. Mỗi user thuộc một trong ba nhóm:
normal (người dân, trọng số 1, mong muốn ≥ 0.5 Mbps), important (điều phối, camera, trọng số 2, ≥ 1 Mbps) và critical
(đội cứu hộ, y tế, trọng số 4, ≥ 2 Mbps). Thí nghiệm dùng 60% normal, 25% important, 15% critical; nhóm được bốc theo
seed, độc lập với vị trí.

**Mục tiêu của đề tài:** phục vụ người dùng công bằng theo mức ưu tiên mà không làm giảm nhiều hiệu quả tổng, và kết quả
phải đúng khi đo trên mạng LTE (NS-3), không chỉ đúng trên công thức Shannon. Viết thành công thức là tối đa tổng log có
trọng số Σ_k w_k log(r_k + r_0), tức công bằng tỷ lệ có trọng số. Mục tiêu này nằm giữa tối đa tổng tốc độ (bỏ rơi user
ở rìa) và tối đa tốc độ nhỏ nhất (hy sinh nhiều tổng tốc độ), và trọng số w đẩy user nhóm cao lên trước.

**Cách so sánh:** các baseline có mục tiêu riêng (`equal` gần với tối đa tổng, `maxmin` tối đa user kém nhất, DRL tối đa
tổng có phạt) và không biết nhóm user. Mọi thuật toán đều được chấm bằng cùng một bộ chỉ số đo trên NS-3: tổng
throughput, min throughput, độ trễ, mất gói, và theo từng nhóm: min throughput và tỷ lệ đạt QoS. Baseline `kmeans-wmaxmin` (max-min có trọng số) cũng biết nhóm, để so sánh trên cùng thông tin. Bốn bản so sánh có
cùng mục tiêu với thuật toán đề xuất: `kmeans-ifair`, `calib-equal` (bỏ một khối), `calib-ifair-noclass` (bỏ qua nhóm)
và `calib-ifair-shannon` (tính tốc độ bằng Shannon như bài báo). Chi tiết ở `BAO_CAO_DU_AN.md`, mục 4.10.

Vì đây là đồ án môn Lập trình mạng, ngoài kết quả tính theo công thức như các bài báo, nhóm còn phải đo lại ở mức gói
tin bằng NS-3.

## 2. Hướng làm: so sánh ba tầng

Các bài báo thường chỉ tính năng lực mạng bằng công thức Shannon. Nhóm đặt kết quả đó cạnh hai phép đo NS-3:

```
Lý thuyết (bài báo) ──khớp < 1%──► NS-3 liên kết lý tưởng ──chênh──► NS-3 LTE
   công thức Shannon,               gói UDP thật,                     giao thức LTE đầy đủ:
   hàng đợi                         tốc độ liên kết = tốc độ          eNB, UE, EPC, handover,
                                    lý thuyết từng khe                scheduler, HARQ
```

So lý thuyết với NS-3 lý tưởng cho biết mô hình hàng đợi (độ trễ, mất gói) và toàn bộ đường ống xử lý có đúng ở mức gói
tin hay không. So NS-3 lý tưởng với NS-3 LTE cho biết giao thức LTE thật làm kết quả khác lý thuyết bao nhiêu và vì sao.

Cách làm cụ thể: thuật toán ra quyết định trên mô hình Python và ghi lại thành một kế hoạch (quỹ đạo UAV, liên kết, tốc
độ và băng thông của từng user ở từng khe) dưới dạng CSV. NS-3 phát lại đúng kế hoạch đó và đo. NS-3 không phản hồi cho
thuật toán trong lúc chạy.

## 3. Các thành phần

### 3.1. Mô hình Python `uavsim`

Mô hình kênh là của Al-Hourani (2014): xác suất có đường nhìn thẳng phụ thuộc góc nâng, với bốn loại môi trường từ ngoại
ô đến nhà cao tầng; có thể thay bằng kênh chỉ có LoS và thêm fading Rician. Tốc độ tính theo Shannon như các bài báo,
hoặc theo công thức Shannon có cắt ngọn của 3GPP TR 36.942 cho gần với LTE. Các UAV dùng chung băng tần nên có nhiễu đồng
kênh, và có tùy chọn để nhiễu giảm khi UAV gây nhiễu ít dùng băng. Năng lượng bay theo mô hình UAV cánh quay của Zeng, Xu
và Zhang (2019). Khi bật lưu lượng, mỗi user có một hàng đợi 1 MiB, và mô hình tính throughput, độ trễ FIFO chính xác của
từng bit và mất gói do tràn bộ đệm.

Có sáu thuật toán baseline, ghép từ ba cách di chuyển (đứng yên, bay về tâm cụm bằng kmeans, bay ngẫu nhiên) và hai cách
chia băng thông (chia đều, maxmin), cùng một giao diện chung để thêm thuật toán mới. Có sẵn môi trường Gymnasium cho học
tăng cường, nhưng chưa huấn luyện agent nào. Với cùng cấu hình và seed, kết quả giống nhau từng bit.

### 3.2. Kịch bản NS-3 `uav-lte`

Kịch bản viết bằng C++ trên NS-3 3.47 và có hai chế độ liên kết. Ở chế độ LTE, mỗi UAV là một eNB, mỗi user là một UE,
có EPC, handover X2 khi kế hoạch đổi UAV phục vụ, và kênh Al-Hourani được viết lại thành một lớp của NS-3 với đúng công
thức như Python. Việc chia băng thông do scheduler PF, RR, hoặc WPF (Weighted PF do nhóm viết, trọng số lấy từ thuật
toán) đảm nhận; bộ đệm là RLC UM 1 MiB. Một run 60 khe mất khoảng 4 phút. Ở chế độ lý tưởng, LTE được bỏ đi, mỗi user nối
với máy chủ bằng một liên kết điểm-điểm có tốc độ bằng tốc độ lý thuyết của khe đó, hàng đợi DropTail 1 MiB; một run chỉ
mất khoảng 6 giây. Cả hai chế độ dùng chung bộ phát UDP đổi tốc độ đúng đầu khe, cùng cách đo và cùng định dạng kết quả.

### 3.3. Trạm điều khiển thời gian thực: dashboard web và Gazebo

Lệnh `python -m uavsim.live` chạy mô hình đúng thời gian thực (khe 0.25 s, tăng tốc được tới 4×, trình duyệt nội suy
chuyển động 60 lần mỗi giây) và mở dashboard ở
`http://localhost:8000`. Trên dashboard có bản đồ hai chiều với UAV, user và các đường liên kết, các chỉ số và biểu đồ
throughput, min rate, độ trễ theo thời gian. Người dùng có thể bật lái tay cho một UAV rồi điều khiển bằng W A S D hoặc
nút trên màn hình; vận tốc nhập vào thay cho vận tốc thuật toán tính, còn các UAV khác vẫn tự động. Nhấp lên bản đồ thì UAV
đang chọn bay tới điểm đó. Có thể đổi thuật toán và 13 tham số kịch bản (số UAV, số user, độ cao, công suất, lưu lượng, tỷ lệ user
important và critical…)
ngay khi đang chạy, và bấm "Ghi & đo" để server ghi một đoạn rồi đo bằng NS-3 (liên kết lý tưởng hoặc LTE), kết quả hiện
ngay trên web.

Khi thêm `--gazebo`, cùng kịch bản đó (cùng cấu hình và seed với các thí nghiệm) được vẽ ba chiều trong Gazebo Harmonic,
trên nền bãi thảm họa của dự án `~/simulation/multi_uav`, với tỷ lệ 1:10. Gazebo chỉ dùng để xem, không có PX4 hay động
lực học bay. Trình duyệt nói chuyện với server qua WebSocket, còn server nói chuyện với Gazebo qua gz-transport.

### 3.4. Công cụ phân tích

`uavsim/ns3.py` ghi kế hoạch, chạy NS-3 song song, đọc số đo, đặt cạnh số của mô hình và gộp nhiều seed.
`uavsim/validate.py` dùng để tìm nguyên nhân chênh lệch: khớp đường cong SINR ra throughput, tính lại mô hình với hằng số
đã khớp, so SINR, so các biến thể lý thuyết với NS-3. `experiments/plot_three_tier.py` vẽ biểu đồ ba tầng và ghi bảng sai
số của từng tầng.

## 4. Kết quả chính

Các kết quả dưới đây dùng cấu hình 3 UAV, 20 user phân cụm, môi trường đô thị, băng thông 10 MHz, công suất 1 W. Số liệu
chi tiết có ở mục 14 của tài liệu thiết kế.

### 4.1. Mô hình hàng đợi đúng ở mức gói tin

Nhóm so lý thuyết với NS-3 liên kết lý tưởng trên 105 run (5 thuật toán, lưu lượng 0.5–4 Mbps mỗi user, 3 seed). Sai số
lớn nhất là 0.02% với throughput, 1.0% với độ trễ, 0.014 điểm phần trăm với mất gói và 2.1% với min throughput (dưới
0.8% khi lưu lượng từ 1 Mbps/user trở lên). Để khớp được như vậy, nhóm phải dùng chung định nghĩa mất gói với NS-3 (tính
cả gói còn trong hàng đợi lúc kết thúc), thay công thức độ trễ theo định luật Little bằng độ trễ FIFO chính xác, và cho bộ
đệm hai bên đếm cùng đơn vị.

### 4.2. LTE khác lý thuyết, và nhóm đã giải thích được vì sao

NS-3 LTE chỉ chuyển được 65–75% tốc độ tính theo công thức 3GPP. Nguyên nhân đã được kiểm chứng: LTE 10 MHz SISO trong
NS-3 đổi SINR ra throughput với độ dốc khoảng 0.40 và trần khoảng 3.51 bit/s/Hz, thay vì 0.6 và 4.4 như công thức. Thay
hai hằng số này vào thì mô hình khớp NS-3 trong khoảng ±2%.

Lý thuyết theo kiểu bài báo cũng quá lạc quan về chất lượng dịch vụ: độ trễ thấp hơn NS-3 nhiều lần và mất gói thấp hơn
nhiều. Ba đặc điểm của LTE giải thích phần lớn khoảng chênh: cách đổi SINR ra tốc độ, nhiễu thay đổi theo tải (quan trọng
khi tải nhẹ) và scheduler chia lại tài nguyên (quan trọng khi tải trung bình). Khi thêm cách đổi SINR của LTE vào lý
thuyết, sai số throughput còn khoảng 3.5% và sai số mất gói còn khoảng 2.7 điểm phần trăm.

Về vận hành, nếu chỉ gửi 50% tốc độ kế hoạch thì NS-3 chuyển hết với độ trễ khoảng 10 ms; từ 70% trở lên độ trễ lên tới
hàng giây. Vì vậy nên dùng hệ số an toàn khoảng 0.5–0.6.

### 4.3. Thuật toán đề xuất

Từ các kết quả trên, nhóm cải tiến các heuristic có sẵn (k-means, max-min có trọng số, PF có trọng số) thành heuristic
`calib-ifair`. Đây không phải thuật toán mới về nguyên lý; điểm cải tiến là cách kết hợp và việc kiểm chứng bằng NS-3.
Thuật toán: chia băng cho tốc độ dự đoán bằng nhau trong mỗi UAV, với
tốc độ tính bằng SINR có nhiễu và ánh xạ LTE đo được từ NS-3, rồi tinh chỉnh vị trí UAV sau khi tới tâm cụm để tăng tiện
ích công bằng tỷ lệ; trọng số được áp ở tầng MAC qua WPF. Đo bằng NS-3 LTE, so với kmeans-equal trên cùng seed, thuật
toán nâng min throughput 1.92–2.03 lần khi tải từ 2 Mbps/user trở lên (cả 3 seed), giữ throughput tổng trong ±4%; ở
tải 1 Mbps/user, độ trễ giảm từ 152 xuống 72 ms và mất gói từ 2.2% xuống 0.5%. Maxmin của baseline chỉ được khoảng 1.1
lần.

Khi thêm ba nhóm user (15% critical, 25% important, 60% normal; trọng số 4/2/1), `calib-ifair` dồn tài nguyên cho nhóm
ưu tiên. Đo bằng NS-3 LTE (42 run mới, baseline dùng lại run cũ), từ 2 Mbps/user trở lên tỷ lệ user critical đạt QoS
tăng từ 59–69% (baseline và bản bỏ qua nhóm) lên 96–97%, min throughput nhóm critical tăng 1.5–2 lần và độ trễ nhóm
critical ở 2 Mbps/user giảm từ hơn 1 s xuống 41 ms. So với baseline cũng biết nhóm (max-min có trọng số,
`kmeans-wmaxmin`, 21 run), tỷ lệ critical đạt QoS vẫn cao hơn (96–97% so với 86–87%), min throughput nhóm normal gần
gấp đôi, còn throughput tổng như nhau. Cái giá là throughput tổng giảm 4–12% và nhóm normal chịu độ trễ cao
hơn, dù min throughput của nhóm normal vẫn cao hơn baseline. Bản `calib-ifair-shannon` (cùng thuật toán nhưng tính tốc độ
bằng Shannon) cho kết quả trùng trong 1–2%: lợi ích đến từ việc tính nhiễu, áp ở MAC và trọng số nhóm, không đến từ
đường cong LTE hiệu chỉnh. Chi tiết ở `BAO_CAO_DU_AN.md`, mục 6.12, hình `experiments/results/classes.png`.

### 4.4. Kết luận nào của mô hình đứng vững trên NS-3

| Kết luận của mô hình | Trên NS-3 LTE |
|---|---|
| Bay về tâm cụm user (kmeans) tốt hơn đứng yên (hover) | Đúng: min throughput khoảng 2.2 lần, Jain khoảng 1.5 lần, cả 5 seed |
| Thêm UAV dùng chung băng có thể làm giảm tổng tốc độ vì nhiễu | Phù hợp (1 trên 5 seed) |
| Maxmin nâng user kém nhất | Chỉ đúng khi áp ở tầng MAC: với PF, maxmin và equal cho số đo giống hệt; với WPF, min throughput tăng 16–18% ở cả 3 seed, khớp dự đoán +18% |
| Giá trị tuyệt đối của tốc độ, độ trễ, mất gói | Lạc quan (mục 4.2) |

Ở tầng lý tưởng, maxmin khác equal rõ rệt đúng như lý thuyết, nên việc hai thuật toán giống nhau trên LTE với PF là do
scheduler, không phải do lý thuyết tính sai. Nói chung, mô hình giải tích đủ tốt để xếp hạng các chiến lược điều khiển,
nhưng không đủ để dự đoán giá trị tuyệt đối hay hiệu quả của việc chia băng thông khi không gắn với scheduler MAC.

## 5. Cấu trúc thư mục

```
LapTrinhMang/
├── uavsim/                      # mô hình Python
│   ├── config.py                # SimConfig: mọi tham số
│   ├── channel.py, energy.py    # kênh A2G, năng lượng bay
│   ├── network.py               # trạng thái mạng, tốc độ, hàng đợi, độ trễ FIFO, một bước thời gian
│   ├── algorithms.py            # các baseline và REGISTRY
│   ├── env.py                   # môi trường Gymnasium
│   ├── run.py, animate.py       # so sánh thuật toán, animation
│   ├── live.py, gazebo.py       # điều khiển thời gian thực, hiển thị 3D
│   ├── web/index.html           # dashboard
│   ├── ns3.py                   # cầu nối NS-3
│   └── validate.py              # phân tích nguyên nhân chênh lệch
├── ns3/
│   ├── scratch/uav_lte/uav-lte.cc               # kịch bản NS-3 (lte và ideal)
│   ├── scratch/uav_lte/wpf-ff-mac-scheduler.*   # scheduler Weighted PF
│   └── install.sh                               # gắn vào cây NS-3 và build
├── experiments/
│   ├── plot_three_tier.py       # biểu đồ ba tầng
│   └── results/                 # kết quả các lần chạy, mỗi thư mục có config.json
├── tests/test_uavsim.py         # 42 test
├── docs/
│   ├── MO_TA_DU_AN.md           # mô tả tổng quan
│   ├── BAO_CAO_DU_AN.md         # báo cáo tóm tắt theo tiêu chí đánh giá
│   └── THIET_KE_MO_PHONG.md     # thiết kế chi tiết
└── README.md                    # giới thiệu, chạy nhanh
```

## 6. Tình trạng hiện tại

Những phần đã xong gồm mô hình Python với sáu baseline, môi trường học tăng cường và animation; kịch bản NS-3 LTE,
scheduler Weighted PF và chế độ liên kết lý tưởng; ma trận NS-3 LTE 90 run, thí nghiệm tách nhiễu và phân tích nguyên
nhân chênh lệch; so sánh ba tầng trên 105 run với sai số dưới 1%; hệ thống điều khiển thời gian thực có dashboard, lái
tay, hiển thị Gazebo và ghi phiên để phát lại trong NS-3; ba nhóm user có trọng số; và 42 test, kể cả các test chạy NS-3. Biểu đồ ba tầng nằm ở
`experiments/results/three_tier_pf.png` và `three_tier_wpf.png`.

Những việc chưa làm, theo thứ tự nhóm đề xuất: mở rộng ma trận NS-3 (scheduler RR, số UAV, môi trường, số user); huấn
luyện agent học tăng cường; liên kết cân bằng tải, quản lý nhiễu và baseline tối ưu lồi BCD + SCA; áp công suất của từng
user ở tầng PHY; và dùng PX4 SITL cho một UAV, nhận lệnh qua MAVLink và đọc vị trí thật về để tính tốc độ.

Khi đọc kết quả cần lưu ý rằng cả hai tầng đều là mô phỏng chứ không phải đo trên phần cứng; NS-3 chỉ phát lại kế hoạch,
không có vòng kín với thuật toán; kịch bản NS-3 dùng anten đẳng hướng, SISO, không fading, không shadowing và chỉ có
đường xuống; liên kết lý tưởng chỉ kiểm chứng phần hàng đợi, còn công thức kênh và SINR được kiểm chứng bằng NS-3 LTE;
mới có một cấu hình topology (3 UAV, 20 user, đô thị); và dashboard hiển thị số tính từ mô hình chứ không phải số đo mạng.
