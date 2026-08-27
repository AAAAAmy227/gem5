#ifndef __MEM_RUBY_NETWORK_GARNET_SUMCHECK_WORKLOAD_HH__
#define __MEM_RUBY_NETWORK_GARNET_SUMCHECK_WORKLOAD_HH__

#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>

#include "mem/ruby/network/MessageBuffer.hh"
#include "params/SumcheckWorkload.hh"
#include "sim/clocked_object.hh"
#include "sim/eventq.hh"

namespace gem5
{
namespace ruby
{
namespace garnet
{

class SumcheckWorkload : public ClockedObject
{
  public:
    PARAMS(SumcheckWorkload);
    explicit SumcheckWorkload(const Params &p);

    void startup() override;
    void notifyArrival(uint64_t event_id, int destination_ni);

  private:
    struct Event
    {
        std::string id;
        int source = -1;
        int destination = -1;
        uint32_t bytes = 0;
        std::string phase;
        int round = -1;
        std::string kind;
        std::vector<std::string> dependencyIds;
        std::vector<size_t> dependencies;
        std::vector<size_t> dependents;
        size_t remaining = 0;
        bool injected = false;
        bool arrived = false;
        Tick injectedAt = 0;
        Tick arrivedAt = 0;
        Cycles releaseCycle = Cycles(0);
    };

    void parseAndValidate(const std::vector<std::string> &records);
    void injectReady();
    void inject(size_t index);
    void watchdog();
    void runLocalPhase();
    void finish();
    void updateDigest(uint64_t &digest, const std::string &text);
    std::string stuckState() const;

    std::vector<Event> events;
    std::unordered_map<std::string, size_t> eventIndex;
    std::vector<MessageBuffer *> injectionBuffers;
    std::set<size_t> pendingReady;
    std::map<std::string, Tick> roundCompletion;
    EventFunctionWrapper injectionEvent;
    EventFunctionWrapper watchdogEvent;
    EventFunctionWrapper localPhaseEvent;
    const std::string mode;
    const std::string reportFile;
    const uint64_t seed;
    const uint32_t flitBytes;
    const Cycles watchdogCycles;
    Tick lastProgress;
    uint64_t packetsInjected;
    uint64_t packetsReceived;
    uint64_t flitsInjected;
    uint64_t flitsReceived;
    uint64_t initialInjections;
    uint64_t arrivalTriggeredInjections;
    uint64_t traceDigest;
    uint64_t injectionDigest;
    std::vector<uint64_t> packetLatencyCycles;
    int phaseCLocalRound;
};

} // namespace garnet
} // namespace ruby
} // namespace gem5

#endif
