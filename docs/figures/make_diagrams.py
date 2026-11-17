"""Sinh các sơ đồ .drawio (mxGraph XML) cho báo cáo và slide. Chạy: python docs/figures/make_diagrams.py docs/figures."""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

NAVY, BLUE, ORANGE, GREEN, RED, AMBER, GREY = "#1a4d8f", "#2a78d6", "#eb6834", "#1baf7a", "#d01010", "#eda100", "#7d8795"
FONT = "fontFamily=Helvetica;fontSize=13;"


class D:
    def __init__(self, name, w=1100, h=620):
        self.name, self.cells, self.n, self.w, self.h = name, [], 2, w, h

    def _id(self):
        self.n += 1
        return f"c{self.n}"

    def box(self, x, y, w, h, text, fill="#ffffff", stroke="#aeb6c2", style="rounded=1;arcSize=6;", font=FONT, bold=False):
        i = self._id()
        st = f"{style}whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};{font}" + ("fontStyle=1;" if bold else "")
        self.cells.append(f'<mxCell id="{i}" value="{escape(text, {chr(34): "&quot;"})}" style="{st}" vertex="1" parent="1">'
                          f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return i

    def text(self, x, y, w, h, text, size=13, color="#14181f", bold=False, align="center"):
        return self.box(x, y, w, h, text, fill="none", stroke="none",
                        style=f"text;align={align};verticalAlign=middle;", font=f"fontFamily=Helvetica;fontSize={size};fontColor={color};",
                        bold=bold)

    def edge(self, a, b, text="", color="#4d5766", dashed=False, width=1.5, arrow="block", both=False, exit=None, entry=None,
             points=None, straight=False):
        i = self._id()
        st = (("" if straight else "edgeStyle=orthogonalEdgeStyle;") + f"rounded=1;html=1;strokeColor={color};strokeWidth={width};endArrow={arrow};"
              f"fontFamily=Helvetica;fontSize=12;fontColor=#14181f;labelBackgroundColor=#ffffff;"
              + ("dashed=1;" if dashed else "") + ("startArrow=block;" if both else ""))
        if exit:
            st += f"exitX={exit[0]};exitY={exit[1]};exitDx=0;exitDy=0;"
        if entry:
            st += f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;"
        self.cells.append(f'<mxCell id="{i}" value="{escape(text, {chr(34): "&quot;"})}" style="{st}" edge="1" parent="1" '
                          f'source="{a}" target="{b}"><mxGeometry relative="1" as="geometry">'
                          + ('<Array as="points">' + "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in points) + "</Array>"
                             if points else "") + '</mxGeometry></mxCell>')
        return i

    def save(self):
        body = "".join(self.cells)
        xml = (f'<mxfile host="drawio"><diagram name="{self.name}" id="{self.name}"><mxGraphModel dx="{self.w}" dy="{self.h}" '
               f'grid="1" gridSize="10" guides="1" page="1" pageWidth="{self.w}" pageHeight="{self.h}" background="#ffffff">'
               f'<root><mxCell id="0"/><mxCell id="1" parent="0"/>{body}</root></mxGraphModel></diagram></mxfile>')
        (OUT / f"{self.name}.drawio").write_text(xml)


# 1. Kịch bản -------------------------------------------------------------------------------------------------------
d = D("kich_ban", 1100, 600)
d.text(0, 5, 1100, 30, "Kịch bản: M UAV làm trạm gốc bay, phục vụ K user mặt đất thuộc ba nhóm ưu tiên", 17, bold=True)
uav = {}
for j, (x, c) in enumerate([(170, BLUE), (500, ORANGE), (830, GREEN)]):
    uav[j] = d.box(x, 70, 110, 60, f"UAV {j}<br><font style='font-size:11px'>eNB, độ cao H</font>", fill=c, stroke="#14181f",
                   style="shape=hexagon;perimeter=hexagonPerimeter2;size=0.18;", font="fontFamily=Helvetica;fontSize=13;fontColor=#ffffff;", bold=True)
users = [(120, 330, 0, 0), (200, 390, 0, 2), (290, 340, 0, 1), (430, 380, 1, 0), (520, 330, 1, 0), (600, 400, 1, 2),
         (760, 340, 2, 0), (840, 400, 2, 1), (930, 350, 2, 0), (1000, 420, 2, 0)]
shape = {0: "ellipse;", 1: "rounded=0;", 2: "rhombus;"}
cname = {0: "normal", 1: "important", 2: "critical"}
col = {0: BLUE, 1: ORANGE, 2: GREEN}
ucell = {}
for k, (x, y, j, c) in enumerate(users):
    u = ucell[k] = d.box(x, y, 34, 34, "", fill=col[j], stroke=RED if c == 2 else "#14181f", style=shape[c] + ("strokeWidth=3;" if c == 2 else ""))
    d.edge(uav[j], u, color=col[j], arrow="none", width=1.2, exit=(0.5, 1), entry=(0.5, 0))
d.edge(uav[0], ucell[5], "", color=RED, dashed=True, width=1.8, straight=True)
d.text(560, 175, 190, 40, "nhiễu đồng kênh<br>tới user của UAV 1", 12, RED, True)
d.edge(uav[2], ucell[5], "", color=RED, dashed=True, width=1.8, straight=True)
d.box(60, 470, 990, 110,
      "<b>Mỗi khe Δt, thuật toán quyết định:</b> user nối UAV nào (a<sub>k</sub>), chia băng thông (b<sub>k</sub>), công suất (p<sub>k</sub>), vận tốc UAV (v<sub>m</sub>).<br>"
      "<b>Ràng buộc mỗi UAV:</b> Σb<sub>k</sub> ≤ 1 (băng B = 10 MHz), Σp<sub>k</sub> ≤ P<sub>max</sub>, ‖v<sub>m</sub>‖ ≤ V<sub>max</sub>, trong vùng L×L. Các UAV dùng chung băng nên nhiễu nhau.<br>"
      "<b>Nhóm user:</b> ● normal (w = 1, ≥ 0.5 Mbps) &nbsp; ■ important (w = 2, ≥ 1 Mbps) &nbsp; ◆ critical (w = 4, ≥ 2 Mbps). "
      "<b>Mục tiêu:</b> max Σ w<sub>k</sub> log(r<sub>k</sub> + r<sub>0</sub>)",
      fill="#f6f7f9", stroke="#d3d8e0", style="rounded=1;arcSize=4;align=left;spacingLeft=12;")
d.save()

# 2. Kiến trúc tổng thể ----------------------------------------------------------------------------------------------
d = D("kien_truc", 1150, 700)
d.text(0, 5, 1150, 30, "Kiến trúc tổng thể", 17, bold=True)
d.box(20, 50, 660, 440, "", fill="#eef3fa", stroke=NAVY, style="rounded=1;arcSize=3;dashed=1;")
d.text(30, 55, 300, 25, "uavsim (Python)", 14, NAVY, True, "left")
cfg = d.box(40, 100, 160, 60, "SimConfig<br><font style='font-size:11px'>tham số, nhóm user</font>")
net = d.box(260, 100, 220, 60, "Network<br><font style='font-size:11px'>kênh A2G, SINR, rate, hàng đợi, năng lượng</font>")
alg = d.box(260, 230, 220, 60, "Thuật toán<br><font style='font-size:11px'>6 baseline, calib-ifair, bản so sánh</font>", fill="#fff1dc", stroke=AMBER)
run = d.box(40, 380, 170, 60, "run.py<br><font style='font-size:11px'>so sánh, biểu đồ</font>")
ns3p = d.box(260, 380, 190, 60, "ns3.py<br><font style='font-size:11px'>ghi kế hoạch, gọi NS-3, đọc số đo</font>")
live = d.box(490, 380, 170, 60, "live.py<br><font style='font-size:11px'>thời gian thực, lái tay</font>")
d.edge(cfg, net)
d.edge(alg, net, "trạng thái ⇄ quyết định a, b, p, v", both=True)
for t in (run, ns3p, live):
    d.edge(alg, t, exit=(0.5, 1), entry=(0.5, 0))
web = d.box(760, 70, 360, 70, "<b>Dashboard web</b><br><font style='font-size:11px'>bản đồ, chỉ số, nhóm user, lái tay, đổi tham số</font>", fill="#e5edf8", stroke=NAVY)
gz = d.box(760, 190, 360, 70, "<b>Gazebo Harmonic</b><br><font style='font-size:11px'>hiển thị 3D trên bãi thảm họa</font>", fill="#e5edf8", stroke=NAVY)
ns3 = d.box(760, 380, 360, 110, "<b>NS-3 3.47 (C++), uav-lte.cc</b><br>link=lte: eNB bay, UE, EPC, handover X2, UDP, scheduler PF/RR/WPF<br>"
            "link=ideal: liên kết điểm-điểm, tốc độ = rate lý thuyết", fill="#e2f3e8", stroke="#157a3a")
res = d.box(760, 560, 360, 80, "<b>Kết quả</b><br>ns3_slots.csv: byte, gói, độ trễ từng user từng khe; trace PHY/MAC")
d.edge(live, web, "WebSocket JSON", both=True, exit=(0.8, 0), entry=(0, 0.5), points=[(626, 105)])
d.edge(live, gz, "gz-transport 20 Hz", exit=(0.95, 0), entry=(0, 0.5), points=[(651, 225)])
d.edge(ns3p, ns3, "kế hoạch uavs.csv, users.csv", exit=(0.5, 1), entry=(0.5, 1), points=[(355, 520), (940, 520)])
d.edge(ns3, res)
d.edge(res, ns3p, "số đo", dashed=True, exit=(0, 0.5), entry=(0.25, 1), points=[(307, 600)])
d.edge(live, ns3p, "Ghi & đo", dashed=True)
d.save()

# 3. Ba tầng kiểm chứng -------------------------------------------------------------------------------------------------
d = D("ba_tang", 1150, 380)
d.text(0, 5, 1150, 30, "Kiểm chứng ba tầng: cùng một kế hoạch chạy ở ba mức", 17, bold=True)
t1 = d.box(30, 70, 300, 170, "<b>Tầng 1: Lý thuyết (như bài báo)</b><br><br>Kênh Al-Hourani, Shannon có nhiễu<br>Hàng đợi theo khe, độ trễ FIFO chính xác<br>Mất gói = 1 − nhận/gửi",
           fill="#e5edf8", stroke=NAVY)
t2 = d.box(425, 70, 300, 170, "<b>Tầng 2: NS-3 liên kết lý tưởng</b><br><br>Gói UDP thật, mỗi user một liên kết<br>Tốc độ liên kết = rate lý thuyết từng khe<br>Bộ đệm 1 MiB",
           fill="#fff1dc", stroke=AMBER)
t3 = d.box(820, 70, 300, 170, "<b>Tầng 3: NS-3 LTE</b><br><br>eNB bay, UE, EPC, handover X2<br>Scheduler PF / WPF, HARQ, AMC<br>Đo throughput, độ trễ, mất gói",
           fill="#e2f3e8", stroke="#157a3a")
d.edge(t1, t2, "", color="#157a3a", width=2.5)
d.edge(t2, t3, "", color=RED, width=2.5)
d.text(330, 95, 95, 50, "khớp<br>&lt; 1%", 12, "#157a3a", True)
d.text(725, 85, 95, 60, "chênh lệch<br>do giao thức<br>LTE", 12, RED, True)
d.box(30, 270, 1090, 85, "<b>Ý nghĩa:</b> tầng giữa tách lỗi của mô hình khỏi ảnh hưởng của giao thức. Tầng 1 khớp tầng 2 dưới 1% → mô hình hàng đợi đúng; "
      "khoảng cách tầng 2 → 3 được giải thích bằng ba nguyên nhân (công thức 3GPP, trần SE, AMC) và thu về ±3% bằng hai hằng số đo từ NS-3 (α = 0.401, SE<sub>max</sub> = 3.514).",
      fill="#f6f7f9", stroke="#d3d8e0", style="rounded=1;arcSize=6;align=left;spacingLeft=12;")
d.save()

# 4. Lưu đồ calib-ifair --------------------------------------------------------------------------------------------------
d = D("calib_ifair", 900, 900)
d.text(0, 5, 900, 30, "Lưu đồ thuật toán đề xuất calib-ifair (mỗi khe)", 17, bold=True)
term = "rounded=1;arcSize=50;"
s0 = d.box(330, 50, 240, 45, "Bắt đầu khe n", fill="#e5edf8", stroke=NAVY, style=term, bold=True)
s1 = d.box(270, 120, 360, 55, "Nối mỗi user với UAV có độ lợi lớn nhất (a<sub>k</sub>)")
s2 = d.box(270, 200, 360, 70, "Tính SINR có nhiễu từ mọi UAV đang phục vụ<br>ŜE<sub>k</sub> = min(0.401·log₂(1+SINR), 3.514)")
s3 = d.box(270, 295, 360, 70, "<b>ifair:</b> b<sub>k</sub> ∝ w<sub>k</sub> / max(ŜE<sub>k</sub>, 0.05)<br>(w = 1/2/4 theo nhóm)", fill="#fff1dc", stroke=AMBER)
s4 = d.box(295, 395, 310, 90, "UAV j còn cách tâm cụm k-means quá một bước?", style="rhombus;", fill="#ffffff")
s5 = d.box(660, 410, 200, 60, "Bay thẳng về tâm cụm")
s6 = d.box(270, 515, 360, 80, "<b>calib:</b> thử đứng yên + 8 hướng × 2 cỡ bước<br>tính U = Σ w<sub>k</sub> log(r̂<sub>k</sub> + r<sub>0</sub>)", fill="#fff1dc", stroke=AMBER)
s7 = d.box(270, 620, 360, 60, "Chọn nước đi tăng U nhiều nhất,<br>không làm giảm số UAV có user")
s8 = d.box(295, 705, 310, 80, "Còn UAV chưa xét?", style="rhombus;")
s9 = d.box(270, 815, 360, 55, "Gửi quyết định: b<sub>k</sub> → scheduler WPF (MAC), v<sub>m</sub> → UAV", fill="#e2f3e8", stroke="#157a3a", style=term)
for a, b in [(s0, s1), (s1, s2), (s2, s3), (s3, s4), (s6, s7), (s7, s8)]:
    d.edge(a, b)
d.edge(s4, s5, "có")
d.edge(s4, s6, "không")
d.edge(s5, s8, exit=(0.5, 1), entry=(1, 0.5))
d.edge(s8, s9, "không")
d.edge(s8, s4, "có (UAV tiếp theo)", exit=(0, 0.5), entry=(0, 0.5), points=[(200, 745), (200, 440)])
d.save()

# 5. Điều khiển thời gian thực ---------------------------------------------------------------------------------------------
d = D("thoi_gian_thuc", 1150, 460)
d.text(0, 5, 1150, 30, "Hệ thống điều khiển thời gian thực", 17, bold=True)
br = d.box(30, 70, 300, 170, "<b>Trình duyệt (dashboard)</b><br><br>Vẽ 60 Hz, nội suy giữa hai khe<br>Bản đồ, chỉ số, nhóm user, biểu đồ<br>Lái tay W A S D, nhấp để bay tới<br>Đổi 13 tham số, nút Ghi &amp; đo",
           fill="#e5edf8", stroke=NAVY)
sv = d.box(425, 70, 300, 170, "<b>Server asyncio (live.py)</b><br><br>Mỗi khe 0.25 s (tăng tốc 0.5–4×)<br>Thuật toán → quyết định → mô hình<br>Tốc độ Shannon và LTE dự đoán<br>Kiểm tra lệnh, an toàn khi mất kết nối",
           fill="#fff1dc", stroke=AMBER)
gz = d.box(820, 40, 300, 110, "<b>Gazebo</b><br>quadrotor màu UAV, hình người áo màu UAV phục vụ,<br>vòng vàng important, vòng đỏ critical",
           fill="#e2f3e8", stroke="#157a3a")
ns = d.box(820, 180, 300, 90, "<b>NS-3 (luồng riêng)</b><br>phát lại đoạn đã ghi, trả số đo về web", fill="#e2f3e8", stroke="#157a3a")
d.edge(br, sv, "", both=True, width=2)
d.edge(sv, gz, "", exit=(1, 0.3), entry=(0, 0.5))
d.edge(sv, ns, "", exit=(1, 0.75), entry=(0, 0.5))
d.text(330, 95, 95, 55, "WebSocket<br>JSON", 12, "#14181f", True)
d.text(725, 62, 95, 40, "pose<br>20 Hz", 11)
d.text(725, 250, 95, 40, "kế hoạch<br>đủ khe", 11)
d.box(30, 300, 1090, 120, "<b>Luồng một khe:</b> (1) nhận lệnh lái tay / bay tới / đổi tham số → (2) thuật toán ra quyết định, UAV lái tay lấy vận tốc từ web → "
      "(3) mô hình tính SINR, tốc độ, hàng đợi → (4) gửi trạng thái cho web, gửi vị trí nội suy cho Gazebo → (5) nếu đang ghi, lưu kế hoạch; đủ khe thì chạy NS-3 "
      "trong luồng riêng và trả bảng mô hình so với NS-3 về web.",
      fill="#f6f7f9", stroke="#d3d8e0", style="rounded=1;arcSize=6;align=left;spacingLeft=12;")
d.save()

# 6. Lưu đồ phát lại kế hoạch trong NS-3 ------------------------------------------------------------------------------------
d = D("phat_lai_ns3", 900, 860)
d.text(0, 5, 900, 30, "Lưu đồ phát lại một kế hoạch trong NS-3 (uav-lte)", 17, bold=True)
a0 = d.box(330, 50, 240, 45, "Bắt đầu", fill="#e5edf8", stroke=NAVY, style="rounded=1;arcSize=50;", bold=True)
a1 = d.box(250, 120, 400, 50, "Đọc kế hoạch uavs.csv, users.csv")
a2 = d.box(250, 195, 400, 70, "Dựng mạng: remote host, EPC/PGW, eNB (UAV), UE (user)<br>"
           "<font style='font-size:11px'>link=ideal: thay EPC/LTE bằng liên kết điểm-điểm</font>")
a3 = d.box(250, 290, 400, 50, "Đặt điểm mốc vị trí eNB, UE; attach UE theo khe 0")
a4 = d.box(250, 365, 400, 90, "<b>Đầu khe n</b><br>đặt tốc độ phát UDP từng user<br>handover X2 nếu kế hoạch đổi UAV<br>đặt trọng số WPF b<sub>k</sub> (10 ms, 150 ms)",
           fill="#fff1dc", stroke=AMBER)
a5 = d.box(250, 480, 400, 70, "<b>Trong khe</b>: gói UDP 1200 B mang số thứ tự và thời điểm gửi;<br>UE ghi gói nhận và độ trễ")
a6 = d.box(250, 575, 400, 70, "<b>Cuối khe n</b>: ghi gói gửi/nhận, byte, tổng độ trễ, cell đang gắn;<br>đặt lại bộ đếm",
           fill="#fff1dc", stroke=AMBER)
a7 = d.box(295, 670, 310, 80, "Còn khe?", style="rhombus;")
a8 = d.box(250, 780, 400, 55, "Ghi ns3_slots.csv, flowmon.xml", fill="#e2f3e8", stroke="#157a3a", style="rounded=1;arcSize=50;", bold=True)
for x, y in [(a0, a1), (a1, a2), (a2, a3), (a3, a4), (a4, a5), (a5, a6), (a6, a7)]:
    d.edge(x, y)
d.edge(a7, a8, "không")
d.edge(a7, a4, "có (khe n+1)", exit=(1, 0.5), entry=(1, 0.5), points=[(760, 710), (760, 410)])
d.save()

# 7. Trình tự WebSocket -----------------------------------------------------------------------------------------------------
d = D("giao_thuc_ws", 720, 720)
d.text(0, 5, 720, 30, "Trình tự trao đổi giữa trình duyệt và server", 17, bold=True)
c = d.box(20, 50, 180, 45, "<b>Trình duyệt</b>", fill="#e5edf8", stroke=NAVY)
s_ = d.box(520, 50, 180, 45, "<b>Server (live.py)</b>", fill="#fff1dc", stroke=AMBER)
d.box(109, 95, 2, 600, "", fill="#7d8795", stroke="none", style="")
d.box(609, 95, 2, 600, "", fill="#7d8795", stroke="none", style="")
msgs = [(">", "HTTP GET /, /config.js (cổng 8000)", "#4d5766", False),
        ("<", "index.html, WS_PORT", "#4d5766", True),
        (">", "WebSocket handshake (cổng 8001)", "#4d5766", False),
        ("<", "info: cấu hình, trạng thái", BLUE, True),
        ("<", "state mỗi khe 0.25 s: vị trí, SINR, tốc độ", BLUE, True),
        (">", '{"cmd":"vel","uav":0,"vx":15,"vy":0}', ORANGE, False),
        ("<", "info cho mọi trình duyệt (lệnh sai → lỗi)", BLUE, True),
        (">", '{"cmd":"measure","seconds":15,...}', ORANGE, False),
        ("<", "info: đang ghi → NS-3 chạy → kết quả", BLUE, True),
        (">", "đóng kết nối → dừng UAV lái tay", RED, False)]
for i, (dirn, text, color, dashed) in enumerate(msgs):
    y = 125 + i * 57
    l = d.box(105, y, 10, 10, "", fill="none", stroke="none", style="")
    r = d.box(605, y, 10, 10, "", fill="none", stroke="none", style="")
    a, b = (l, r) if dirn == ">" else (r, l)
    d.edge(a, b, text, color=color, dashed=dashed, straight=True)
d.save()

# 8. Chồng giao thức đường LTE ----------------------------------------------------------------------------------------------
d = D("chong_giao_thuc", 1150, 520)
d.text(0, 5, 1150, 30, "Đường đi của một gói dữ liệu đường xuống trong NS-3 LTE", 17, bold=True)
def stack(x, title, layers, fill, stroke):
    d.text(x, 45, 220, 25, title, 14, NAVY, True)
    ids = []
    for i, t in enumerate(layers):
        ids.append(d.box(x, 75 + i * 48, 220, 42, t, fill=fill, stroke=stroke))
    return ids
rh = stack(20, "Remote host", ["Bộ phát UDP<br><font style='font-size:11px'>SeqTsHeader + 1200 B</font>", "UDP (cổng 9)", "IP 1.0.0.0/8", "Point-to-point 10 Gb/s, 1 ms"], "#e5edf8", NAVY)
pg = stack(310, "PGW / SGW (EPC)", ["IP", "GTP-U / UDP / IP", "Point-to-point (S1-U)"], "#f6f7f9", "#aeb6c2")
en = stack(600, "eNB (UAV)", ["GTP-U / UDP / IP", "PDCP", "RLC UM, bộ đệm 1 MiB", "MAC: scheduler PF / RR / <b>WPF (b<sub>k</sub>)</b>", "PHY: AMC, HARQ"], "#fff1dc", AMBER)
ue = stack(890, "UE (user)", ["UDP server: đo độ trễ, mất gói", "UDP / IP 7.0.0.0/8", "PDCP / RLC", "MAC", "PHY"], "#e2f3e8", "#157a3a")
d.edge(rh[3], pg[2], "", width=2)
d.edge(pg[2], en[0], "GTP-U", width=2, exit=(1, 0.5), entry=(0, 0.5))
d.edge(en[4], ue[4], "vô tuyến LTE<br>kênh Al-Hourani", width=2)
x2 = d.box(600, 360, 220, 42, "eNB khác", fill="#fff1dc", stroke=AMBER)
d.edge(en[4], x2, "X2: handover khi kế hoạch đổi UAV", dashed=True, exit=(0.5, 1), entry=(0.5, 0))
d.box(20, 430, 1100, 70, "<b>Chế độ liên kết lý tưởng:</b> bỏ EPC và LTE; remote host nối mỗi UE bằng một liên kết điểm-điểm riêng, tốc độ = tốc độ phục vụ lý thuyết "
      "của khe (bù header 30 B), hàng đợi DropTail 1 MiB. Dùng để kiểm chứng mô hình hàng đợi (tầng 2 của kiểm chứng ba tầng).",
      fill="#f6f7f9", stroke="#d3d8e0", style="rounded=1;arcSize=6;align=left;spacingLeft=12;")
d.save()
print("ok", sorted(p.name for p in OUT.glob("*.drawio")))
