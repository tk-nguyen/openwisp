#include "tcp-packet-filter.h"
#include "ns3/ipv4-packet-filter.h"
#include "ns3/log.h"
#include "ns3/queue-item.h"
#include "ns3/type-id.h"
#include <cstdint>
#include <ostream>

namespace ns3 {

// Logging
NS_LOG_COMPONENT_DEFINE("TcpPacketFilter");

TypeId TcpPacketFilter::GetTypeId() {
  static TypeId tid = TypeId("ns3::TcpPacketFilter")
                          .SetParent<Ipv4PacketFilter>()
                          .SetGroupName("TrafficControl")
                          .AddConstructor<TcpPacketFilter>();
  return tid;
}

TcpPacketFilter::TcpPacketFilter() {}
TcpPacketFilter::~TcpPacketFilter() {}

int32_t TcpPacketFilter::DoClassify(Ptr<QueueDiscItem> item) const {
  return 42;
}

// Check the protocol of the queued item
bool TcpPacketFilter::CheckProtocol(Ptr<QueueDiscItem> item) const {
  std::cout << item->GetProtocol() << std::endl;
  return true;
}

}; // namespace ns3
