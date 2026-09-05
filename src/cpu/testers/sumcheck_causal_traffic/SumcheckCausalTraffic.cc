#include "cpu/testers/sumcheck_causal_traffic/SumcheckCausalTraffic.hh"

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

Addr
SumcheckCausalTraffic::encodeAddr(int destId, int msg_type,
                                   unsigned blockSizeBits)
{
    return ((Addr)destId << blockSizeBits) | ((Addr)(uint8_t)msg_type << 17);
}

int
SumcheckCausalTraffic::decodeMsgType(Addr addr, unsigned blockSizeBits)
{
    return (int)((addr >> 17) & 0x3);
}

SumcheckCausalTraffic::SumcheckCausalTraffic(const Params &p)
    : ClockedObject(p),
      tickEvent([this]{ tick(); }, name(), false, Event::CPU_Tick_Pri),
      cachePort(name() + ".sumcheck_port", this),
      retryPkt(nullptr),
      blockSizeBits(p.block_offset),
      nodeId(p.node_id),
      nodeType(p.node_type),
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
      sendVectorWorkerIdx(0),
      sendVectorPacketIdx(0),
      sendChalWorkerIdx(0),
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
    for (int i = 0; i < numWorkers; i++) {
        workerIds.push_back(p.worker_ids[i]);
    }

    int minPackets = 1 << (numSumcheckRounds - simulateRounds);
    fatal_if(minPackets % numWorkers != 0,
             "Sumcheck: 2^{%d-%d}=%d not divisible by %d workers",
             numSumcheckRounds, simulateRounds, minPackets, numWorkers);

    DPRINTF(SumcheckCausalTraffic,
            "SumcheckCausalTraffic[%d]: nodeType=%d, numWorkers=%d, "
            "numRounds=%d, simulateRounds=%d, polyDegree=%d\n",
            nodeId, nodeType, numWorkers, numSumcheckRounds,
            simulateRounds, polyDegree);

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
    int destWorkerId = workerIds[sendChalWorkerIdx];
    PacketPtr pkt = createSumcheckPacket(destWorkerId,
                CHALLENGE_, elementBytes);
    DPRINTF(SumcheckCausalTraffic,
            "SRC Round %d: sendChallenge to Worker %d\n",
            currentRound, destWorkerId);

    sendPkt(pkt);
    sendChalWorkerIdx += 1;

    if (sendChalWorkerIdx >= numWorkers) {
        DPRINTF(SumcheckCausalTraffic,
                "SRC enters Round %d State [SEND_VECTOR_] at tick %d",
            currentRound, curTick());
        sourceState = SEND_VECTOR_;
        sendChalWorkerIdx = 0;
    }
}

void
SumcheckCausalTraffic::srcTickSendVector()
{
    int totalPackets = (1 << (numSumcheckRounds - currentRound));
    int elementsPerPacket = 0;

    if (currentRound == 1) {
        elementsPerPacket = 2 * polyDegree;
    } else {
        elementsPerPacket = 4 * polyDegree;
    }
    int destWorkerId = workerIds[sendVectorWorkerIdx];
    PacketPtr pkt = createSumcheckPacket(destWorkerId,
                VECTOR_ELEMENT_, elementsPerPacket * elementBytes);

    DPRINTF(SumcheckCausalTraffic,
            "SRC Round %d: sendVector[%d/%d] to Worker %d\n",
            currentRound, sendVectorPacketIdx + 1,
            (1 << (numSumcheckRounds - currentRound)), destWorkerId);

    sendPkt(pkt);
    sendVectorPacketIdx += 1;

    sendVectorWorkerIdx += 1;
    if (sendVectorWorkerIdx >= numWorkers) {
        sendVectorWorkerIdx = 0;
    }

    if (sendVectorPacketIdx >= totalPackets) {
        DPRINTF(SumcheckCausalTraffic,
                "SRC enters Round %d State [WAIT_RESPONSE] at tick %d",
                currentRound, curTick());
        sourceState = WAIT_RESPONSE_;
        sendVectorWorkerIdx = sendVectorPacketIdx = 0;
    }
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

    DPRINTF(SumcheckCausalTraffic, "SRC enters to Round %d at tick %d",
        currentRound, curTick());

    if (currentRound > simulateRounds) {
        return;
    }
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
                (1 << (numSumcheckRounds - currentRound)) / numWorkers);

        int elementsPerPacket = 0;
        if (currentRound == 1) {
            elementsPerPacket = polyDegree;
        } else {
            elementsPerPacket = 2 * polyDegree;
        }
        PacketPtr pkt = createSumcheckPacket(sourceId,
            RESPONSE_ELEMENT_, elementsPerPacket * elementBytes);
        sendPkt(pkt);

        computingVectorPacket = false;
        pendingVectorPacketCount--;
        completedVectorPacketCount++;
        if (completedVectorPacketCount ==
            (1 << (numSumcheckRounds - currentRound)) / numWorkers) {

            DPRINTF(SumcheckCausalTraffic,
                    "WRK %d send aggregate (round %d), tick=%d\n",
                    nodeId, currentRound, curTick());

            PacketPtr aggregate_pkt = createSumcheckPacket(sourceId,
                RESPONSE_AGGREGATE_, (polyDegree + 1) * elementBytes);
            sendPkt(aggregate_pkt);

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
    int msgType = decodeMsgType(addr, blockSizeBits);

    DPRINTF(SumcheckCausalTraffic,
            "Node %d notifyArrivalByAddr: addr=0x%x msgType=%d\n",
            nodeId, addr, msgType);

    notifyArrival(msgType);
}

PacketPtr
SumcheckCausalTraffic::createSumcheckPacket(int destId, int msgType,
                                            unsigned packetSize)
{
    Addr paddr = encodeAddr(destId, msgType, blockSizeBits);
    unsigned access_size = 1;
    RequestPtr req = std::make_shared<Request>(
        paddr, access_size, Request::Flags(), requestorId);

    req->setContext(nodeId);
    PacketPtr pkt = new Packet(req, MemCmd::WriteReq);
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
    tester->doRetry();
}

void
SumcheckCausalTraffic::sendPkt(PacketPtr pkt)
{
    if (!cachePort.sendTimingReq(pkt)) {
        retryPkt = pkt; // RubyPort will retry sending
    }
    numPacketsSent++;
}

Port &
SumcheckCausalTraffic::getPort(const std::string &if_name, PortID idx)
{
    if (if_name == "test")
        return cachePort;
    else
        return ClockedObject::getPort(if_name, idx);
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
SumcheckCausalTraffic::doRetry()
{
    if (cachePort.sendTimingReq(retryPkt)) {
        retryPkt = NULL;
    }
}

} // namespace gem5
