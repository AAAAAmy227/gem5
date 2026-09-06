#ifndef __CPU_SUMCHECK_CAUSAL_TRAFFIC_HH__
#define __CPU_SUMCHECK_CAUSAL_TRAFFIC_HH__

#include <deque>
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
    ~SumcheckCausalTraffic() override;

    void init() override;

    void tick();

    Port &getPort(const std::string &if_name,
                  PortID idx=InvalidPortID) override;

    void notifyArrival(int msgType);
    void notifyArrivalByAddr(Addr addr);

    Addr encodeAddr(int destId, int msgType) const;
    int decodeMsgType(Addr addr) const;
  protected:
    EventFunctionWrapper tickEvent;

    class CpuPort : public RequestPort
    {
        SumcheckCausalTraffic *tester;
        PortID laneId;

      public:

        CpuPort(const std::string &_name, SumcheckCausalTraffic *_tester,
                PortID id)
            : RequestPort(_name, id), tester(_tester), laneId(id)
        { }

      protected:

        virtual bool recvTimingResp(PacketPtr pkt);

        virtual void recvReqRetry();
    };

    std::vector<CpuPort *> cachePorts;
    std::vector<std::deque<PacketPtr>> outboundQueues;
    std::vector<bool> retryPending;
    unsigned blockSizeBits;
    unsigned destinationBits;

    //  ========== Basic config for sumcheck ==========
    int nodeId;
    int nodeType;
    int workerIndex;
    int workersPerCluster;
    int numClusters;
    int numInjectionLanes;

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

    int sendVectorPacketIdx;
    int preparedVectorRound;
    int preparedChallengeRound;
    std::vector<std::deque<int>> vectorDestinations;
    std::vector<std::deque<int>> challengeDestinations;

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
    void enqueuePkt(PacketPtr pkt, int lane=0);
    void trySend(int lane);
    void doRetry(PortID lane);
    int laneForWorkerIndex(int index) const;
    int workerAtSchedulePosition(int position) const;
    int schedulePositionForWorker(int index) const;
    bool allDestinationQueuesEmpty(
        const std::vector<std::deque<int>> &queues) const;
    void prepareChallengeDestinations();
    void prepareVectorDestinations();

    // Source activity
    void srcTickSendVector();
    void srcTickSendChallenge();
    void srcTickWaitResponse();
    void srcTickAggregate();

    void workerTick();
    int vectorPacketsForWorker() const;
    PacketPtr createSumcheckPacket(
      int destId, int msgType, unsigned packetSize);
};

} // namespace gem5

#endif // __CPU_SUMCHECK_CAUSAL_TRAFFIC_HH__
