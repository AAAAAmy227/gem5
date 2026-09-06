#include "cpu/testers/sumcheck_causal_traffic/SumcheckCausalTraffic.hh"

#include <algorithm>
#include <cmath>
#include <string>
#include <vector>

#include "base/logging.hh"
#include "debug/SumcheckCausalTraffic.hh"
#include "mem/packet.hh"
#include "mem/port.hh"
#include "mem/request.hh"
#include "mem/ruby/network/garnet/CommonTypes.hh"
#include "sim/sim_events.hh"
#include "sim/stats.hh"
#include "sim/system.hh"

namespace gem5
{

using namespace ruby::garnet;

constexpr unsigned MessageTypeBits = 2;
constexpr Addr MessageTypeMask = (1U << MessageTypeBits) - 1;

Addr
SumcheckCausalTraffic::encodeAddr(int destId, int msgType) const
{
    const unsigned messageTypeShift = blockSizeBits + destinationBits;
    return ((Addr)destId << blockSizeBits) |
           ((Addr)(uint8_t)msgType << messageTypeShift);
}

int
SumcheckCausalTraffic::decodeMsgType(Addr addr) const
{
    const unsigned messageTypeShift = blockSizeBits + destinationBits;
    return (int)((addr >> messageTypeShift) & MessageTypeMask);
}

SumcheckCausalTraffic::SumcheckCausalTraffic(const Params &p)
    : ClockedObject(p),
      tickEvent([this]{ tick(); }, name(), false, Event::CPU_Tick_Pri),
      blockSizeBits(p.block_offset),
      destinationBits(p.destination_bits),
      nodeId(p.node_id),
      nodeType(p.node_type),
      workerIndex(p.worker_index),
      workersPerCluster(p.workers_per_cluster),
      numClusters(0),
      numInjectionLanes(p.port_test_connection_count),
      sourceId(p.source_id),
      numWorkers(p.num_workers),
      numSumcheckRounds(p.num_sumcheck_rounds),
      simulateRounds(p.simulate_rounds),
      currentRound(1),
      polyDegree(p.poly_degree),
      elementBytes(p.element_bytes),
      multiplyLatency(p.multiply_latency),
      addLatency(p.add_latency),
      sourceState(SEND_VECTOR_),
      sendVectorPacketIdx(0),
      preparedVectorRound(0),
      preparedChallengeRound(0),
      responseElementPacketReceived(0),
      responseAggregateReceived(0),
      aggregateStartTick(0),
      chalThisRoundReceived(false),
      pendingVectorPacketCount(0),
      completedVectorPacketCount(0),
      computingVectorPacket(false),
      computeStartTick(0),
      requestorId(p.system->getRequestorId(this)),
      numPacketsSent(0),
      injVnet(p.inj_vnet)
{
    fatal_if(numWorkers <= 0, "Sumcheck requires at least one worker");
    fatal_if(numInjectionLanes <= 0,
             "Sumcheck tester %d has no connected injection port", nodeId);
    fatal_if(workersPerCluster <= 0 ||
             numWorkers % workersPerCluster != 0,
             "Invalid workers_per_cluster=%d for %d workers",
             workersPerCluster, numWorkers);
    numClusters = numWorkers / workersPerCluster;
    fatal_if(destinationBits == 0,
             "Sumcheck destination_bits must be positive");
    for (int lane = 0; lane < numInjectionLanes; ++lane) {
        cachePorts.push_back(new CpuPort(
            csprintf("%s.sumcheck_port[%d]", name(), lane), this, lane));
    }
    outboundQueues.resize(numInjectionLanes);
    retryPending.resize(numInjectionLanes, false);
    vectorDestinations.resize(numInjectionLanes);
    challengeDestinations.resize(numInjectionLanes);
    for (int i = 0; i < numWorkers; i++) {
        workerIds.push_back(p.worker_ids[i]);
    }
    const int highestEndpoint = std::max(
        sourceId, *std::max_element(workerIds.begin(), workerIds.end()));
    fatal_if(highestEndpoint >= (1ULL << destinationBits),
             "Endpoint %d does not fit in %u destination bits",
             highestEndpoint, destinationBits);
    fatal_if(blockSizeBits + destinationBits + MessageTypeBits >
             sizeof(Addr) * 8,
             "Sumcheck address encoding exceeds %u-bit Addr",
             (unsigned)(sizeof(Addr) * 8));

    int minPackets = 1 << (numSumcheckRounds - simulateRounds);
    fatal_if(minPackets < numWorkers,
             "Sumcheck: 2^{%d-%d}=%d provides no work for some of %d workers",
             numSumcheckRounds, simulateRounds, minPackets, numWorkers);
    fatal_if(nodeType == WORKER_ &&
             (workerIndex < 0 || workerIndex >= numWorkers),
             "Sumcheck worker %d has invalid worker index %d",
             nodeId, workerIndex);

    DPRINTF(SumcheckCausalTraffic,
            "SumcheckCausalTraffic[%d]: nodeType=%d, numWorkers=%d, "
            "numRounds=%d, simulateRounds=%d, polyDegree=%d\n",
            nodeId, nodeType, numWorkers, numSumcheckRounds,
            simulateRounds, polyDegree);

}

SumcheckCausalTraffic::~SumcheckCausalTraffic()
{
    for (auto *port : cachePorts) {
        delete port;
    }
}

void
SumcheckCausalTraffic::init()
{
    numPacketsSent = 0;
    if (nodeType == NEITHER_) {
        return;
    }
    schedule(tickEvent, clockEdge(Cycles(1)));
}

void
SumcheckCausalTraffic::tick()
{
    if (nodeType == NEITHER_) {
        return;
    }

    if (nodeType == SOURCE_ && curTick() % 10000 == 0) {
        DPRINTF(SumcheckCausalTraffic,
                "SRC heartbeat: tick=%d round=%d state=%d\n",
                curTick(), currentRound, sourceState);
    }

    if (currentRound > simulateRounds) {
        if (nodeType == SOURCE_) {
            exitSimLoop("Sumcheck simulation completed all rounds");
        }
        return;
    }

    for (int lane = 0; lane < numInjectionLanes; ++lane) {
        trySend(lane);
    }

    switch (nodeType) {
    case SOURCE_:
        switch (sourceState) {
        case SEND_CHALLENGE_: srcTickSendChallenge(); break;
        case SEND_VECTOR_:    srcTickSendVector();    break;
        case WAIT_RESPONSE_:  srcTickWaitResponse();  break;
        case AGGREGATE_:      srcTickAggregate();     break;
        }
        break;

    case WORKER_:
        workerTick();
        break;

    default:
        break;
    }

    schedule(tickEvent, clockEdge(Cycles(1)));
}

void
SumcheckCausalTraffic::srcTickSendChallenge()
{
    prepareChallengeDestinations();
    for (int lane = 0; lane < numInjectionLanes; ++lane) {
        if (challengeDestinations[lane].empty()) {
            continue;
        }
        int destWorkerId = challengeDestinations[lane].front();
        challengeDestinations[lane].pop_front();
        enqueuePkt(createSumcheckPacket(
            destWorkerId, CHALLENGE_, elementBytes), lane);
        DPRINTF(SumcheckCausalTraffic,
                "SRC Round %d lane %d: challenge to Worker %d\n",
                currentRound, lane, destWorkerId);
    }

    if (allDestinationQueuesEmpty(challengeDestinations)) {
        DPRINTF(SumcheckCausalTraffic,
                "SRC enters Round %d State [SEND_VECTOR_] at tick %d",
            currentRound, curTick());
        sourceState = SEND_VECTOR_;
    }
}

void
SumcheckCausalTraffic::srcTickSendVector()
{
    prepareVectorDestinations();
    int elementsPerPacket = 0;

    if (currentRound == 1) {
        elementsPerPacket = 2 * polyDegree;
    } else {
        elementsPerPacket = 4 * polyDegree;
    }
    for (int lane = 0; lane < numInjectionLanes; ++lane) {
        if (vectorDestinations[lane].empty()) {
            continue;
        }
        int destWorkerId = vectorDestinations[lane].front();
        vectorDestinations[lane].pop_front();
        enqueuePkt(createSumcheckPacket(
            destWorkerId, VECTOR_ELEMENT_,
            elementsPerPacket * elementBytes), lane);
        ++sendVectorPacketIdx;
        DPRINTF(SumcheckCausalTraffic,
                "SRC Round %d lane %d: sendVector[%d] to Worker %d\n",
                currentRound, lane, sendVectorPacketIdx, destWorkerId);
    }

    if (allDestinationQueuesEmpty(vectorDestinations)) {
        DPRINTF(SumcheckCausalTraffic,
                "SRC enters Round %d State [WAIT_RESPONSE] at tick %d",
                currentRound, curTick());
        sourceState = WAIT_RESPONSE_;
        sendVectorPacketIdx = 0;
    }
}

int
SumcheckCausalTraffic::laneForWorkerIndex(int index) const
{
    const int cluster = index / workersPerCluster;
    return cluster % numInjectionLanes;
}

int
SumcheckCausalTraffic::workerAtSchedulePosition(int position) const
{
    // Transpose cluster-major worker numbering so consecutive sends rotate
    // across clusters. For four 16-worker clusters this is
    // 0,16,32,48; 1,17,33,49; ... .
    const int cluster = position % numClusters;
    const int localWorker = position / numClusters;
    return cluster * workersPerCluster + localWorker;
}

int
SumcheckCausalTraffic::schedulePositionForWorker(int index) const
{
    const int cluster = index / workersPerCluster;
    const int localWorker = index % workersPerCluster;
    return localWorker * numClusters + cluster;
}

bool
SumcheckCausalTraffic::allDestinationQueuesEmpty(
    const std::vector<std::deque<int>> &queues) const
{
    return std::all_of(queues.begin(), queues.end(),
                       [](const auto &queue) { return queue.empty(); });
}

void
SumcheckCausalTraffic::prepareChallengeDestinations()
{
    if (preparedChallengeRound == currentRound) {
        return;
    }
    for (auto &queue : challengeDestinations) {
        queue.clear();
    }
    for (int position = 0; position < numWorkers; ++position) {
        const int worker = workerAtSchedulePosition(position);
        challengeDestinations[laneForWorkerIndex(worker)].push_back(
            workerIds[worker]);
    }
    preparedChallengeRound = currentRound;
}

void
SumcheckCausalTraffic::prepareVectorDestinations()
{
    if (preparedVectorRound == currentRound) {
        return;
    }
    for (auto &queue : vectorDestinations) {
        queue.clear();
    }
    const int totalPackets = 1 << (numSumcheckRounds - currentRound);
    for (int packet = 0; packet < totalPackets; ++packet) {
        const int worker = workerAtSchedulePosition(packet % numWorkers);
        vectorDestinations[laneForWorkerIndex(worker)].push_back(
            workerIds[worker]);
    }
    preparedVectorRound = currentRound;
}

void
SumcheckCausalTraffic::srcTickWaitResponse()
{
    int expectedPackets = (1 << (numSumcheckRounds - currentRound));
    int expectedAggregates = numWorkers;

    if (curTick() % 1000 == 0) {
        DPRINTF(SumcheckCausalTraffic,
                "SRC Round %d WAIT: respElem=%d/%d respAgg=%d/%d@tick%d\n",
                currentRound,
                responseElementPacketReceived, expectedPackets,
                responseAggregateReceived, expectedAggregates, curTick());
    }

    if (responseElementPacketReceived >= expectedPackets &&
        responseAggregateReceived >= expectedAggregates) {

        DPRINTF(SumcheckCausalTraffic,
            "SRC enters Round %d State [AGGREGATE_] at tick %d",
            currentRound, curTick());

        sourceState = AGGREGATE_;
        aggregateStartTick = curTick();
    }
}

void
SumcheckCausalTraffic::srcTickAggregate()
{
    Tick now = curTick();

    if (now % 10 == 0) {
        DPRINTF(SumcheckCausalTraffic,
            "SRC at Round %d State [AGGREGATE_] at tick %d",
            currentRound, curTick());
    }

    int aggregateCycles = addLatency * numWorkers * (polyDegree + 1);
    Tick aggregateTicks = cyclesToTicks(Cycles(aggregateCycles));
    if (now - aggregateStartTick < aggregateTicks) {
        return;
    }
    sourceState = SEND_CHALLENGE_;
    responseElementPacketReceived = 0;
    responseAggregateReceived = 0;
    currentRound++;


    if (currentRound > simulateRounds) {
        DPRINTF(SumcheckCausalTraffic, "SRC enters to Round %d at tick %d",
            currentRound, curTick());
        return;
    }
}

int
SumcheckCausalTraffic::vectorPacketsForWorker() const
{
    const int totalPackets = 1 << (numSumcheckRounds - currentRound);
    const int packetsPerWorker = totalPackets / numWorkers;
    const int remainder = totalPackets % numWorkers;
    return packetsPerWorker +
        (schedulePositionForWorker(workerIndex) < remainder ? 1 : 0);
}

void
SumcheckCausalTraffic::workerTick()
{
    Tick now = curTick();
    int deg = polyDegree;
    int packetComputeCycles =
        (deg + (deg + 1) * (deg - 1)) * multiplyLatency
        + (deg + 1) * addLatency;
    if (currentRound == 1) {
        packetComputeCycles -= deg * multiplyLatency;
    }
    Tick packetComputeTicks = cyclesToTicks(
        Cycles(packetComputeCycles));
    if (computingVectorPacket &&
       (now - computeStartTick < packetComputeTicks)) {
        return;
    }

    if (computingVectorPacket) {

        DPRINTF(SumcheckCausalTraffic,
                "WRK %d compute done -> send respElem (completed=%d/%d)\n",
                nodeId, completedVectorPacketCount + 1,
                vectorPacketsForWorker());

        int elementsPerPacket = 0;
        if (currentRound == 1) {
            elementsPerPacket = polyDegree;
        } else {
            elementsPerPacket = 2 * polyDegree;
        }
        PacketPtr pkt = createSumcheckPacket(sourceId,
            RESPONSE_ELEMENT_, elementsPerPacket * elementBytes);
        enqueuePkt(pkt);

        computingVectorPacket = false;
        pendingVectorPacketCount--;
        completedVectorPacketCount++;
        if (completedVectorPacketCount == vectorPacketsForWorker()) {

            DPRINTF(SumcheckCausalTraffic,
                    "WRK %d send aggregate (round %d), tick=%d\n",
                    nodeId, currentRound, curTick());

            PacketPtr aggregate_pkt = createSumcheckPacket(sourceId,
                RESPONSE_AGGREGATE_, (polyDegree + 1) * elementBytes);
            enqueuePkt(aggregate_pkt);

            currentRound++;
            pendingVectorPacketCount = 0;
            completedVectorPacketCount = 0;
            chalThisRoundReceived = false;
        }
    }

    if ((currentRound == 1 || chalThisRoundReceived)
        && pendingVectorPacketCount > 0) {

        DPRINTF(SumcheckCausalTraffic,
            "WRK %d start computing (round=%d, completed=%d, tick=%d)\n",
            nodeId, currentRound, completedVectorPacketCount, curTick());

        computeStartTick = curTick();
        computingVectorPacket = true;
    }
}

void
SumcheckCausalTraffic::notifyArrival(int msgType)
{

    DPRINTF(SumcheckCausalTraffic,
            "Node %d (%s) notifyArrival: %s\n",
            nodeId, nodeType == SOURCE_ ? "SRC" : "WRK",
            msgType == VECTOR_ELEMENT_ ? "VECTOR" :
            msgType == CHALLENGE_ ? "CHALLENGE" :
            msgType == RESPONSE_ELEMENT_ ? "RESP_ELEM" :
            msgType == RESPONSE_AGGREGATE_ ? "RESP_AGG" : "UNKNOWN");

    if (nodeType == SOURCE_) {
        if (msgType == RESPONSE_ELEMENT_) {
            responseElementPacketReceived++;
        } else if (msgType == RESPONSE_AGGREGATE_) {
            responseAggregateReceived++;
        }

        DPRINTF(SumcheckCausalTraffic,
            "Node %d SRCE: respElem=%d/%d respAgg=%d/%d\n",
            nodeId, responseElementPacketReceived,
            (1 << (numSumcheckRounds - currentRound)),
            responseAggregateReceived, numWorkers);
    } else if (nodeType == WORKER_) {
        if (msgType == VECTOR_ELEMENT_) {
            pendingVectorPacketCount++;
        } else if (msgType == CHALLENGE_) {
            chalThisRoundReceived = true;
            computingVectorPacket = false;
        }
        DPRINTF(SumcheckCausalTraffic,
                "Node %d WKR: pending=%d completed=%d\n",
                nodeId, pendingVectorPacketCount,
                completedVectorPacketCount);
    }
}

void
SumcheckCausalTraffic::notifyArrivalByAddr(Addr addr)
{
    int msgType = decodeMsgType(addr);

    DPRINTF(SumcheckCausalTraffic,
            "Node %d notifyArrivalByAddr: addr=0x%x msgType=%d\n",
            nodeId, addr, msgType);

    notifyArrival(msgType);
}

PacketPtr
SumcheckCausalTraffic::createSumcheckPacket(int destId, int msgType,
                                            unsigned packetSize)
{
    Addr paddr = encodeAddr(destId, msgType);
    unsigned access_size = 1;
    RequestPtr req = std::make_shared<Request>(
        paddr, access_size, Request::Flags(), requestorId);

    // Ruby memory accesses must remain within one cache block, so keep the
    // functional access small and carry the modeled network size separately.
    req->setExtraData(packetSize);
    req->setContext(nodeId);
    PacketPtr pkt = new Packet(req, MemCmd::ReadReq);
    pkt->dataDynamic(new uint8_t[req->getSize()]);
    pkt->senderState = nullptr;
    return pkt;
}

bool
SumcheckCausalTraffic::CpuPort::recvTimingResp(PacketPtr pkt)
{
    tester->completeRequest(pkt);
    return true;
}

void
SumcheckCausalTraffic::CpuPort::recvReqRetry()
{
    tester->doRetry(laneId);
}

void
SumcheckCausalTraffic::enqueuePkt(PacketPtr pkt, int lane)
{
    fatal_if(lane < 0 || lane >= numInjectionLanes,
             "Invalid injection lane %d for tester %d", lane, nodeId);
    outboundQueues[lane].push_back(pkt);
    ++numPacketsSent;
    trySend(lane);
}

void
SumcheckCausalTraffic::trySend(int lane)
{
    if (retryPending[lane] || outboundQueues[lane].empty()) {
        return;
    }
    PacketPtr pkt = outboundQueues[lane].front();
    if (cachePorts[lane]->sendTimingReq(pkt)) {
        outboundQueues[lane].pop_front();
    } else {
        retryPending[lane] = true;
    }
}

Port &
SumcheckCausalTraffic::getPort(const std::string &if_name, PortID idx)
{
    if (if_name != "test") {
        return ClockedObject::getPort(if_name, idx);
    }
    fatal_if(idx < 0 || idx >= cachePorts.size(),
             "Unknown Sumcheck test port index %d", idx);
    return *cachePorts[idx];
}

void
SumcheckCausalTraffic::completeRequest(PacketPtr pkt)
{

    DPRINTF(SumcheckCausalTraffic,
            "Completed injection of %s packet for address %x\n",
            pkt->isWrite() ? "write" : "read\n",
            pkt->req->getPaddr());

    assert(pkt->isResponse());
    delete pkt;
}

void
SumcheckCausalTraffic::doRetry(PortID lane)
{
    fatal_if(lane < 0 || lane >= cachePorts.size(),
             "Retry on invalid Sumcheck lane %d", lane);
    fatal_if(!retryPending[lane] || outboundQueues[lane].empty(),
             "Unexpected retry on Sumcheck lane %d", lane);
    retryPending[lane] = false;
    trySend(lane);
    while (!retryPending[lane] && !outboundQueues[lane].empty()) {
        trySend(lane);
    }
}

} // namespace gem5
