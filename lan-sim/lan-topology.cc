#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/dhcp-helper.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/netanim-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/random-variable-stream.h"
#include "ns3/simulator.h"
#include "ns3/traffic-control-module.h"
#include "ns3/wifi-module.h"
#include "tcp-packet-filter.h"

using namespace ns3;
/* Topology
 *       +--------n1------n2
 *       |
 * n0----+
 *       |
 *       +--------n3 )))))) n4
 * n2 and n4 will use all bandwidth for the speed test
 */
NS_LOG_COMPONENT_DEFINE("lan-topology");
int main(int argc, char *argv[]) {
  // Logging
  LogComponentEnable("BulkSendApplication", LOG_LEVEL_INFO);
  LogComponentEnable("PacketSink", LOG_LEVEL_INFO);
  LogComponentEnable("TcpPacketFilter", LOG_LEVEL_INFO);
  // LogComponentEnable("AnimationInterface", LOG_LEVEL_INFO);
  // LogComponentEnable("FlowMonitor", LOG_LEVEL_INFO);
  LogComponentEnable("lan-topology", LOG_LEVEL_INFO);
  Time::SetResolution(Time::NS);

  // Control the amount of wifi nodes
  int nWifiNodes = 2;

  // Point to point, simulate the internet
  NodeContainer p2pNodes;
  p2pNodes.Create(2);

  PointToPointHelper p2p;
  p2p.SetChannelAttribute("Delay", StringValue("5ms"));
  p2p.SetDeviceAttribute("DataRate", StringValue("10Mbps"));
  NetDeviceContainer p2pDevs = p2p.Install(p2pNodes);

  // Wifi nodes
  NodeContainer wifiStaNodes;
  wifiStaNodes.Create(nWifiNodes);

  NodeContainer wifiApNodes = p2pNodes.Get(1);

  // The wifi model
  // The layer 1
  YansWifiChannelHelper channel = YansWifiChannelHelper::Default();
  YansWifiPhyHelper phy;
  phy.SetErrorRateModel("ns3::NistErrorRateModel");
  phy.SetChannel(channel.Create());

  // The layer 2
  WifiHelper wifi;
  wifi.SetRemoteStationManager("ns3::MinstrelWifiManager");
  WifiMacHelper mac;

  // Install on the client
  Ssid ssid = Ssid("ns3-wlan");
  mac.SetType("ns3::StaWifiMac", "Ssid", SsidValue(ssid), "ActiveProbing",
              BooleanValue(false));
  NetDeviceContainer staDevs;
  staDevs = wifi.Install(phy, mac, wifiStaNodes);

  // Install on the AP
  mac.SetType("ns3::ApWifiMac", "Ssid", SsidValue(ssid));
  NetDeviceContainer apDevs;
  apDevs = wifi.Install(phy, mac, wifiApNodes);

  // Mobility model
  // Make the client move around
  MobilityHelper mobility;
  mobility.SetPositionAllocator(
      "ns3::GridPositionAllocator", "MinX", DoubleValue(0.0), "MinY",
      DoubleValue(0.0), "DeltaX", DoubleValue(5.0), "DeltaY", DoubleValue(10.0),
      "GridWidth", UintegerValue(nWifiNodes / 2 + 1), "LayoutType",
      StringValue("RowFirst"));
  mobility.SetMobilityModel("ns3::RandomWalk2dMobilityModel", "Bounds",
                            RectangleValue(Rectangle(-50, 50, -50, 50)));
  mobility.Install(wifiStaNodes);
  // Make the other nodes stand still
  mobility.SetPositionAllocator(
      "ns3::GridPositionAllocator", "MinX", DoubleValue(-15.0), "MinY",
      DoubleValue(0.0), "DeltaX", DoubleValue(5.0), "DeltaY", DoubleValue(5.0),
      "GridWidth", UintegerValue(3), "LayoutType", StringValue("RowFirst"));
  mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  mobility.Install(p2pNodes);

  // Internet stack
  InternetStackHelper inet;
  inet.Install(p2pNodes);
  inet.Install(wifiStaNodes);

  // Traffic control stuff
  TrafficControlHelper tc;
  tc.SetRootQueueDisc("ns3::PrioQueueDisc");
  tc.AddPacketFilter(0, "ns3::TcpPacketFilter");
  tc.Install(apDevs.Get(0));

  // IP Address for the devices
  Ipv4AddressHelper address;
  address.SetBase("10.0.0.0", "255.255.255.0");
  Ipv4InterfaceContainer p2pIfaces = address.Assign(p2pDevs);
  address.SetBase("172.16.0.0", "255.255.255.0");
  address.Assign(apDevs);
  address.Assign(staDevs);
  // Ipv4InterfaceContainer csmaIfaces = address.Assign(csmaDevs);
  // Ipv4InterfaceContainer staIface = address.Assign(staDevs);

  // Populate the routing table for inter network connection
  Ipv4GlobalRoutingHelper::PopulateRoutingTables();

  // Send as much data as possible
  uint16_t port = 9;
  PacketSinkHelper sink("ns3::TcpSocketFactory",
                        InetSocketAddress(p2pIfaces.GetAddress(0), port));
  ApplicationContainer server = sink.Install(p2pNodes.Get(0));
  server.Start(Seconds(5.0));
  server.Stop(Seconds(10.0));

  BulkSendHelper send("ns3::TcpSocketFactory",
                      InetSocketAddress(p2pIfaces.GetAddress(0), port));
  // Randomly send the specified bytes
  Ptr<UniformRandomVariable> random = CreateObject<UniformRandomVariable>();
  random->SetAttribute("Min", DoubleValue(500.0));
  random->SetAttribute("Max", DoubleValue(512.0));
  send.SetAttribute("MaxBytes", UintegerValue(0));
  send.SetAttribute("SendSize", UintegerValue(random->GetInteger()));

  ApplicationContainer clients = send.Install(wifiStaNodes);
  clients.Start(Seconds(6.0));
  clients.Stop(Seconds(9.0));
  // Stats
  FlowMonitorHelper flowMon;
  Ptr<FlowMonitor> result = flowMon.InstallAll();

  Simulator::Stop(Seconds(12.0));

  // Capturing packets
  p2p.EnablePcapAll("p2p");
  phy.EnablePcapAll("wireless-client");

  NS_LOG_INFO("Running the simulation...");

  // Animating the nodes
  AnimationInterface anim("anim.xml");
  anim.SetMaxPktsPerTraceFile(500000);
  anim.EnablePacketMetadata(true);
  // anim.SetMobilityPollInterval(Seconds(2.0));
  Simulator::Run();
  result->SerializeToXmlFile("stats.xml", false, false);

  Simulator::Destroy();
  NS_LOG_INFO("Simulation finished.");
  return 0;
}
