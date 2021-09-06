#ifndef TCP_PACKET_FILTER_H
#define TCP_PACKET_FILTER_H

#include "ns3/ipv4-packet-filter.h"
#include "ns3/ipv4-queue-disc-item.h"
#include "ns3/tcp-header.h"
#include "ns3/type-id.h"

namespace ns3 {

class TcpPacketFilter : public Ipv4PacketFilter {
public:
  static TypeId GetTypeId();
  TcpPacketFilter();
  virtual ~TcpPacketFilter();

private:
  virtual int32_t DoClassify(Ptr<QueueDiscItem> item) const;
  virtual bool CheckProtocol(Ptr<QueueDiscItem> item) const;
};

};     // namespace ns3
#endif /* TCP_PACKET_FILTER */
