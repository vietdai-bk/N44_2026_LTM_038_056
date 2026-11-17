# Kịch bản thuyết trình

Kịch bản đi theo bộ slide `slides/main.pdf` (34 trang). Tổng thời gian khoảng **25 phút**, cộng phần hỏi đáp. Mỗi slide
có: thời lượng gợi ý, lời nói (đọc tự nhiên, không cần thuộc từng chữ) và ghi chú cho người trình bày. Phần thuật toán
(slide 9–19) là trọng tâm, nên chiếm gần nửa thời gian.

| Phần | Slide | Thời gian |
|---|---|---|
| Mở đầu, bài toán | 1–8 | 6 phút |
| Heuristic calib-ifair | 9–19 | 9 phút |
| Thí nghiệm, kết quả | 20–26 | 5 phút |
| Hệ thống, lập trình mạng, tổng kết | 27–34 | 5 phút |

---

## Slide 1. Trang bìa (20 giây)

> Kính chào thầy cô và các bạn. Nhóm em xin trình bày đồ án môn Lập trình mạng: **cấp phát tài nguyên cho mạng nhiều
> UAV làm trạm gốc có ưu tiên người dùng**. Nhóm đề xuất một heuristic cải tiến tên là calib-ifair, và kiểm chứng nó ở
> mức gói tin bằng NS-3 LTE.

## Slide 2. Nội dung trình bày (20 giây)

> Bài trình bày gồm bốn phần: bài toán, heuristic calib-ifair, kiểm chứng bằng NS-3, và cuối cùng là hệ thống điều
> khiển cùng phần tổng kết. Phần thứ hai là trọng tâm, nhóm em sẽ giải thích chi tiết.

## Slide 3. Bối cảnh và vấn đề (45 giây)

> Khi có thiên tai hay sự kiện đông người, trạm gốc mặt đất có thể hỏng hoặc quá tải. Một giải pháp là dùng UAV mang
> trạm gốc LTE bay tới vùng cần phủ sóng.
>
> Bài toán này có ba khó khăn. Thứ nhất, vị trí UAV quyết định chất lượng kênh. Thứ hai, các UAV dùng chung băng tần nên
> gây nhiễu cho nhau. Thứ ba, người dùng không quan trọng như nhau: trong cứu hộ, đội cứu hộ và y tế cần kết nối chắc
> chắn hơn người dân.
>
> Ngoài ra, các bài báo thường chỉ tính bằng công thức Shannon. Nhóm muốn biết kết quả có còn đúng khi đo ở mức gói tin
> trên mạng LTE thật hay không.

*Ghi chú: chỉ vào hình Gazebo, nói ngắn "đây là kịch bản nhóm dựng trên bãi thảm họa, vòng đỏ là người dùng critical".*

## Slide 4. Kịch bản và ba nhóm người dùng (40 giây)

> Kịch bản gồm 3 UAV phục vụ 20 người dùng trong vùng 1 km × 1 km. Người dùng chia thành ba nhóm. Normal là người dân,
> trọng số 1. Important là điều phối, camera giám sát, trọng số 2. Critical là đội cứu hộ, y tế, trọng số 4.
>
> Mỗi khe thời gian, thuật toán phải quyết định bốn thứ: người dùng nối với UAV nào, mỗi người được bao nhiêu băng
> thông, công suất phát, và UAV bay theo hướng nào.

## Slide 5. Phát biểu bài toán (40 giây)

> Đầu vào là vị trí và nhóm của người dùng, vị trí hiện tại của UAV, các tham số vô tuyến và lưu lượng gửi tới mỗi
> người. Đầu ra mỗi khe là liên kết, băng thông, công suất và vận tốc UAV.
>
> Mục tiêu là ưu tiên critical, rồi important, nhưng **không bỏ rơi** người dùng normal. Nhóm giả thiết xét đường
> xuống, các UAV dùng chung băng, độ cao cố định.

## Slide 6. Mô hình kênh, SINR và tốc độ (45 giây)

> Kênh từ UAV xuống mặt đất dùng mô hình Al-Hourani: xác suất có đường nhìn thẳng phụ thuộc góc ngẩng, suy hao gồm phần
> không gian tự do cộng phần suy hao thêm.
>
> SINR của người dùng có mẫu số là nhiễu từ các UAV khác. Đây là điểm quan trọng: vị trí UAV nằm cả trong tín hiệu lẫn
> trong nhiễu, nên dịch một UAV làm thay đổi chất lượng của người dùng ở UAV khác.
>
> Tốc độ theo bài báo dùng Shannon. Nhóm còn đo trên NS-3 và hiệu chỉnh ra công thức LTE với hai hằng số 0.401 và 3.514.

## Slide 7. Băng thông của mỗi UAV (50 giây)

> Trước khi vào bài toán tối ưu, nhóm giải thích tài nguyên cần chia là gì. Mỗi UAV có một kênh LTE rộng 10 MHz ở tần
> số 2 GHz, chia thành 50 khối tài nguyên. Mọi UAV dùng chung tần số này, nên chúng gây nhiễu cho nhau.
>
> b_k là phần băng của UAV dành cho người dùng k. Tốc độ bằng số Hz được cấp nhân với hiệu suất phổ, mà hiệu suất phổ
> phụ thuộc chất lượng kênh. Vì vậy người có kênh xấu cần nhiều Hz hơn mới đạt cùng tốc độ.
>
> Trong NS-3, băng không bị cắt cố định cho từng người. Cứ mỗi mili giây, scheduler chia 50 khối cho các người dùng;
> scheduler WPF nhận b_k làm trọng số, nên tính trung bình người dùng k nhận khoảng b_k phần tài nguyên.

*Ghi chú: chỉ vào thanh 50 ô: phần đỏ (75%) là của người critical trong ví dụ số ở Khối 2.*

## Slide 8. Bài toán tối ưu (P) (50 giây)

> Hàm mục tiêu là tổng log tốc độ có trọng số, còn gọi là công bằng tỷ lệ có trọng số. Các ràng buộc gồm: mỗi người nối
> một UAV, tổng băng thông và công suất của mỗi UAV không vượt giới hạn, UAV bay không quá vận tốc tối đa và ở trong
> vùng.
>
> Vì sao chọn tổng log? Nếu tối đa tổng tốc độ thì người dùng ở rìa gần như bị bỏ rơi. Nếu tối đa tốc độ nhỏ nhất thì
> mất rất nhiều hiệu quả. Tổng log nằm giữa: nó phạt rất nặng người dùng có tốc độ gần 0 nhưng vẫn thưởng cho việc tăng
> tổng. Trọng số w đẩy nhóm critical lên trước.
>
> Ngưỡng tốc độ tối thiểu của từng nhóm không phải ràng buộc cứng, vì khi quá tải thì không có nghiệm thỏa hết. Nhóm
> dùng ngưỡng đó để chấm chất lượng dịch vụ.

## Slide 9. Vì sao giải bằng heuristic (45 giây)

> Bài toán này khó giải chính xác: có biến nguyên, không lồi, các UAV ghép với nhau qua nhiễu, và mỗi khe chỉ có 0.25
> giây để quyết định. Vì vậy nhóm dùng heuristic, tức là thuật toán tìm nhanh một nghiệm đủ tốt, không đảm bảo tối ưu.
>
> Nhóm xin nói rõ: calib-ifair là **heuristic cải tiến**, các thành phần dựa trên kỹ thuật đã có như PF có trọng số,
> max-min có trọng số, k-means. Điểm cải tiến là cách kết hợp chúng và việc kiểm chứng ở mức gói tin.
>
> Mỗi khe, heuristic chia làm ba khối: liên kết và tính SINR, chia băng ifair, di chuyển calib, rồi áp quyết định xuống
> tầng MAC.

## Slide 10. Ý tưởng của calib-ifair trong một hình (50 giây)

> Trước khi vào công thức, nhóm xin tóm ý tưởng bằng ba hình. Thứ nhất, **nhìn đúng ai đang yếu**: một người đứng giữa
> hai UAV có thể ở gần UAV phục vụ, nhưng lại bị UAV kia gây nhiễu nặng. Thuật toán tính SINR có nhiễu, không chỉ nhìn
> khoảng cách.
>
> Thứ hai, **chia băng theo nhóm**: băng thông của mỗi UAV giống một chiếc bánh. Người critical có kênh xấu nhận miếng
> lớn nhất, để cuối cùng tốc độ của ba nhóm theo tỷ lệ 1 : 2 : 4.
>
> Thứ ba, **dịch UAV về chỗ có lợi**: UAV thử 17 hướng di chuyển nhỏ, chọn hướng làm hàm mục tiêu tăng nhiều nhất.
> Ba bước này lặp lại mỗi 0.25 giây, rồi phần băng được đưa xuống tầng MAC.

## Slide 11. Bài toán mỗi khe (Pₙ) (40 giây)

> Thay vì giải cả chu kỳ, heuristic giải tham lam từng khe. Tốc độ thật được thay bằng tốc độ dự đoán, tính theo đường
> cong LTE có nhiễu.
>
> Có thêm một điều kiện, chỉ áp khi tinh chỉnh vị trí: không nhận nước đi làm giảm số UAV đang có người dùng. Khi chưa
> có điều kiện này, thuật toán
> hay "tắt" một UAV để giảm nhiễu tức thời và rơi vào nghiệm kém: ở seed 1, tổng tốc độ chỉ còn 13 Mbps so với 43 Mbps.

## Slide 12. Lưu đồ calib-ifair (40 giây)

> Đây là toàn bộ luồng một khe, gồm sáu bước. Nối người dùng với UAV có kênh mạnh nhất. Tính SINR có nhiễu. Chia băng
> ifair theo trọng số. Với từng UAV, nếu còn xa tâm cụm thì bay thẳng tới. Nếu đã tới thì thử 17 nước đi và giữ nước
> tốt nhất. Cuối cùng gửi quyết định xuống tầng MAC.
>
> Mỗi khe chỉ tốn khoảng 5.5 mili giây với 3 UAV và 20 người dùng, rất nhỏ so với khe 250 mili giây.

## Slide 13. Khối 1: liên kết và SINR có nhiễu (40 giây)

> Khối đầu tiên nối người dùng với UAV có độ lợi kênh lớn nhất, rồi tính SINR có tính nhiễu từ mọi UAV đang phục vụ.
>
> Đây là điểm khác baseline. Baseline maxmin tính SNR không có nhiễu, nên một người đứng giữa hai UAV trông như kênh tốt
> nhưng thật ra bị nhiễu nặng. calib-ifair tính đúng nhiễu nên biết ai thật sự yếu để bù băng thông.

## Slide 14. Khối 2: chia băng ifair (50 giây)

> Công thức chia băng là b_k tỷ lệ với trọng số chia cho hiệu suất phổ. Kết quả là trong một UAV, tốc độ chia cho
> trọng số của mọi người bằng nhau: đây là max-min có trọng số. Khi kênh không quá yếu, người dùng critical nhanh gấp 4
> lần normal cùng UAV, kể cả khi kênh của họ xấu hơn.
>
> Có thể thầy cô sẽ hỏi: sao không dùng nghiệm đúng của tổng log? Nghiệm đúng chia băng tỷ lệ với trọng số, không phụ
> thuộc kênh, nên người critical ở rìa vẫn chậm. Nhóm cố ý chia để **tốc độ** tỷ lệ với trọng số; hàm tổng log chỉ dùng
> để chọn vị trí UAV.

## Slide 15. Khối 2: ví dụ số (60 giây)

> Để dễ hình dung, xét một UAV có ba người dùng. Normal có kênh tốt nhất, hiệu suất phổ 3. Critical có kênh xấu nhất, 1.
>
> Nếu chia đều, critical chỉ được 3.33 Mbps, chậm nhất. Nếu max-min không trọng số, ai cũng được 5.45 Mbps, critical
> không được ưu tiên. Với ifair, critical được 7.5 Mbps, important 3.75, normal 1.88, đúng tỷ lệ 1 : 2 : 4.
>
> Đổi lại, tổng tốc độ giảm từ 20 xuống 13 Mbps. Đây là đánh đổi có chủ đích, và có thể chỉnh bằng trọng số.

*Ghi chú: nói rõ đây là ví dụ minh họa, số do nhóm tự đặt, không phải số đo.*

## Slide 16. Khối 2: so sánh ba cách chia băng bằng biểu đồ (40 giây)

> Biểu đồ này vẽ lại ví dụ vừa rồi. Cột xám là chia đều: người normal kênh tốt nhanh nhất, critical chậm nhất. Cột xanh
> là max-min: ai cũng như nhau. Cột đỏ là ifair: critical cao nhất, đúng tỷ lệ 1 : 2 : 4. Tổng tốc độ giảm, đó là giá
> phải trả cho việc ưu tiên.

## Slide 17. Khối 3: di chuyển calib (75 giây)

> Khối thứ ba điều khiển vị trí UAV, gồm hai pha. Khi UAV còn xa tâm cụm người dùng, nó bay thẳng tới tâm cụm. Khi đã
> tới, nó thử 17 nước đi: đứng yên, hoặc 8 hướng với 2 cỡ bước 5 m và 1.25 m. Với mỗi nước đi, thuật toán tính lại hàm
> mục tiêu có nhiễu và trọng số, rồi giữ nước tốt nhất.
>
> Hàm mục tiêu U ở đây là tổng log tốc độ có trọng số. Lưu ý U chỉ là điểm để so sánh các vị trí với nhau, không phải
> throughput và không có đơn vị Mbps. Dùng log vì tăng thêm 1 Mbps cho người đang có 1 Mbps đáng giá hơn nhiều so với
> cho người đang có 10 Mbps, nên thuật toán tự ưu tiên người đang chậm.
>
> Pha tiếp cận dùng k-means, chỉ nhìn tọa độ người dùng, chưa biết ai là critical. Trọng số nhóm chỉ tác động từ pha tinh
> chỉnh trở đi.
>
> Các UAV được xét lần lượt, UAV sau thấy vị trí mới của UAV trước. Đây là cách tham lam: thử mọi tổ hợp thì cần 17 mũ M
> phép thử, nên thuật toán có thể bỏ lỡ những cách mà nhiều UAV phải cùng di chuyển mới tốt. Ở pha tinh chỉnh, nước đi
> làm giảm số UAV có người dùng bị loại.

## Slide 18. Thuật toán chạy thế nào (60 giây)

> Đây là mô phỏng thật trên cùng một kịch bản, hàng trên là kmeans-equal, hàng dưới là calib-ifair, ở các khe 0, 10 và
> 59. Hình thoi viền đỏ là người critical, dấu nhân là người chưa đạt chất lượng dịch vụ.
>
> Ở khe 0 hai thuật toán giống nhau. Tới khe 59, kmeans-equal chỉ có 1 trên 3 người critical đạt chất lượng. Với
> calib-ifair, UAV màu xanh dịch xuống giữa hai cụm người dùng và cả 3 người critical đều đạt, trong khi throughput tổng
> gần như bằng nhau, 30 so với 29 Mbps.

*Ghi chú: chỉ tay vào hình thoi đỏ ở góc dưới phải của hai hàng để hội đồng thấy khác biệt.*

## Slide 19. Áp quyết định ở tầng MAC và kiểm chứng ba tầng (60 giây)

> Một phát hiện quan trọng: nếu dùng scheduler PF mặc định của LTE, nó tự chia lại tài nguyên và quyết định chia băng
> của thuật toán mất tác dụng. Vì vậy nhóm viết thêm scheduler Weighted PF trong NS-3, nhận b_k làm trọng số.
>
> Cần nói rõ: b_k là trọng số ưu tiên của scheduler, không phải phần resource block cố định. Tỷ lệ resource block thực
> tế mỗi khe còn phụ thuộc lưu lượng, kênh, lịch sử PF và handover, nên không bằng đúng b_k.
>
> Để tin được số đo, nhóm kiểm chứng ba tầng: lý thuyết, NS-3 với liên kết lý tưởng, và NS-3 LTE đầy đủ. Lý thuyết khớp
> tầng giữa dưới 1% trên 105 lần chạy, nghĩa là mô hình đúng; chênh lệch còn lại là do giao thức LTE.

## Slide 20. Các thuật toán tham chiếu (45 giây)

> Nhóm so sánh với các baseline sau. Equal đứng yên hoặc bay về tâm cụm rồi chia đều băng, đại diện cho tối đa hiệu quả.
> Maxmin chia băng để mọi người có tốc độ bằng nhau, đại diện cho tối đa công bằng.
>
> Quan trọng nhất là kmeans-wmaxmin: max-min có trọng số nhóm, tức là baseline **cũng biết nhóm người dùng**. Như vậy so
> sánh là công bằng: cùng thông tin, chỉ khác phương pháp.
>
> Ngoài ra có hai bản để tách nguồn gốc lợi ích: bỏ trọng số nhóm, và thay LTE bằng Shannon.

## Slide 21. Cài đặt hệ thống (40 giây)

> Mô hình và thuật toán viết bằng Python. Mô phỏng mạng dùng NS-3 phiên bản 3.47 với module LTE. Quy trình đo gồm bốn
> bước: thuật toán ra quyết định, ghi thành kế hoạch, NS-3 phát lại kế hoạch với eNB bay thật, handover và lưu lượng UDP,
> rồi đo từng người dùng từng khe. Mỗi thí nghiệm lưu kèm cấu hình, chạy lại cho kết quả trùng.

## Slide 22. Thông số thí nghiệm (30 giây)

> Thông số chính: 3 UAV, 20 người dùng gồm 3 critical, 5 important, 12 normal; băng 10 MHz, công suất 1 W; mỗi lần chạy
> 60 khe; lưu lượng mỗi người từ 0.5 đến 4 Mbps; 3 seed, mọi thuật toán dùng cùng seed.

## Slide 23. Thiết lập thí nghiệm (20 giây)

> Slide này tóm tắt lại môi trường đo và bảng sáu thuật toán. Các chỉ số gồm throughput, tỷ lệ đạt chất lượng dịch vụ
> theo nhóm, độ trễ và tỉ lệ mất gói.

*Ghi chú: nếu thiếu thời gian, bỏ qua slide này vì đã nói ở slide 20–22.*

## Slide 24. Kết quả trên NS-3 LTE (50 giây)

> Đây là kết quả đo bằng NS-3 LTE. Biểu đồ đầu tiên là tỷ lệ người dùng critical đạt chất lượng dịch vụ. calib-ifair,
> đường đỏ đậm, giữ được 95 đến 100% ở mọi mức tải. Các baseline không biết nhóm tụt xuống 59 đến 69%. Max-min có trọng
> số, đường tím, dừng ở 86–87%.
>
> Biểu đồ cuối là throughput tổng: ở tải cao, calib-ifair thấp hơn các baseline không biết nhóm. Đây là cái giá nhóm sẽ
> nói ở phần sau.

## Slide 25. So sánh chi tiết (60 giây)

> Xem số cụ thể ở tải 2 và 4 Mbps mỗi người. So với max-min có trọng số, calib-ifair cho tỷ lệ critical đạt QoS 97% so
> với 87%; min throughput của critical cao hơn; và đặc biệt nhóm normal được đối xử tốt hơn hẳn, 0.95 so với 0.49 Mbps.
> Throughput tổng của hai thuật toán gần như bằng nhau.
>
> So với baseline không biết nhóm, ở 2 Mbps độ trễ của critical giảm từ hơn 1 giây xuống 41 mili giây.
>
> Nhóm cũng xin nói thẳng chỗ calib-ifair không thắng: ở tải 4 Mbps, độ trễ critical của max-min có trọng số thấp hơn
> một chút, 652 so với 720 mili giây; và throughput tổng thấp hơn baseline không biết nhóm khoảng 11%.

## Slide 26. Lợi ích đến từ đâu (50 giây)

> Để biết lợi ích đến từ đâu, nhóm bỏ từng yếu tố. Bỏ trọng số nhóm thì tỷ lệ critical đạt QoS rơi xuống 59%. Bỏ việc
> tính nhiễu và tinh chỉnh vị trí, tức là max-min có trọng số, còn 86%. Bỏ khối chia băng hay khối di chuyển đều làm kết
> quả kém đi.
>
> Có một phát hiện nhóm muốn nói trung thực: thay đường cong LTE bằng Shannon cho kết quả như nhau, chênh dưới 2%. Đường
> cong LTE giúp **dự đoán** số đo NS-3 rất tốt, nhưng **không** làm thuật toán tốt hơn. Lợi ích thật đến từ trọng số
> nhóm, tính nhiễu, tinh chỉnh vị trí và áp ở tầng MAC.

## Slide 27. Trạm điều khiển thời gian thực (40 giây)

> Ngoài thí nghiệm, nhóm xây một trạm điều khiển thời gian thực. Dashboard web hiển thị bản đồ, các chỉ số và bảng nhóm
> người dùng; có thể lái tay UAV, nhấp lên bản đồ để UAV bay tới, đổi 13 tham số khi đang chạy, và bấm "Ghi và đo" để
> chạy NS-3 ngay từ web. Gazebo hiển thị cùng kịch bản ở dạng 3D.

*Ghi chú: nếu có demo trực tiếp, chạy `python -m uavsim.live --gazebo`, chọn UAV 0, nhấp một góc bản đồ cho UAV bay đi,
chỉ cho hội đồng thấy người dùng đổi màu áo sang UAV khác và bảng nhóm user thay đổi.*

## Slide 28. Giao tiếp trình duyệt – server qua WebSocket (70 giây)

> Đây là phần lập trình mạng của trạm điều khiển. Server mở hai cổng, chỉ nghe trên máy cục bộ: cổng 8000 là HTTP để tải
> trang web, cổng 8001 là WebSocket. Nhóm chọn WebSocket thay cho HTTP polling vì server phải chủ động đẩy trạng thái
> bốn lần mỗi giây tới mọi trình duyệt, còn lệnh lái tay phải đi ngược lại với độ trễ thấp, trên cùng một kết nối TCP.
>
> Hình bên trái là trình tự: trình duyệt tải trang, bắt tay WebSocket, nhận bản tin info rồi state mỗi khe. Khi người
> dùng lái, trình duyệt gửi lệnh JSON như vel hay measure; server kiểm tra rồi phát info mới cho mọi trình duyệt. Có
> mười một loại lệnh. Server chạy trên một vòng lặp asyncio, còn NS-3 chạy ở thread riêng để mô phỏng không bị dừng. Lệnh
> sai chỉ bị từ chối, và khi mọi trình duyệt ngắt kết nối thì UAV lái tay tự dừng.
>
> Nhóm đo hiệu năng server với tới 50 trình duyệt cùng lúc: mỗi bản tin khoảng 1.7 kB, mỗi trình duyệt tốn 9.4 kB/s,
> lệnh đi và về dưới 3.5 ms, nhịp khe vẫn giữ 250 ms và server chỉ dùng 3.5% CPU.

## Slide 29. Các node và kết nối trong NS-3 (45 giây)

> Trong NS-3, mạng gồm bốn loại node. Một remote host làm nguồn dữ liệu, mở một socket UDP cho mỗi người dùng. Remote
> host nối với PGW của lõi EPC (gồm PGW, SGW, MME) bằng liên kết điểm-điểm 10 Gb/s, trễ 1 ms. Mỗi UAV là một eNB: phát 30 dBm,
> 50 resource block, ba eNB dùng chung tần số, bay theo đúng quỹ đạo thuật toán đã tính, và chạy scheduler WPF. Mỗi người
> dùng là một UE có ứng dụng UdpServer ở cổng 9 để đo độ trễ và mất gói. Các eNB nối với nhau qua giao diện X2 để
> handover khi kế hoạch đổi UAV phục vụ. Kênh vô tuyến dùng mô hình Al-Hourani do nhóm viết lại trong C++, cùng công thức
> với phía Python.

## Slide 30. Đường đi của gói tin trong NS-3 LTE (50 giây)

> Còn đây là đường đi của một gói dữ liệu trong NS-3. Remote host gửi UDP cổng 9, mỗi gói mang số thứ tự và thời điểm
> gửi để đo độ trễ từng gói. Gói đi qua EPC bằng đường hầm GTP-U tới eNB trên UAV, qua PDCP, RLC, rồi scheduler ở tầng
> MAC, chính là chỗ nhóm cài WPF để áp phần băng thông của thuật toán, rồi qua vô tuyến tới UE. Khi kế hoạch đổi UAV
> phục vụ, eNB làm handover qua giao diện X2.
>
> Bảng dưới tóm tắt bốn kênh truyền thông của hệ thống: WebSocket với trình duyệt, gz-transport với Gazebo, tiến trình
> con và file CSV với NS-3, và socket UDP bên trong NS-3.

*Ghi chú: nếu hội đồng hỏi vì sao gửi vị trí sang Gazebo bằng một lời gọi service: gom mọi vị trí vào một bản tin
protobuf giữ tải cố định 20 lời gọi mỗi giây, không phụ thuộc số UAV và user.*

## Slide 31. Đánh đổi và hạn chế (40 giây)

> Về đánh đổi: ở tải cao, throughput tổng thấp hơn baseline không biết nhóm khoảng 11%, và nhóm normal chịu độ trễ cao
> hơn, nhưng tốc độ tối thiểu của họ vẫn cao hơn mọi baseline. Mức đánh đổi chỉnh được bằng trọng số.
>
> Về hạn chế: đây là heuristic nên không đảm bảo tối ưu toàn cục; ngưỡng tốc độ tối thiểu chưa là ràng buộc cứng; công
> suất và độ cao chưa được tối ưu; nhóm mới đánh giá một cấu hình với 3 seed, và chưa có baseline tối ưu lồi.

## Slide 32. Kết luận (40 giây)

> Tóm lại, nhóm rút ra sáu kết luận đo trên NS-3. Mô hình hàng đợi đúng ở mức gói tin. Giá trị tốc độ theo Shannon lạc
> quan, NS-3 chỉ đạt 25–40%. Chia băng chỉ có tác dụng khi áp ở tầng MAC. calib-ifair ưu tiên được người dùng critical,
> 96–97% đạt chất lượng dịch vụ, và hơn cả max-min có trọng số cùng biết nhóm. Cuối cùng, dùng đường cong LTE thay Shannon
> không làm thuật toán tốt hơn.
>
> Hướng phát triển gồm ràng buộc cứng cho nhóm critical, baseline tối ưu lồi, mở rộng thí nghiệm và học tăng cường.

## Slide 33. Tài liệu tham khảo (10 giây)

> Đây là các tài liệu nhóm tham khảo chính.

## Slide 34. Cảm ơn (10 giây)

> Nhóm em xin cảm ơn thầy cô và các bạn đã lắng nghe. Nhóm rất mong nhận được câu hỏi và góp ý.

---

## Câu hỏi hội đồng có thể hỏi và gợi ý trả lời

**1. Đây có phải thuật toán mới không?**
Không phải thuật toán mới về nguyên lý. Đây là heuristic cải tiến: các thành phần (PF có trọng số, max-min có trọng
số, k-means, tìm kiếm cục bộ) đều đã có. Điểm cải tiến là kết hợp chia băng có tính nhiễu với tinh chỉnh vị trí theo
cùng mục tiêu có trọng số nhóm, áp ở tầng MAC, và kiểm chứng ở mức gói tin. Kết quả hơn baseline max-min có trọng số
cùng biết nhóm.

**2. Khác gì PF có trọng số trong LTE?**
PF có trọng số trong LTE chỉ là scheduler ở một trạm, không quyết định vị trí UAV và không biết nhiễu từ UAV khác.
calib-ifair quyết định cả vị trí UAV và phần băng của từng người dựa trên SINR có nhiễu; WPF chỉ là công cụ để áp phần
chia băng đó xuống tầng MAC.

**3. Kết quả cách nghiệm tối ưu bao xa?**
Chưa đo được, vì bài toán không lồi và chưa có baseline tối ưu lồi (BCD + SCA). Đây là hạn chế nhóm đã nêu.

**4. Vì sao không dùng nghiệm đúng của bài toán con chia băng?**
Nghiệm đúng của tổng log là băng tỷ lệ với trọng số, không phụ thuộc kênh, nên người critical ở rìa vẫn chậm. Nhóm chia
để tốc độ tỷ lệ với trọng số, ưu tiên người yếu hơn trong cùng nhóm.

**5. Vì sao throughput tổng giảm?**
Vì băng thông dồn cho người critical và người có kênh yếu. Đây là đánh đổi có chủ đích của mục tiêu công bằng có trọng
số; giảm trọng số critical thì throughput tổng tăng lại.

**6. Chỉ 3 seed và một cấu hình có đủ tin cậy không?**
Kết quả nhất quán trên cả 3 seed ở phần lớn chỉ số (có một seed hòa ở min throughput critical). Đây là hạn chế; mở
rộng lên 10–20 seed và nhiều cấu hình là việc tiếp theo.

**7. Tại sao dùng NS-3 mà không chỉ dùng công thức?**
Vì công thức Shannon lạc quan: NS-3 LTE chỉ đạt 25–40% con số Shannon, và quyết định chia băng không có tác dụng nếu
scheduler không áp nó. Môn Lập trình mạng yêu cầu kết quả ở mức gói tin: throughput, độ trễ, mất gói.

**8. Mô hình có đúng không, làm sao biết?**
Nhờ kiểm chứng ba tầng: lý thuyết khớp NS-3 liên kết lý tưởng dưới 1% trên 105 lần chạy, nên phần hàng đợi và độ trễ
của mô hình đúng; chênh lệch với LTE đã được giải thích bằng ba nguyên nhân.

**9. Hằng số 0.401 và 3.514 lấy từ đâu?**
Đo từ NS-3 bằng thí nghiệm một liên kết: quét công suất phát, ghi tốc độ thật, rồi khớp đường cong. 3.514 bit/s/Hz là
trần ứng với mã hóa điều chế cao nhất của LTE trong NS-3.

**10. Người dùng normal có bị bỏ rơi không?**
Không. Tốc độ tối thiểu của nhóm normal vẫn cao hơn mọi baseline (0.95 Mbps so với 0.49–0.76 Mbps ở 4 Mbps/user), chỉ
có độ trễ trung bình cao hơn.
