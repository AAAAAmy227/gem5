#ifndef __CPU_SUMCHECK_CAUSAL_TRAFFIC_HH__
#define __CPU_SUMCHECK_CAUSAL_TRAFFIC_HH__

#include <set>
#include <vector>

#include "base/statistics.hh"
#include "mem/port.hh"
#include "mem/ruby/network/garnet/CommonTypes.hh"
#include "params/SumcheckCausalTraffic.hh"
#include "sim/clocked_object.hh"
#include "sim/eventq.hh"
#include "sim/sim_exit.hh"
#include "sim/sim_object.hh"
#include "sim/stats.hh"

namespace gem5
{

class Packet;

class SumcheckCausalTraffic : public ClockedObject
{
  public:
    typedef SumcheckCausalTrafficParams Params;
    SumcheckCausalTraffic(const Params &p);

    void init() override;

    void tick();

    Port &getPort(const std::string &if_name,
                  PortID idx=InvalidPortID) override;

    void notifyArrival(int msgType);
    void notifyArrivalByAddr(Addr addr);

    static Addr encodeAddr(int destId, int msg_type,
                           unsigned blockSizeBits);
    static int decodeMsgType(Addr addr,
                             unsigned blockSizeBits);
  protected:
    EventFunctionWrapper tickEvent;

    class CpuPort : public RequestPort
    {
        SumcheckCausalTraffic *tester;

      public:

        CpuPort(const std::string &_name, SumcheckCausalTraffic *_tester)
            : RequestPort(_name), tester(_tester)
        { }

      protected:

        virtual bool recvTimingResp(PacketPtr pkt);

        virtual void recvReqRetry();
    };

    CpuPort cachePort;

    PacketPtr retryPkt;
    unsigned blockSizeBits;

    //  ========== Basic config for sumcheck ==========
    int nodeId;
    int nodeType;

    int sourceId;
    int numWorkers;
    std::vector<int> workerIds;

    int numSumcheckRounds;
    int simulateRounds;
    int currentRound;

    int polyDegree;
    int elementBytes;

    // latency of computing 256 bits * 256 bits mod prime
    int multiplyLatency;
    // latency of computing 256 bits + 256 bits
    int addLatency;

    //  ========== Source state ==========
    int sourceState;

    int sendVectorWorkerIdx;
    int sendVectorPacketIdx;

    // Stage of sending challenge
    int sendChalWorkerIdx;

    // expected == sent (2^{n-i})
    int responseElementPacketReceived;

    // expected == # workers
    int responseAggregateReceived;
    Tick aggregateStartTick;

    // ========== Worker state ==========
    bool chalThisRoundReceived;

    // Received but uncomputed vector element packets
    int pendingVectorPacketCount;

    // expected == 2^{n-i} / #workers
    int completedVectorPacketCount;

    bool computingVectorPacket;
    Tick computeStartTick;

    RequestorID requestorId;

    int numPacketsSent;
    int injVnet;

    void completeRequest(PacketPtr pkt);
    void sendPkt(PacketPtr pkt);
    void doRetry();

    // Source activity
    void srcTickSendVector();
    void srcTickSendChallenge();
    void srcTickWaitResponse();
    void srcTickAggregate();

    void workerTick();
    PacketPtr createSumcheckPacket(
      int destId, int msgType, unsigned packetSize);
};

} // namespace gem5

#endif // __CPU_SUMCHECK_CAUSAL_TRAFFIC_HH__
