# X3 UAV — nguồn của quadcopter.sdf

Mẫu `~/simulation/multi_uav/worlds/quadcopter.sdf` tham chiếu X3 UAV phiên bản 4 của OpenRobotics:
https://fuel.gazebosim.org/1.0/OpenRobotics/models/X3%20UAV/4

Các file trong thư mục này được sao chép từ bản cache Fuel có sẵn trên máy. `model.config` giữ thông tin tác giả Carlos Aguero và Cole Biesemeyer; `source_model.sdf` giữ mô tả gốc. Chỉ đóng gói các mesh/texture được sử dụng: `x3.dae`, `x3.png`, `propeller_cw.dae`, `propeller_ccw.dae`.

`gazebo._uav()` lấy năm visual từ mô tả gốc, giữ texture thân, đổi màu vật liệu cánh để nhận diện UAV và chuyển URI mesh sang file cục bộ. Visual được phóng đại 8 lần để quan sát trên bản đồ tỷ lệ 1:10. Các offset rotor cũng được phóng đại tương ứng.

Đây là phần hiển thị của mẫu quadcopter, không bật plugin MulticopterMotorModel, joint động hoặc collision của bản demo. Vị trí tiếp tục nhận từ thuật toán Python qua `set_pose_vector`. Gộp visual vào một link giúp tránh tăng chi phí động lực học và không cần truy cập Fuel lúc chạy.
