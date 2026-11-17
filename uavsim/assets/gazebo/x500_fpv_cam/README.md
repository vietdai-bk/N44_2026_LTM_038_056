# X500 với camera FPV

Nguồn người dùng cung cấp: `~/Downloads/x500_fpv_cam/model.sdf`, tác giả Rajan Gupta (xem `model.config`). Model ghép hai thành phần có sẵn trong cache Fuel:

- PX4 X500 phiên bản 3, tác giả Benjamin Perseghetti: `https://fuel.gazebosim.org/1.0/PX4/models/x500/3`.
- FPV Camera phiên bản 1, tác giả Rajan Gupta: `https://fuel.gazebosim.org/1.0/rg28/models/FPV%20Camera/1`.

Giữ bản SDF và metadata nguồn tại thư mục gốc, `x500/`, `fpv_camera/`. Mesh và texture được sao chép cục bộ, không sửa file trong Downloads hay cache Fuel.

`visual_model.sdf` là bản dành cho hiển thị: ghép 17 visual vào một template và quy đổi pose của include/link/visual về gốc `base_link` của X500. Pose của camera FPV có phép quay theo file nguồn. Thân, motor và texture carbon được giữ nguyên; cánh dùng màu nhận diện UAV. `gazebo._uav()` đổi URI `asset://` sang đường dẫn cục bộ và phóng đại hình học 8 lần để dễ quan sát trên bản đồ tỷ lệ 1:10.

Không chạy cảm biến FPV 640×640/30 Hz, IMU hay lực nâng của MulticopterMotorModel: model hiển thị quỹ đạo do Python quyết định, không thêm camera render cho từng UAV. Runtime tách bốn rotor thành link với joint quay và JointController (±15 rad/s để mắt nhìn rõ). Cặp 0/1 và 2/3 quay ngược chiều; UAV đang cất dưới đất dừng rotor. Lệnh tăng/giảm số UAV được thử lại sau khi transport discovery đã nối subscriber.

## LOD và GPU

Runtime dùng `x500/meshes/lod/` khi có. Các bản gốc không thay đổi. Tổng mesh một UAV giảm từ 251.556 xuống 35.972 tam giác (~86%): thân giữ 21.472/179.000 tam giác, các motor/cánh cũng được giảm. UV và ranh giới vật liệu thân/motor được giữ; vẫn dùng texture carbon gốc. `lod/stats.json` lưu số tam giác trước/sau.

Để tái tạo LOD bằng Blender 4.2 (không cần Blender lúc chạy):

```bash
blender -b --factory-startup --python uavsim/assets/gazebo/x500_fpv_cam/build_lod.py
```

Gazebo dùng bước vật lý hiển thị 0.01 s (100 Hz); đây không phải bước mô phỏng mạng và không đổi số liệu Python/NS-3. Các rotor không có collision và không tạo lực bay. `gazebo.launch()` tự chọn PRIME offload NVIDIA khi phát hiện driver/GPU, giữ biến môi trường mà người dùng đã đặt. Có thể đặt `UAVSIM_GZ_GPU=system` để không tự thêm cấu hình offload; `UAVSIM_GZ_GPU=nvidia` yêu cầu offload. Lỗi driver/resource được giữ trong `experiments/results/gazebo/gazebo.log`.

Bối cảnh được viết sang URI file tuyệt đối trong bản sao để GUI và server đều tìm đúng mesh/texture, tránh cảnh thiếu đường/mái nhà hoặc tìm tài nguyên lặp lại. Không sửa bãi gốc.
