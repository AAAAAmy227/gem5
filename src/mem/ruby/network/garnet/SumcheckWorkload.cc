#include "mem/ruby/network/garnet/SumcheckWorkload.hh"

#include <algorithm>
#include <fstream>
#include <iomanip>
#include <sstream>

#include "base/logging.hh"
#include "mem/ruby/common/MachineID.hh"
#include "mem/ruby/common/NetDest.hh"
#include "mem/ruby/protocol/CoherenceRequestType.hh"
#include "mem/ruby/protocol/MachineType.hh"
#include "mem/ruby/protocol/MessageSizeType.hh"
#include "mem/ruby/protocol/RequestMsg.hh"
#include "sim/sim_exit.hh"

namespace gem5
{
namespace ruby
{
namespace garnet
{

namespace
{

std::vector<std::string>
split(const std::string &text, char delimiter)
{
    std::vector<std::string> fields;
    std::stringstream stream(text);
    std::string field;
    while (std::getline(stream, field, delimiter))
        fields.push_back(field);
    return fields;
}

MachineID
machineForNode(int node)
{
    if (node < 64)
        return MachineID{MachineType_L1Cache, node};
    return MachineID{MachineType_Directory, node - 64};
}

} // anonymous namespace

SumcheckWorkload::SumcheckWorkload(const Params &p)
    : ClockedObject(p), injectionEvent([this] { injectReady(); },
          "Sumcheck causal ready injection"),
      watchdogEvent([this] { watchdog(); }, "Sumcheck causal watchdog"),
      localPhaseEvent([this] { runLocalPhase(); },
          "Sumcheck root-local Phase C"),
      mode(p.mode), reportFile(p.report_file), seed(p.seed),
      flitBytes(p.flit_bytes), watchdogCycles(p.watchdog_cycles),
      lastProgress(0), packetsInjected(0), packetsReceived(0),
      flitsInjected(0), flitsReceived(0), initialInjections(0),
      arrivalTriggeredInjections(0),
      traceDigest(1469598103934665603ULL),
      injectionDigest(1469598103934665603ULL), phaseCLocalRound(0)
{
    fatal_if(flitBytes == 0, "Sumcheck flit size must be positive");
    fatal_if(watchdogCycles == Cycles(0),
             "Sumcheck watchdog must be positive");
    parseAndValidate(p.events);
    injectionBuffers.assign(
        p.injection_buffers.begin(), p.injection_buffers.end());
    fatal_if(injectionBuffers.size() != 69,
             "Sumcheck workload requires 69 injection queues, got %d",
             injectionBuffers.size());
}

void
SumcheckWorkload::parseAndValidate(const std::vector<std::string> &records)
{
    fatal_if(records.empty(), "Sumcheck workload has no events");
    events.reserve(records.size());
    for (size_t index = 0; index < records.size(); ++index) {
        const auto fields = split(records[index], ';');
        fatal_if(fields.size() != 7 && fields.size() != 8,
                 "Malformed Sumcheck event record %d", index);
        Event event;
        event.id = fields[0];
        event.source = std::stoi(fields[1]);
        event.destination = std::stoi(fields[2]);
        event.bytes = std::stoul(fields[3]);
        event.phase = fields[4];
        event.round = std::stoi(fields[5]);
        event.kind = fields[6];
        if (fields.size() == 8 && !fields[7].empty())
            event.dependencyIds = split(fields[7], ',');

        fatal_if(event.id.empty(), "Sumcheck event %d has no ID", index);
        fatal_if(eventIndex.count(event.id),
                 "Duplicate Sumcheck event ID %s", event.id);
        fatal_if(event.source < 0 || event.source >= 69 ||
                 event.destination < 0 || event.destination >= 69 ||
                 event.source == event.destination,
                 "Sumcheck event %s has invalid endpoints %d -> %d",
                 event.id, event.source, event.destination);
        fatal_if(event.bytes != 32 && event.bytes != 128,
                 "Sumcheck event %s has invalid byte count %u",
                 event.id, event.bytes);
        eventIndex.emplace(event.id, index);
        updateDigest(traceDigest, records[index]);
        events.push_back(std::move(event));
    }

    for (size_t index = 0; index < events.size(); ++index) {
        auto &event = events[index];
        std::set<size_t> unique;
        for (const auto &dependencyId : event.dependencyIds) {
            auto found = eventIndex.find(dependencyId);
            fatal_if(found == eventIndex.end(),
                     "Sumcheck event %s has missing dependency %s",
                     event.id, dependencyId);
            const size_t dependency = found->second;
            fatal_if(dependency >= index,
                     "Sumcheck event %s has forward/invalid dependency %s",
                     event.id, dependencyId);
            fatal_if(!unique.insert(dependency).second,
                     "Sumcheck event %s repeats dependency %s",
                     event.id, dependencyId);
            event.dependencies.push_back(dependency);
            events[dependency].dependents.push_back(index);
        }
        event.remaining = event.dependencies.size();
        if (event.remaining == 0)
            pendingReady.insert(index);
    }
}

void
SumcheckWorkload::startup()
{
    lastProgress = curTick();
    schedule(injectionEvent, clockEdge(Cycles(1)));
    schedule(watchdogEvent, clockEdge(watchdogCycles));
}

void
SumcheckWorkload::injectReady()
{
    const std::vector<size_t> ready(pendingReady.begin(), pendingReady.end());
    pendingReady.clear();
    for (size_t index : ready)
        inject(index);
}

void
SumcheckWorkload::inject(size_t index)
{
    Event &event = events.at(index);
    fatal_if(event.injected || event.remaining != 0,
             "Invalid injection state for Sumcheck event %s", event.id);
    for (size_t dependency : event.dependencies) {
        fatal_if(!events[dependency].arrived,
                 "Sumcheck event %s injected before dependency %s arrived",
                 event.id, events[dependency].id);
    }

    MessageBuffer *buffer = injectionBuffers.at(event.source);
    fatal_if(!buffer->areNSlotsAvailable(1, curTick()),
             "Sumcheck source queue unexpectedly full for event %s",
             event.id);
    auto message = std::make_shared<RequestMsg>(curTick());
    message->setaddr(static_cast<Addr>(index) << 6);
    message->setType(CoherenceRequestType_MSG);
    message->setRequestor(machineForNode(event.source));
    NetDest destination;
    destination.add(machineForNode(event.destination));
    message->setDestination(destination);
    message->setMessageSize(MessageSizeType_Control);
    message->setSumcheckEventId(index);
    message->setMessageSizeBytes(event.bytes);

    event.injected = true;
    event.injectedAt = curTick();
    ++packetsInjected;
    flitsInjected += (event.bytes + flitBytes - 1) / flitBytes;
    if (event.dependencies.empty())
        ++initialInjections;
    else
        ++arrivalTriggeredInjections;
    updateDigest(injectionDigest, event.id);
    buffer->enqueue(message, curTick(), cyclesToTicks(Cycles(1)));
}

void
SumcheckWorkload::notifyArrival(uint64_t event_id, int destination_ni)
{
    fatal_if(event_id >= events.size(),
             "Unknown Sumcheck arrival event ID %llu", event_id);
    Event &event = events[event_id];
    fatal_if(!event.injected, "Sumcheck event %s arrived before injection",
             event.id);
    fatal_if(event.arrived, "Duplicate Sumcheck arrival for event %s",
             event.id);
    fatal_if(destination_ni != event.destination,
             "Sumcheck event %s arrived at NI %d, expected NI %d",
             event.id, destination_ni, event.destination);

    event.arrived = true;
    event.arrivedAt = curTick();
    ++packetsReceived;
    flitsReceived += (event.bytes + flitBytes - 1) / flitBytes;
    lastProgress = curTick();
    const std::string roundKey =
        event.phase + ":" + std::to_string(event.round);
    roundCompletion[roundKey] = curTick();

    for (size_t successorIndex : event.dependents) {
        Event &successor = events[successorIndex];
        fatal_if(successor.remaining == 0,
                 "Dependency accounting underflow for event %s",
                 successor.id);
        --successor.remaining;
        if (successor.remaining == 0)
            pendingReady.insert(successorIndex);
    }

    if (packetsReceived == events.size()) {
        // Phase C contains two root-local rounds and deliberately injects no
        // messages.  Model one controller cycle for each before completion.
        schedule(localPhaseEvent, clockEdge(Cycles(1)));
        return;
    }

    // Reinjection is deliberately deferred until the next endpoint clock:
    // the predecessor tail has ejected and its VC-free credit has been sent.
    if (!pendingReady.empty() && !injectionEvent.scheduled())
        schedule(injectionEvent, clockEdge(Cycles(1)));
}

void
SumcheckWorkload::runLocalPhase()
{
    fatal_if(packetsReceived != events.size(),
             "Sumcheck Phase C began before all network messages arrived");
    fatal_if(phaseCLocalRound < 0 || phaseCLocalRound >= 2,
             "Invalid Sumcheck Phase C local round");
    roundCompletion["C:" + std::to_string(phaseCLocalRound)] = curTick();
    ++phaseCLocalRound;
    if (phaseCLocalRound < 2)
        schedule(localPhaseEvent, clockEdge(Cycles(1)));
    else
        finish();
}

void
SumcheckWorkload::watchdog()
{
    const Tick limit = cyclesToTicks(watchdogCycles);
    if (curTick() - lastProgress >= limit) {
        const std::string state = stuckState();
        fatal("Sumcheck causal watchdog: %s", state);
    }
    schedule(watchdogEvent, lastProgress + limit);
}

std::string
SumcheckWorkload::stuckState() const
{
    std::ostringstream output;
    output << "injected=" << packetsInjected
           << " received=" << packetsReceived
           << " outstanding=" << (packetsInjected - packetsReceived);
    int shown = 0;
    for (const auto &event : events) {
        if (event.arrived)
            continue;
        output << " | " << event.id << " " << event.source << "->"
               << event.destination << " kind=" << event.kind
               << " injected=" << event.injected
               << " unmet=" << event.remaining;
        if (++shown == 8)
            break;
    }
    return output.str();
}

void
SumcheckWorkload::finish()
{
    fatal_if(packetsInjected != packetsReceived ||
             flitsInjected != flitsReceived || !pendingReady.empty(),
             "Sumcheck completion accounting mismatch");
    std::ofstream output(reportFile);
    fatal_if(!output, "Cannot open Sumcheck report %s", reportFile);
    output << "{\n"
           << "  \"mode\": \"" << mode << "\",\n"
           << "  \"seed\": " << seed << ",\n"
           << "  \"trace_events\": " << events.size() << ",\n"
           << "  \"packets_injected\": " << packetsInjected << ",\n"
           << "  \"packets_received\": " << packetsReceived << ",\n"
           << "  \"flits_injected\": " << flitsInjected << ",\n"
           << "  \"flits_received\": " << flitsReceived << ",\n"
           << "  \"outstanding_packets\": 0,\n"
           << "  \"initial_injections\": " << initialInjections << ",\n"
           << "  \"arrival_triggered_injections\": "
           << arrivalTriggeredInjections << ",\n"
           << "  \"endpoint_ejections\": " << packetsReceived << ",\n"
           << "  \"flit_bytes\": " << flitBytes << ",\n"
           << "  \"completion_tick\": " << curTick() << ",\n"
           << "  \"phase_c_local_rounds\": " << phaseCLocalRound << ",\n"
           << "  \"trace_digest_fnv64\": \"" << std::hex
           << traceDigest << "\",\n"
           << "  \"injection_digest_fnv64\": \""
           << injectionDigest << std::dec << "\",\n"
           << "  \"eject_then_reinject\": true,\n"
           << "  \"endpoint_mapping\": "
           << "\"logical n -> NI n -> ExtLink n -> router n\",\n"
           << "  \"round_completion_ticks\": {";
    bool first = true;
    for (const auto &[round, tick] : roundCompletion) {
        if (!first)
            output << ",";
        output << "\n    \"" << round << "\": " << tick;
        first = false;
    }
    if (!roundCompletion.empty())
        output << "\n  ";
    output << "}\n}\n";
    output.close();
    exitSimLoop("Sumcheck causal workload complete");
}

void
SumcheckWorkload::updateDigest(uint64_t &digest, const std::string &text)
{
    for (unsigned char byte : text) {
        digest ^= byte;
        digest *= 1099511628211ULL;
    }
    digest ^= '\n';
    digest *= 1099511628211ULL;
}

} // namespace garnet
} // namespace ruby
} // namespace gem5
