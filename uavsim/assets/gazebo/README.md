# Tài nguyên hiển thị Gazebo

`priority_ring.dae` là mesh vành phẳng tự dựng, trục Z hướng lên, bán kính ngoài 1 m và bán kính trong 0.86 m, gồm 48 đoạn (96 tam giác). `gazebo._ring()` co giãn mesh theo nhóm user và gán màu từ SDF. Không cần tải tài nguyên từ mạng.

UAV dùng model [X500 với camera FPV](x500_fpv_cam/README.md) do người dùng cung cấp; người được dựng bằng hình học SDF trong `uavsim/gazebo.py`. Áo người và cánh UAV dùng màu liên kết giống dashboard; vành vàng chỉ nhóm important, vành đỏ chỉ nhóm critical. Kích thước hiển thị được phóng đại để dễ quan sát, không tham gia mô hình kênh hoặc động lực học. Không có collision mới.

Ảnh render kiểm tra bằng camera Gazebo Ogre2:

- [Cận cảnh](../../../docs/figures/gazebo_models_detail.png): một UAV và ba user minh họa ba nhóm, bố trí riêng để nhìn rõ hình học.
- [Toàn cảnh](../../../docs/figures/gazebo_models_overview.png): cấu hình 3 UAV, 20 user, seed 1, sau 20 khe calib-ifair; render cả bể model dựng sẵn.

Khởi động lại `python -m uavsim.live --gazebo` để dựng world bằng hình học mới. Không cần build lại NS-3.

## Hiệu năng

Bản live chỉ dựng bể theo số UAV/user ban đầu và dùng service `create_multiple` để bổ sung khi tăng cấu hình. Tên model và cơ chế đổi màu áo được giữ nguyên. Các vị trí user không đổi sẽ không gửi lại ở mỗi lần nội suy; trạng thái chỉ được ghi nhận sau khi service xác nhận thành công.

Với 3 UAV/20 user, world giảm từ 669 model, 6.881 visual xuống 129 model, 1.281 visual. Số này không bao gồm các model lồng trong bối cảnh tĩnh.

Phép đo đối chiếu trên máy phát triển: Ogre2 headless, camera 1280×960 yêu cầu 30 Hz, lấy mẫu 10 giây sau ảnh đầu tiên. Bể đầy đủ đạt RTF 0.648 và 19.78 ảnh/giây; bể theo cấu hình đạt RTF 1.001 và 30.67 ảnh/giây. Thời gian tới ảnh đầu tiên lần lượt 23.76 và 4.79 giây. Đây là số đo camera offscreen trong một lần chạy mỗi cấu hình, không phải FPS của cửa sổ GUI hoặc cam kết trên mọi máy. Các model có cùng hình học và cùng trạng thái trong hai phép đo. Kết quả lưu ở `experiments/results/gazebo_performance.json`.

## Camera gần cụm user

Camera mặc định cách điểm nhìn 60 m theo phương ngang, cao 50 m, góc chúc 0.66 rad. Bản live đặt tâm camera theo khung bao user lúc khởi động, thiên về phía gần để tránh cắt mép dưới; không tự lùi ra để bao hết hàng rào hoặc UAV ở xa. Có thể tiếp tục dùng chuột orbit/zoom/pan trong Gazebo.

Ảnh mới dùng X3 và camera gần: [toàn cảnh vùng hoạt động](../../../docs/figures/gazebo_x3_close.png), [cận cảnh model](../../../docs/figures/gazebo_x3_detail.png). Các ảnh `gazebo_models_*` phía trên ghi lại phiên bản hình học tự dựng trước X3; số đo hiệu năng phía trên cũng thuộc phiên bản đó.

Với mẫu X3 và camera gần, world mặc định còn 1.041 visual. Phép đo camera offscreen cùng phương pháp đạt 30.57 ảnh/giây và RTF 1.000; thời gian tới ảnh đầu tiên 4.32 giây. Camera đã đổi góc nên đây là kiểm tra tải của phiên bản mới, không phải phép so sánh GPU cô lập chỉ riêng mesh.

Phiên bản hiện tại dùng X500 FPV và lùi camera khoảng 15% so với góc X3 gần. Ảnh X3 và các số đo phía trên là của phiên bản trước.

Ảnh X500 FPV: [góc tổng thể mới](../../../docs/figures/gazebo_x500_wide.png), [cận cảnh](../../../docs/figures/gazebo_x500_detail.png). Phiên bản X500 có 1.137 visual ở cấu hình mặc định; phép đo offscreen đạt 30.67 ảnh/giây, RTF 1.001.

## X500 LOD với rotor quay (phiên bản hiện tại)

Thân/motor/cánh dùng bản LOD từ model X500 gốc, tổng 35.972 thay vì 251.556 tam giác/UAV. Có bốn rotor quay bằng joint controller, không tạo lực nâng. Nguồn và cách tái tạo mesh nằm ở [README X500](x500_fpv_cam/README.md).

Kiểm tra **cửa sổ GUI thật** trên RTX 3050: lấy mẫu khoảng 25 giây, RTF 0.992, nhịp state trung bình 0.251 s (lớn nhất 0.272 s), cả 3 UAV có góc rotor thay đổi liên tục. Kiểm thử native riêng xác nhận tăng/giảm 2 → 1 → 3 UAV thì số UAV quay rotor tương ứng 2 → 1 → 3. Đây là số đo một phiên trên máy phát triển, không phải cam kết FPS hoặc độ ổn định cho mọi máy.

Cảnh GUI dùng đường dẫn tài nguyên tuyệt đối và log được giữ trong thư mục world. Driver NVIDIA được chọn tự động khi có; xem tùy chọn `UAVSIM_GZ_GPU` trong README X500. Thuật toán mạng và bước NS-3 không thay đổi.
