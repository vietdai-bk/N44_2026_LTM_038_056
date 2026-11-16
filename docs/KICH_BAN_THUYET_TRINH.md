# Kịch bản thuyết trình

Kịch bản đi theo bộ slide `slides/main.pdf` (32 trang). Tổng thời gian khoảng **22 phút**, cộng phần hỏi đáp. Mỗi slide
có: thời lượng gợi ý, lời nói (đọc tự nhiên, không cần thuộc từng chữ) và ghi chú cho người trình bày. Phần thuật toán
(slide 8–20) là trọng tâm, nên chiếm gần nửa thời gian.

| Phần | Slide | Thời gian |
|---|---|---|
| Mở đầu, bài toán | 1–7 | 5 phút |
| Heuristic calib-ifair | 8–20 | 10 phút |
| Thí nghiệm, kết quả | 21–27 | 5 phút |
| Hệ thống, tổng kết | 28–32 | 2 phút |

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

## Slide 7. Bài toán tối ưu (P) (50 giây)

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

## Slide 8. Vì sao giải bằng heuristic (45 giây)

> Bài toán này khó giải chính xác: có biến nguyên, không lồi, các UAV ghép với nhau qua nhiễu, và mỗi khe chỉ có 0.25
> giây để quyết định. Vì vậy nhóm dùng heuristic, tức là thuật toán tìm nhanh một nghiệm đủ tốt, không đảm bảo tối ưu.
>
> Nhóm xin nói rõ: calib-ifair là **heuristic cải tiến**, các thành phần dựa trên kỹ thuật đã có như PF có trọng số,
> max-min có trọng số, k-means. Điểm cải tiến là cách kết hợp chúng và việc kiểm chứng ở mức gói tin.
>
> Mỗi khe, heuristic chia làm ba khối: liên kết và tính SINR, chia băng ifair, di chuyển calib, rồi áp quyết định xuống
> tầng MAC.

## Slide 9. Ý tưởng của calib-ifair trong một hình (50 giây)

> Trước khi vào công thức, nhóm xin tóm ý tưởng bằng ba hình. Thứ nhất, **nhìn đúng ai đang yếu**: một người đứng giữa
> hai UAV có thể ở gần UAV phục vụ, nhưng lại bị UAV kia gây nhiễu nặng. Thuật toán tính SINR có nhiễu, không chỉ nhìn
> khoảng cách.
>
> Thứ hai, **chia băng theo nhóm**: băng thông của mỗi UAV giống một chiếc bánh. Người critical có kênh xấu nhận miếng
> lớn nhất, để cuối cùng tốc độ của ba nhóm theo tỷ lệ 1 : 2 : 4.
>
> Thứ ba, **dịch UAV về chỗ có lợi**: UAV thử 17 hướng di chuyển nhỏ, chọn hướng làm hàm mục tiêu tăng nhiều nhất.
> Ba bước này lặp lại mỗi 0.25 giây, rồi phần băng được đưa xuống tầng MAC.

## Slide 10. Bài toán mỗi khe (Pₙ) (40 giây)

> Thay vì giải cả chu kỳ, heuristic giải tham lam từng khe. Tốc độ thật được thay bằng tốc độ dự đoán, tính theo đường
> cong LTE có nhiễu.
>
> Có thêm một ràng buộc thực tế: không nhận nước đi làm một UAV mất hết người dùng. Khi chưa có ràng buộc này, thuật toán
> hay "tắt" một UAV để giảm nhiễu tức thời và rơi vào nghiệm kém: ở seed 1, tổng tốc độ chỉ còn 13 Mbps so với 43 Mbps.

## Slide 11. Lưu đồ calib-ifair (40 giây)

> Đây là toàn bộ luồng một khe, gồm sáu bước. Nối người dùng với UAV có kênh mạnh nhất. Tính SINR có nhiễu. Chia băng
> ifair theo trọng số. Với từng UAV, nếu còn xa tâm cụm thì bay thẳng tới. Nếu đã tới thì thử 17 nước đi và giữ nước
> tốt nhất. Cuối cùng gửi quyết định xuống tầng MAC.
>
> Mỗi khe chỉ tốn khoảng 5.5 mili giây với 3 UAV và 20 người dùng, rất nhỏ so với khe 250 mili giây.

## Slide 12. Khối 1: liên kết và SINR có nhiễu (40 giây)

> Khối đầu tiên nối người dùng với UAV có độ lợi kênh lớn nhất, rồi tính SINR có tính nhiễu từ mọi UAV đang phục vụ.
>
> Đây là điểm khác baseline. Baseline maxmin tính SNR không có nhiễu, nên một người đứng giữa hai UAV trông như kênh tốt
> nhưng thật ra bị nhiễu nặng. calib-ifair tính đúng nhiễu nên biết ai thật sự yếu để bù băng thông.

## Slide 13. Khối 2: chia băng ifair (50 giây)

> Công thức chia băng là b_k tỷ lệ với trọng số chia cho hiệu suất phổ. Kết quả là trong một UAV, tốc độ chia cho
> trọng số của mọi người bằng nhau: đây là max-min có trọng số. Người dùng critical luôn nhanh gấp 4 lần normal cùng
> UAV, kể cả khi kênh của họ xấu hơn.
>
> Có thể thầy cô sẽ hỏi: sao không dùng nghiệm đúng của tổng log? Nghiệm đúng chia băng tỷ lệ với trọng số, không phụ
> thuộc kênh, nên người critical ở rìa vẫn chậm. Nhóm cố ý chia để **tốc độ** tỷ lệ với trọng số; hàm tổng log chỉ dùng
> để chọn vị trí UAV.

## Slide 14. Khối 2: ví dụ số (60 giây)

> Để dễ hình dung, xét một UAV có ba người dùng. Normal có kênh tốt nhất, hiệu suất phổ 3. Critical có kênh xấu nhất, 1.
>
> Nếu chia đều, critical chỉ được 3.33 Mbps, chậm nhất. Nếu max-min không trọng số, ai cũng được 5.45 Mbps, critical
> không được ưu tiên. Với ifair, critical được 7.5 Mbps, important 3.75, normal 1.88, đúng tỷ lệ 1 : 2 : 4.
>
> Đổi lại, tổng tốc độ giảm từ 20 xuống 13 Mbps. Đây là đánh đổi có chủ đích, và có thể chỉnh bằng trọng số.

*Ghi chú: nói rõ đây là ví dụ minh họa, số do nhóm tự đặt, không phải số đo.*

## Slide 15. Khối 2: so sánh ba cách chia băng bằng biểu đồ (40 giây)

> Biểu đồ này vẽ lại ví dụ vừa rồi. Cột xám là chia đều: người normal kênh tốt nhanh nhất, critical chậm nhất. Cột xanh
> là max-min: ai cũng như nhau. Cột đỏ là ifair: critical cao nhất, đúng tỷ lệ 1 : 2 : 4. Tổng tốc độ giảm, đó là giá
> phải trả cho việc ưu tiên.

## Slide 16. Khối 3: di chuyển calib (50 giây)

> Khối thứ ba điều khiển vị trí UAV, gồm hai pha. Khi UAV còn xa tâm cụm người dùng, nó bay thẳng tới tâm cụm. Khi đã
> tới, nó thử 17 nước đi: đứng yên, hoặc 8 hướng với 2 cỡ bước 5 m và 1.25 m. Với mỗi nước đi, thuật toán tính lại hàm
> mục tiêu có nhiễu và trọng số, rồi giữ nước tốt nhất.
>
> Các UAV được xét lần lượt, UAV sau thấy vị trí mới của UAV trước. Nước đi nào làm một UAV mất hết người dùng thì bị
> loại.

## Slide 17. Thuật toán chạy thế nào (60 giây)

> Đây là mô phỏng thật trên cùng một kịch bản, hàng trên là kmeans-equal, hàng dưới là calib-ifair, ở các khe 0, 10 và
> 59. Hình thoi viền đỏ là người critical, dấu nhân là người chưa đạt chất lượng dịch vụ.
>
> Ở khe 0 hai thuật toán giống nhau. Tới khe 59, kmeans-equal chỉ có 1 trên 3 người critical đạt chất lượng. Với
> calib-ifair, UAV màu xanh dịch xuống giữa hai cụm người dùng và cả 3 người critical đều đạt, trong khi throughput tổng
> gần như bằng nhau, 30 so với 29 Mbps.

*Ghi chú: chỉ tay vào hình thoi đỏ ở góc dưới phải của hai hàng để hội đồng thấy khác biệt.*

## Slide 18. Mã giả (1/2) (40 giây)

> Đây là hai hàm hỗ trợ. Hàm thứ nhất tính hiệu suất phổ dự đoán: tính độ lợi kênh, liên kết, rồi SINR có nhiễu. UAV
> không có người dùng thì không phát, nên không gây nhiễu. Hàm thứ hai tính tiện ích U: với cách chia ifair, tốc độ dự
> đoán của mỗi người là B nhân trọng số chia cho tải của UAV.

## Slide 19. Mã giả (2/2) (40 giây)

> Đây là thủ tục một khe. Đầu tiên gán trọng số theo nhóm, tính SINR, chia băng ifair. Sau đó chạy k-means, và với từng
> UAV, hoặc bay về tâm cụm, hoặc thử 16 nước đi quanh vị trí hiện tại. Điều kiện chấp nhận là tiện ích tăng và số UAV có
> người dùng không giảm.
>
> Độ phức tạp mỗi khe là bậc M bình phương nhân K, đủ nhanh để chạy thời gian thực.

## Slide 20. Áp quyết định ở tầng MAC và kiểm chứng ba tầng (50 giây)

> Một phát hiện quan trọng: nếu dùng scheduler PF mặc định của LTE, nó tự chia lại tài nguyên và quyết định chia băng
> của thuật toán mất tác dụng. Vì vậy nhóm viết thêm scheduler Weighted PF trong NS-3, nhận b_k làm trọng số.
>
> Để tin được số đo, nhóm kiểm chứng ba tầng: lý thuyết, NS-3 với liên kết lý tưởng, và NS-3 LTE đầy đủ. Lý thuyết khớp
> tầng giữa dưới 1% trên 105 lần chạy, nghĩa là mô hình đúng; chênh lệch còn lại là do giao thức LTE.

## Slide 21. Các thuật toán tham chiếu (45 giây)

> Nhóm so sánh với các baseline sau. Equal đứng yên hoặc bay về tâm cụm rồi chia đều băng, đại diện cho tối đa hiệu quả.
> Maxmin chia băng để mọi người có tốc độ bằng nhau, đại diện cho tối đa công bằng.
>
> Quan trọng nhất là kmeans-wmaxmin: max-min có trọng số nhóm, tức là baseline **cũng biết nhóm người dùng**. Như vậy so
> sánh là công bằng: cùng thông tin, chỉ khác phương pháp.
>
> Ngoài ra có hai bản để tách nguồn gốc lợi ích: bỏ trọng số nhóm, và thay LTE bằng Shannon.

## Slide 22. Cài đặt hệ thống (40 giây)

> Mô hình và thuật toán viết bằng Python. Mô phỏng mạng dùng NS-3 phiên bản 3.47 với module LTE. Quy trình đo gồm bốn
> bước: thuật toán ra quyết định, ghi thành kế hoạch, NS-3 phát lại kế hoạch với eNB bay thật, handover và lưu lượng UDP,
> rồi đo từng người dùng từng khe. Mỗi thí nghiệm lưu kèm cấu hình, chạy lại cho kết quả trùng.

## Slide 23. Thông số thí nghiệm (30 giây)

> Thông số chính: 3 UAV, 20 người dùng gồm 3 critical, 5 important, 12 normal; băng 10 MHz, công suất 1 W; mỗi lần chạy
> 60 khe; lưu lượng mỗi người từ 0.5 đến 4 Mbps; 3 seed, mọi thuật toán dùng cùng seed.

## Slide 24. Thiết lập thí nghiệm (20 giây)

> Slide này tóm tắt lại môi trường đo và bảng sáu thuật toán. Các chỉ số gồm throughput, tỷ lệ đạt chất lượng dịch vụ
> theo nhóm, độ trễ và tỉ lệ mất gói.

*Ghi chú: nếu thiếu thời gian, bỏ qua slide này vì đã nói ở slide 21–23.*

## Slide 25. Kết quả trên NS-3 LTE (50 giây)

> Đây là kết quả đo bằng NS-3 LTE. Biểu đồ đầu tiên là tỷ lệ người dùng critical đạt chất lượng dịch vụ. calib-ifair,
> đường đỏ đậm, giữ được 95 đến 100% ở mọi mức tải. Các baseline không biết nhóm tụt xuống 59 đến 69%. Max-min có trọng
> số, đường tím, dừng ở 86–87%.
>
> Biểu đồ cuối là throughput tổng: ở tải cao, calib-ifair thấp hơn các baseline không biết nhóm. Đây là cái giá nhóm sẽ
> nói ở phần sau.

## Slide 26. So sánh chi tiết (60 giây)

> Xem số cụ thể ở tải 2 và 4 Mbps mỗi người. So với max-min có trọng số, calib-ifair cho tỷ lệ critical đạt QoS 97% so
> với 87%; min throughput của critical cao hơn; và đặc biệt nhóm normal được đối xử tốt hơn hẳn, 0.95 so với 0.49 Mbps.
> Throughput tổng của hai thuật toán gần như bằng nhau.
>
> So với baseline không biết nhóm, ở 2 Mbps độ trễ của critical giảm từ hơn 1 giây xuống 41 mili giây.
>
> Nhóm cũng xin nói thẳng chỗ calib-ifair không thắng: ở tải 4 Mbps, độ trễ critical của max-min có trọng số thấp hơn
> một chút, 652 so với 720 mili giây; và throughput tổng thấp hơn baseline không biết nhóm khoảng 11%.

## Slide 27. Lợi ích đến từ đâu (50 giây)

> Để biết lợi ích đến từ đâu, nhóm bỏ từng yếu tố. Bỏ trọng số nhóm thì tỷ lệ critical đạt QoS rơi xuống 59%. Bỏ việc
> tính nhiễu và tinh chỉnh vị trí, tức là max-min có trọng số, còn 86%. Bỏ khối chia băng hay khối di chuyển đều làm kết
> quả kém đi.
>
> Có một phát hiện nhóm muốn nói trung thực: thay đường cong LTE bằng Shannon cho kết quả như nhau, chênh dưới 2%. Đường
> cong LTE giúp **dự đoán** số đo NS-3 rất tốt, nhưng **không** làm thuật toán tốt hơn. Lợi ích thật đến từ trọng số
> nhóm, tính nhiễu, tinh chỉnh vị trí và áp ở tầng MAC.

## Slide 28. Trạm điều khiển thời gian thực (40 giây)

> Ngoài thí nghiệm, nhóm xây một trạm điều khiển thời gian thực. Dashboard web hiển thị bản đồ, các chỉ số và bảng nhóm
> người dùng; có thể lái tay UAV, nhấp lên bản đồ để UAV bay tới, đổi 13 tham số khi đang chạy, và bấm "Ghi và đo" để
> chạy NS-3 ngay từ web. Gazebo hiển thị cùng kịch bản ở dạng 3D.

*Ghi chú: nếu có demo trực tiếp, chạy `python -m uavsim.live --gazebo`, chọn UAV 0, nhấp một góc bản đồ cho UAV bay đi,
chỉ cho hội đồng thấy người dùng đổi màu áo sang UAV khác và bảng nhóm user thay đổi.*

## Slide 29. Đánh đổi và hạn chế (40 giây)

> Về đánh đổi: ở tải cao, throughput tổng thấp hơn baseline không biết nhóm khoảng 11%, và nhóm normal chịu độ trễ cao
> hơn, nhưng tốc độ tối thiểu của họ vẫn cao hơn mọi baseline. Mức đánh đổi chỉnh được bằng trọng số.
>
> Về hạn chế: đây là heuristic nên không đảm bảo tối ưu toàn cục; ngưỡng tốc độ tối thiểu chưa là ràng buộc cứng; công
> suất và độ cao chưa được tối ưu; nhóm mới đánh giá một cấu hình với 3 seed, và chưa có baseline tối ưu lồi.

## Slide 30. Kết luận (40 giây)

> Tóm lại, nhóm rút ra sáu kết luận đo trên NS-3. Mô hình hàng đợi đúng ở mức gói tin. Giá trị tốc độ theo Shannon lạc
> quan, NS-3 chỉ đạt 25–40%. Chia băng chỉ có tác dụng khi áp ở tầng MAC. calib-ifair ưu tiên được người dùng critical,
> 96–97% đạt chất lượng dịch vụ, và hơn cả max-min có trọng số cùng biết nhóm. Cuối cùng, dùng đường cong LTE thay Shannon
> không làm thuật toán tốt hơn.
>
> Hướng phát triển gồm ràng buộc cứng cho nhóm critical, baseline tối ưu lồi, mở rộng thí nghiệm và học tăng cường.

## Slide 31. Tài liệu tham khảo (10 giây)

> Đây là các tài liệu nhóm tham khảo chính.

## Slide 32. Cảm ơn (10 giây)

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
