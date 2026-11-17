# Tài nguyên hiển thị Gazebo

- **UAV:** model [X500 với camera FPV](x500_fpv_cam/README.md), dùng bản mesh rút gọn (LOD) trong `x500/meshes/lod/`:
  35.972 tam giác mỗi UAV thay vì 251.556. Bốn rotor quay bằng joint controller, không tạo lực nâng. Màu cánh trùng màu
  UAV trên dashboard.
- **Người dùng:** dựng bằng hình học SDF trong `uavsim/gazebo.py`; áo mang màu UAV đang phục vụ, đỏ khi không được phục vụ.
- **Vành nhóm:** `priority_ring.dae` là vành phẳng tự dựng (bán kính ngoài 1 m, trong 0.86 m, 96 tam giác).
  `gazebo._ring()` co giãn theo nhóm và gán màu: vàng cho important, đỏ cho critical, normal không có vành.

Kích thước hiển thị được phóng đại để dễ quan sát trên bản đồ tỷ lệ 1:10; vị trí vẫn đúng tỷ lệ. Gazebo chỉ hiển thị,
không có va chạm và không ảnh hưởng mô hình kênh hay số liệu. Ảnh: [toàn cảnh](../../../docs/figures/gazebo.png),
[cận cảnh](../../../docs/figures/gazebo_x500_closeup.png).

## Hiệu năng

Bản live chỉ dựng bể model theo số UAV và user ban đầu, và dùng service `create_multiple` để bổ sung khi tăng cấu
hình. Vị trí user không đổi thì không gửi lại ở mỗi lần nội suy; trạng thái chỉ được ghi nhận sau khi service xác nhận
thành công. Với 3 UAV, 20 user, world giảm từ 669 model (6.881 visual) xuống 129 model (1.281 visual).

Đo bằng camera offscreen Ogre2 (1280×960, 30 Hz, 10 giây): bể đầy đủ đạt RTF 0.648 và 19.78 ảnh/giây; bể theo cấu
hình đạt RTF 1.001 và 30.67 ảnh/giây; thời gian tới ảnh đầu tiên giảm từ 23.76 xuống 4.79 giây. Số liệu ở
`experiments/results/gazebo_performance.json`. Với X500 ở cấu hình mặc định (1.137 visual), cửa sổ GUI thật trên
RTX 3050 đạt RTF 0.992, nhịp state trung bình 0.251 s. Đây là số đo một phiên trên máy phát triển, không phải cam kết
cho mọi máy.

## Camera và GPU

Camera đặt tâm theo khung bao user lúc khởi động; có thể orbit, zoom, pan bằng chuột. Driver NVIDIA được chọn tự động
khi có; xem tùy chọn `UAVSIM_GZ_GPU` trong [README X500](x500_fpv_cam/README.md).
