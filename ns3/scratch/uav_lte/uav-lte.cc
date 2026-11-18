/*
 * uav-lte: phát lại kế hoạch của uavsim trong NS-3 LTE và đo ở mức gói tin.
 *
 * - Mỗi UAV là một eNB bay theo quỹ đạo trong uavs.csv (WaypointMobilityModel, độ cao cố định).
 * - Mỗi user là một UE; liên kết user-UAV theo users.csv, đổi liên kết bằng handover X2.
 * - Kênh: AlHouraniPropagationLossModel (cùng công thức với uavsim/channel.py).
 * - reuse1=true: mọi eNB dùng chung một kênh tần số, LTE PHY tính nhiễu liên cell.
 *   reuse1=false: mỗi eNB một kênh riêng không chồng lấn, không có nhiễu liên cell.
 * - traces=true: ghi trace LTE (DlRsrpSinrStats, DlRxPhyStats, DlMacStats) vào <out>/.
 * - Lưu lượng: một luồng UDP downlink remote host -> UE, rate từng khe = rate kế hoạch * load.
 * - Đo mỗi khe, mỗi UE: gói gửi, gói nhận, byte nhận, tổng delay, cell đang phục vụ thực tế.
 *
 * - scheduler=wpf: Weighted PF (wpf-ff-mac-scheduler.cc), trọng số mỗi UE = b_k của thuật toán, nên quyết định
 *   chia băng thông được áp ở tầng MAC.
 *
 * Đầu vào:  <plan>/uavs.csv   slot,uav,x,y            (slot 0..N)
 *           <plan>/users.csv  slot,user,x,y,serving,rate_bps[,bw[,cap_bps]]   (slot 0..N; slot N chỉ dùng vị trí;
 *                             bw = tỷ lệ băng thông b_k, mặc định 1)
 * - link=ideal: bỏ LTE; mỗi user một liên kết điểm-điểm remote host -> UE, tốc độ từng khe = cap_bps (rate
 *   lý thuyết của mô hình), hàng đợi DropTail bufferBytes. Kiểm chứng mô hình hàng đợi ở mức gói tin.
 *
 * Đầu ra:   <out>/ns3_slots.csv, <out>/flowmon.xml
 */
#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/lte-module.h"
#include "ns3/mobility-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/propagation-loss-model.h"
#include "ns3/traffic-control-module.h"

#include "wpf-ff-mac-scheduler.h"

#include <cmath>
#include <fstream>
#include <map>
#include <sstream>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("UavLte");

// ---------------------------------------------------------------- kênh Al-Hourani
class AlHouraniPropagationLossModel : public PropagationLossModel
{
  public:
    static TypeId GetTypeId()
    {
        static TypeId tid =
            TypeId("ns3::AlHouraniPropagationLossModel")
                .SetParent<PropagationLossModel>()
                .AddConstructor<AlHouraniPropagationLossModel>()
                .AddAttribute("Frequency", "Hz", DoubleValue(2e9),
                              MakeDoubleAccessor(&AlHouraniPropagationLossModel::m_fc),
                              MakeDoubleChecker<double>())
                .AddAttribute("A", "", DoubleValue(9.61),
                              MakeDoubleAccessor(&AlHouraniPropagationLossModel::m_a),
                              MakeDoubleChecker<double>())
                .AddAttribute("B", "", DoubleValue(0.16),
                              MakeDoubleAccessor(&AlHouraniPropagationLossModel::m_b),
                              MakeDoubleChecker<double>())
                .AddAttribute("EtaLos", "dB", DoubleValue(1.0),
                              MakeDoubleAccessor(&AlHouraniPropagationLossModel::m_etaLos),
                              MakeDoubleChecker<double>())
                .AddAttribute("EtaNlos", "dB", DoubleValue(20.0),
                              MakeDoubleAccessor(&AlHouraniPropagationLossModel::m_etaNlos),
                              MakeDoubleChecker<double>())
                .AddAttribute("LosOnly", "true: g = beta0/d^2", BooleanValue(false),
                              MakeBooleanAccessor(&AlHouraniPropagationLossModel::m_losOnly),
                              MakeBooleanChecker())
                .AddAttribute("Beta0Db", "dB tại 1 m (LosOnly)", DoubleValue(-60.0),
                              MakeDoubleAccessor(&AlHouraniPropagationLossModel::m_beta0Db),
                              MakeDoubleChecker<double>());
        return tid;
    }

    double PathLossDb(Ptr<MobilityModel> a, Ptr<MobilityModel> b) const
    {
        Vector pa = a->GetPosition();
        Vector pb = b->GetPosition();
        double horiz = std::hypot(pa.x - pb.x, pa.y - pb.y);
        double dz = std::abs(pa.z - pb.z);
        double d3 = std::max(std::hypot(horiz, dz), 1.0);
        if (m_losOnly)
        {
            return -m_beta0Db + 20 * std::log10(d3);
        }
        double theta = std::atan2(dz, horiz) * 180.0 / M_PI;
        double pLos = 1.0 / (1.0 + m_a * std::exp(-m_b * (theta - m_a)));
        double fspl = 20 * std::log10(4 * M_PI * m_fc * d3 / 299792458.0);
        return fspl + pLos * m_etaLos + (1 - pLos) * m_etaNlos;
    }

  private:
    double DoCalcRxPower(double txPowerDbm, Ptr<MobilityModel> a, Ptr<MobilityModel> b) const override
    {
        return txPowerDbm - PathLossDb(a, b);
    }

    int64_t DoAssignStreams(int64_t) override
    {
        return 0;
    }

    double m_fc, m_a, m_b, m_etaLos, m_etaNlos, m_beta0Db;
    bool m_losOnly;
};

NS_OBJECT_ENSURE_REGISTERED(AlHouraniPropagationLossModel);

// ---------------------------------------------------------------- đọc kế hoạch
struct UserRow
{
    double x, y;
    int serving;
    double rate;
    double bw;  // tỷ lệ băng thông b_k thuật toán cấp (trọng số cho scheduler wpf)
    double cap; // tốc độ phục vụ lý thuyết (bit/s), dùng cho link=ideal
};

static std::vector<std::vector<std::string>>
ReadCsv(const std::string& path)
{
    std::ifstream f(path);
    NS_ABORT_MSG_IF(!f.is_open(), "không mở được " << path);
    std::vector<std::vector<std::string>> rows;
    std::string line;
    std::getline(f, line); // header
    while (std::getline(f, line))
    {
        if (line.empty())
        {
            continue;
        }
        std::vector<std::string> cols;
        std::stringstream ss(line);
        std::string c;
        while (std::getline(ss, c, ','))
        {
            cols.push_back(c);
        }
        rows.push_back(cols);
    }
    return rows;
}

// ---------------------------------------------------------------- luồng UDP rate thay đổi theo khe
struct Flow
{
    Ptr<Socket> sock;
    double rate = 0; // bit/s
    EventId ev;
    uint32_t seq = 0;
    // bộ đếm của khe hiện tại
    uint64_t txPkts = 0, rxPkts = 0, rxBytes = 0;
    double delaySum = 0;
};

static uint32_t g_pktSize = 1200; // byte payload UDP
static Ptr<UniformRandomVariable> g_jitter;

static void
SendPacket(Flow* f)
{
    SeqTsHeader h;
    h.SetSeq(f->seq++);
    Ptr<Packet> p = Create<Packet>(g_pktSize - h.GetSerializedSize());
    p->AddHeader(h);
    f->sock->Send(p);
    f->txPkts++;
    f->ev = Simulator::Schedule(Seconds(g_pktSize * 8.0 / f->rate), &SendPacket, f);
}

static void
SetRate(Flow* f, double rate)
{
    f->ev.Cancel();
    f->rate = rate;
    if (rate > 0)
    {
        // lệch pha ngẫu nhiên để các luồng không gửi cùng lúc
        f->ev = Simulator::Schedule(Seconds(g_jitter->GetValue(0, g_pktSize * 8.0 / rate)),
                                    &SendPacket, f);
    }
}

static void
OnRx(Flow* f, Ptr<const Packet> p, const Address&, const Address&)
{
    SeqTsHeader h;
    p->PeekHeader(h);
    f->rxPkts++;
    f->rxBytes += p->GetSize();
    f->delaySum += (Simulator::Now() - h.GetTs()).GetSeconds();
}

static uint32_t g_hoOk = 0, g_hoStart = 0;

static void
HoStart(std::string, uint64_t, uint16_t, uint16_t, uint16_t)
{
    g_hoStart++;
}

static void
HoOk(std::string, uint64_t, uint16_t, uint16_t)
{
    g_hoOk++;
}

// ---------------------------------------------------------------- link=ideal
static void
SetLinkRate(Ptr<PointToPointNetDevice> dev, double bps)
{
    // payload UDP g_pktSize + UDP 8 + IP 20 + PPP 2 byte: nâng tốc độ dây để goodput đúng bằng cap
    double wire = bps * (g_pktSize + 30.0) / g_pktSize;
    dev->SetDataRate(DataRate(uint64_t(std::max(wire, 1e3)))); // 0 bit/s không hợp lệ trong NS-3
}

static int
RunIdeal(const std::vector<std::vector<UserRow>>& users, uint32_t numUsers, uint32_t slots, double dt,
         double warmup, double load, uint32_t bufferBytes, const std::string& out)
{
    NodeContainer remote, ues;
    remote.Create(1);
    ues.Create(numUsers);
    InternetStackHelper inet;
    inet.Install(remote);
    inet.Install(ues);
    PointToPointHelper p2p;
    p2p.SetChannelAttribute("Delay", TimeValue(Seconds(0)));
    p2p.SetQueue("ns3::DropTailQueue<Packet>", "MaxSize",
                 // mô hình đếm bộ đệm theo payload, thiết bị đếm cả header 30 byte mỗi gói
                 QueueSizeValue(QueueSize(QueueSizeUnit::BYTES, uint32_t(bufferBytes * (g_pktSize + 30.0) / g_pktSize))));
    Ipv4AddressHelper ip;
    TrafficControlHelper tch;
    std::vector<Flow> flows(numUsers);
    std::vector<Ptr<PointToPointNetDevice>> devs(numUsers);
    for (uint32_t k = 0; k < numUsers; k++)
    {
        NetDeviceContainer d = p2p.Install(remote.Get(0), ues.Get(k));
        std::ostringstream net;
        net << "10." << (k / 256) << "." << (k % 256) << ".0";
        ip.SetBase(net.str().c_str(), "255.255.255.0");
        Ipv4InterfaceContainer ifs = ip.Assign(d);
        tch.Uninstall(d); // sau Assign (Assign tự cài qdisc): chỉ còn hàng đợi bufferBytes của thiết bị, giống mô hình
        devs[k] = DynamicCast<PointToPointNetDevice>(d.Get(0));
        SetLinkRate(devs[k], users[0][k].cap);

        Ptr<UdpServer> srv = CreateObject<UdpServer>();
        srv->SetAttribute("Port", UintegerValue(9));
        ues.Get(k)->AddApplication(srv);
        srv->TraceConnectWithoutContext("RxWithAddresses", MakeBoundCallback(&OnRx, &flows[k]));
        flows[k].sock = Socket::CreateSocket(remote.Get(0), UdpSocketFactory::GetTypeId());
        flows[k].sock->Connect(InetSocketAddress(ifs.GetAddress(1), 9));
    }

    for (uint32_t s = 0; s < slots; s++)
    {
        Time t = Seconds(warmup + s * dt);
        for (uint32_t k = 0; k < numUsers; k++)
        {
            const UserRow& u = users[s][k];
            Simulator::Schedule(t, &SetLinkRate, devs[k], u.serving >= 0 ? u.cap : 0.0);
            Simulator::Schedule(t, &SetRate, &flows[k], u.serving >= 0 ? u.rate * load : 0.0);
        }
    }

    std::ofstream csv(out + "/ns3_slots.csv");
    csv << "slot,user,plan_cell,actual_cell,tx_pkts,rx_pkts,rx_bytes,delay_sum_s\n";
    for (uint32_t s = 0; s < slots; s++)
    {
        Simulator::Schedule(Seconds(warmup + (s + 1) * dt), [&, s]() {
            for (uint32_t k = 0; k < numUsers; k++)
            {
                Flow& f = flows[k];
                csv << s << "," << k << "," << users[s][k].serving << "," << users[s][k].serving << ","
                    << f.txPkts << "," << f.rxPkts << "," << f.rxBytes << "," << f.delaySum << "\n";
                f.txPkts = f.rxPkts = f.rxBytes = 0;
                f.delaySum = 0;
            }
        });
    }
    Simulator::Stop(Seconds(warmup + slots * dt + 1e-6));
    Simulator::Run();
    csv.close();
    std::cout << "link=ideal" << std::endl;
    Simulator::Destroy();
    return 0;
}

int
main(int argc, char* argv[])
{
    std::string plan = "plan", out = "out", scheduler = "pf", channel = "al_hourani";
    uint32_t numUavs = 3, numUsers = 20, slots = 60, rb = 50, seed = 1;
    double dt = 1.0, altitude = 100, txPowerDbm = 30, noiseFigure = 5, fc = 2e9;
    double a = 9.61, b = 0.16, etaLos = 1.0, etaNlos = 20.0, beta0Db = -60, load = 1.0;
    double warmup = 0.5;
    bool reuse1 = true, traces = false;
    std::string link = "lte";
    uint32_t bufferBytes = 1024 * 1024;

    CommandLine cmd(__FILE__);
    cmd.AddValue("plan", "thư mục chứa uavs.csv, users.csv", plan);
    cmd.AddValue("out", "thư mục kết quả", out);
    cmd.AddValue("numUavs", "M", numUavs);
    cmd.AddValue("numUsers", "K", numUsers);
    cmd.AddValue("slots", "số khe N", slots);
    cmd.AddValue("dt", "độ dài khe (s)", dt);
    cmd.AddValue("altitude", "độ cao UAV (m)", altitude);
    cmd.AddValue("rb", "số resource block (50 = 10 MHz)", rb);
    cmd.AddValue("txPowerDbm", "công suất phát eNB (dBm)", txPowerDbm);
    cmd.AddValue("noiseFigure", "noise figure UE (dB)", noiseFigure);
    cmd.AddValue("fc", "tần số dùng trong mô hình suy hao (Hz)", fc);
    cmd.AddValue("channel", "al_hourani | los", channel);
    cmd.AddValue("a", "Al-Hourani a", a);
    cmd.AddValue("b", "Al-Hourani b", b);
    cmd.AddValue("etaLos", "dB", etaLos);
    cmd.AddValue("etaNlos", "dB", etaNlos);
    cmd.AddValue("beta0Db", "dB tại 1 m (channel=los)", beta0Db);
    cmd.AddValue("scheduler", "rr | pf | wpf (PF có trọng số b_k)", scheduler);
    cmd.AddValue("load", "hệ số nhân rate kế hoạch", load);
    cmd.AddValue("pktSize", "byte payload UDP", g_pktSize);
    cmd.AddValue("seed", "RngRun", seed);
    cmd.AddValue("reuse1", "true: mọi eNB chung tần số; false: mỗi eNB một kênh riêng", reuse1);
    cmd.AddValue("traces", "ghi trace PHY/MAC downlink của LTE", traces);
    cmd.AddValue("link", "lte | ideal (liên kết điểm-điểm, tốc độ = rate lý thuyết)", link);
    cmd.AddValue("bufferBytes", "hàng đợi mỗi user (byte): RLC UM khi lte, DropTail khi ideal", bufferBytes);
    cmd.Parse(argc, argv);
    NS_ABORT_MSG_UNLESS(link == "lte" || link == "ideal", "link không hợp lệ");

    RngSeedManager::SetSeed(1);
    RngSeedManager::SetRun(seed);
    g_jitter = CreateObject<UniformRandomVariable>();

    // ---- kế hoạch
    std::vector<std::vector<Vector>> uavPos(slots + 1, std::vector<Vector>(numUavs));
    for (auto& r : ReadCsv(plan + "/uavs.csv"))
    {
        uint32_t s = std::stoul(r[0]), m = std::stoul(r[1]);
        NS_ABORT_MSG_IF(s > slots || m >= numUavs, "uavs.csv ngoài phạm vi");
        uavPos[s][m] = Vector(std::stod(r[2]), std::stod(r[3]), altitude);
    }
    std::vector<std::vector<UserRow>> users(slots + 1, std::vector<UserRow>(numUsers));
    for (auto& r : ReadCsv(plan + "/users.csv"))
    {
        uint32_t s = std::stoul(r[0]), k = std::stoul(r[1]);
        NS_ABORT_MSG_IF(s > slots || k >= numUsers, "users.csv ngoài phạm vi");
        users[s][k] = {std::stod(r[2]), std::stod(r[3]), std::stoi(r[4]), std::stod(r[5]),
                       r.size() > 6 ? std::stod(r[6]) : 1.0,
                       r.size() > 7 ? std::stod(r[7]) : 0.0};
    }

    if (link == "ideal")
    {
        return RunIdeal(users, numUsers, slots, dt, warmup, load, bufferBytes, out);
    }

    // ---- LTE + EPC
    Config::SetDefault("ns3::LteEnbPhy::TxPower", DoubleValue(txPowerDbm));
    Config::SetDefault("ns3::LteUePhy::NoiseFigure", DoubleValue(noiseFigure));
    Config::SetDefault("ns3::LteEnbRrc::SrsPeriodicity", UintegerValue(numUsers > 20 ? 80 : 40));
    Config::SetDefault("ns3::LteRlcUm::MaxTxBufferSize", UintegerValue(bufferBytes));

    if (traces)
    {
        Config::SetDefault("ns3::PhyStatsCalculator::DlRsrpSinrFilename", StringValue(out + "/DlRsrpSinrStats.txt"));
        Config::SetDefault("ns3::PhyStatsCalculator::UlSinrFilename", StringValue(out + "/UlSinrStats.txt"));
        Config::SetDefault("ns3::PhyStatsCalculator::UlInterferenceFilename", StringValue(out + "/UlInterferenceStats.txt"));
        Config::SetDefault("ns3::PhyRxStatsCalculator::DlRxOutputFilename", StringValue(out + "/DlRxPhyStats.txt"));
        Config::SetDefault("ns3::PhyRxStatsCalculator::UlRxOutputFilename", StringValue(out + "/UlRxPhyStats.txt"));
        Config::SetDefault("ns3::MacStatsCalculator::DlOutputFilename", StringValue(out + "/DlMacStats.txt"));
        Config::SetDefault("ns3::MacStatsCalculator::UlOutputFilename", StringValue(out + "/UlMacStats.txt"));
    }

    Ptr<LteHelper> lte = CreateObject<LteHelper>();
    Ptr<PointToPointEpcHelper> epc = CreateObject<PointToPointEpcHelper>();
    lte->SetEpcHelper(epc);
    NS_ABORT_MSG_UNLESS(scheduler == "rr" || scheduler == "pf" || scheduler == "wpf", "scheduler không hợp lệ");
    lte->SetSchedulerType(scheduler == "rr"    ? "ns3::RrFfMacScheduler"
                          : scheduler == "pf" ? "ns3::PfFfMacScheduler"
                                              : "ns3::WpfFfMacScheduler");
    lte->SetHandoverAlgorithmType("ns3::NoOpHandoverAlgorithm"); // handover chỉ theo kế hoạch
    lte->SetPathlossModelType(AlHouraniPropagationLossModel::GetTypeId());
    lte->SetPathlossModelAttribute("Frequency", DoubleValue(fc));
    lte->SetPathlossModelAttribute("A", DoubleValue(a));
    lte->SetPathlossModelAttribute("B", DoubleValue(b));
    lte->SetPathlossModelAttribute("EtaLos", DoubleValue(etaLos));
    lte->SetPathlossModelAttribute("EtaNlos", DoubleValue(etaNlos));
    lte->SetPathlossModelAttribute("LosOnly", BooleanValue(channel == "los"));
    lte->SetPathlossModelAttribute("Beta0Db", DoubleValue(beta0Db));
    lte->SetEnbDeviceAttribute("DlBandwidth", UintegerValue(rb));
    lte->SetEnbDeviceAttribute("UlBandwidth", UintegerValue(rb));

    // remote host -- PGW
    Ptr<Node> pgw = epc->GetPgwNode();
    NodeContainer remote;
    remote.Create(1);
    InternetStackHelper inet;
    inet.Install(remote);
    PointToPointHelper p2p;
    p2p.SetDeviceAttribute("DataRate", DataRateValue(DataRate("10Gb/s")));
    p2p.SetChannelAttribute("Delay", TimeValue(MilliSeconds(1)));
    NetDeviceContainer core = p2p.Install(pgw, remote.Get(0));
    Ipv4AddressHelper ip;
    ip.SetBase("1.0.0.0", "255.0.0.0");
    ip.Assign(core);
    Ipv4StaticRoutingHelper srh;
    srh.GetStaticRouting(remote.Get(0)->GetObject<Ipv4>())
        ->AddNetworkRouteTo(Ipv4Address("7.0.0.0"), Ipv4Mask("255.0.0.0"), 1);

    NodeContainer enbs, ues;
    enbs.Create(numUavs);
    ues.Create(numUsers);

    // ---- di chuyển theo kế hoạch: vị trí đầu khe s tại thời điểm warmup + s*dt
    MobilityHelper mob;
    mob.SetMobilityModel("ns3::WaypointMobilityModel");
    mob.Install(enbs);
    mob.Install(ues);
    for (uint32_t m = 0; m < numUavs; m++)
    {
        auto wp = enbs.Get(m)->GetObject<WaypointMobilityModel>();
        wp->AddWaypoint(Waypoint(Seconds(0), uavPos[0][m]));
        for (uint32_t s = 0; s <= slots; s++)
        {
            wp->AddWaypoint(Waypoint(Seconds(warmup + s * dt), uavPos[s][m]));
        }
    }
    for (uint32_t k = 0; k < numUsers; k++)
    {
        auto wp = ues.Get(k)->GetObject<WaypointMobilityModel>();
        wp->AddWaypoint(Waypoint(Seconds(0), Vector(users[0][k].x, users[0][k].y, 0)));
        for (uint32_t s = 0; s <= slots; s++)
        {
            wp->AddWaypoint(Waypoint(Seconds(warmup + s * dt), Vector(users[s][k].x, users[s][k].y, 0)));
        }
    }

    NetDeviceContainer enbDevs;
    if (reuse1)
    {
        enbDevs = lte->InstallEnbDevice(enbs);
    }
    else
    {
        // EARFCN tính theo 100 kHz; băng rb RB rộng ~ rb*0.2 MHz nên cách nhau rb*2 là không chồng lấn
        for (uint32_t m = 0; m < numUavs; m++)
        {
            lte->SetEnbDeviceAttribute("DlEarfcn", UintegerValue(100 + 2 * rb * m));
            lte->SetEnbDeviceAttribute("UlEarfcn", UintegerValue(18100 + 2 * rb * m));
            enbDevs.Add(lte->InstallEnbDevice(NodeContainer(enbs.Get(m))));
        }
    }
    NetDeviceContainer ueDevs = lte->InstallUeDevice(ues);
    inet.Install(ues);
    Ipv4InterfaceContainer ueIfs = epc->AssignUeIpv4Address(ueDevs);
    for (uint32_t k = 0; k < numUsers; k++)
    {
        srh.GetStaticRouting(ues.Get(k)->GetObject<Ipv4>())
            ->SetDefaultRoute(epc->GetUeDefaultGatewayAddress(), 1);
    }
    lte->AddX2Interface(enbs);

    std::vector<int> cur(numUsers);
    for (uint32_t k = 0; k < numUsers; k++)
    {
        cur[k] = std::max(users[0][k].serving, 0);
        lte->Attach(ueDevs.Get(k), enbDevs.Get(cur[k]));
    }

    // ---- luồng UDP downlink
    std::vector<Flow> flows(numUsers);
    uint16_t port = 9;
    for (uint32_t k = 0; k < numUsers; k++)
    {
        Ptr<UdpServer> srv = CreateObject<UdpServer>();
        srv->SetAttribute("Port", UintegerValue(port));
        ues.Get(k)->AddApplication(srv);
        srv->SetStartTime(Seconds(0));
        srv->TraceConnectWithoutContext("RxWithAddresses", MakeBoundCallback(&OnRx, &flows[k]));

        flows[k].sock = Socket::CreateSocket(remote.Get(0), UdpSocketFactory::GetTypeId());
        flows[k].sock->Connect(InetSocketAddress(ueIfs.GetAddress(k), port));
    }

    // ---- wpf: trọng số b_k đặt trên scheduler của eNB đang phục vụ UE, theo RNTI hiện tại của UE.
    // RNTI đổi sau handover nên đặt lại sau đầu khe 10 ms và 150 ms.
    uint32_t weightSet = 0, weightSkipped = 0;
    auto applyWeights = [&](uint32_t s) {
        for (uint32_t k = 0; k < numUsers; k++)
        {
            auto ueDev = DynamicCast<LteUeNetDevice>(ueDevs.Get(k));
            int cell = int(ueDev->GetRrc()->GetCellId()) - 1;
            if (users[s][k].serving < 0 || cell != users[s][k].serving)
            {
                weightSkipped++;  // UE chưa ở cell kế hoạch (đang handover) -> lần đặt sau sẽ áp
                continue;
            }
            auto enbDev = DynamicCast<LteEnbNetDevice>(enbDevs.Get(cell));
            auto cc = DynamicCast<ComponentCarrierEnb>(enbDev->GetCcMap().at(0));
            auto sched = DynamicCast<WpfFfMacScheduler>(cc->GetFfMacScheduler());
            sched->SetDlWeight(ueDev->GetRrc()->GetRnti(), users[s][k].bw);
            weightSet++;
        }
    };
    if (scheduler == "wpf")
    {
        double t1 = std::min(0.01, 0.2 * dt);
        double t2 = std::min(0.15, 0.6 * dt);
        for (uint32_t s = 0; s < slots; s++)
        {
            Simulator::Schedule(Seconds(warmup + s * dt + t1), [&applyWeights, s]() { applyWeights(s); });
            if (t2 > t1)
            {
                Simulator::Schedule(Seconds(warmup + s * dt + t2), [&applyWeights, s]() { applyWeights(s); });
            }
        }
    }

    // ---- lịch: đầu khe s đặt rate, handover nếu kế hoạch đổi liên kết
    for (uint32_t s = 0; s < slots; s++)
    {
        Time t = Seconds(warmup + s * dt);
        for (uint32_t k = 0; k < numUsers; k++)
        {
            const UserRow& u = users[s][k];
            if (u.serving >= 0 && u.serving != cur[k])
            {
                lte->HandoverRequest(t, ueDevs.Get(k), enbDevs.Get(cur[k]), enbDevs.Get(u.serving));
                cur[k] = u.serving;
            }
            double rate = u.serving >= 0 ? u.rate * load : 0.0;
            Simulator::Schedule(t, &SetRate, &flows[k], rate);
        }
    }

    // ---- ghi số đo cuối mỗi khe (gói còn bay qua ranh giới khe được tính vào khe nhận)
    std::ofstream csv(out + "/ns3_slots.csv");
    csv << "slot,user,plan_cell,actual_cell,tx_pkts,rx_pkts,rx_bytes,delay_sum_s\n";
    for (uint32_t s = 0; s < slots; s++)
    {
        Simulator::Schedule(Seconds(warmup + (s + 1) * dt), [&, s]() {
            for (uint32_t k = 0; k < numUsers; k++)
            {
                Flow& f = flows[k];
                auto ueDev = DynamicCast<LteUeNetDevice>(ueDevs.Get(k));
                csv << s << "," << k << "," << users[s][k].serving << ","
                    << int(ueDev->GetRrc()->GetCellId()) - 1 << "," << f.txPkts << "," << f.rxPkts << ","
                    << f.rxBytes << "," << f.delaySum << "\n";
                f.txPkts = f.rxPkts = f.rxBytes = 0;
                f.delaySum = 0;
            }
        });
    }

    Config::Connect("/NodeList/*/DeviceList/*/LteUeRrc/HandoverStart", MakeCallback(&HoStart));
    Config::Connect("/NodeList/*/DeviceList/*/LteUeRrc/HandoverEndOk", MakeCallback(&HoOk));

    if (traces)
    {
        lte->EnableDlPhyTraces();
        lte->EnableDlRxPhyTraces();
        lte->EnableDlMacTraces();
    }

    FlowMonitorHelper fmh;
    Ptr<FlowMonitor> fm = fmh.Install(remote);
    fmh.Install(ues);

    Simulator::Stop(Seconds(warmup + slots * dt + 1e-6));
    Simulator::Run();
    fm->SerializeToXmlFile(out + "/flowmon.xml", false, false);
    csv.close();
    std::cout << "handover_start=" << g_hoStart << " handover_ok=" << g_hoOk << " weight_set=" << weightSet
              << " weight_skipped=" << weightSkipped << std::endl;
    Simulator::Destroy();
    return 0;
}
