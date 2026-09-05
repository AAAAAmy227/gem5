#ifndef __MEM_RUBY_NETWORK_GARNET_SUMCHECK_ADAPTIVE_HH__
#define __MEM_RUBY_NETWORK_GARNET_SUMCHECK_ADAPTIVE_HH__

#include <vector>

#include "base/random.hh"
#include "mem/ruby/network/garnet/CommonTypes.hh"

namespace gem5
{

namespace ruby
{

namespace garnet
{

class Router;
class RoutingUnit;

struct AdaptiveEntryDecision
{
    int selected;
    int fixed;
    bool tied;
};

class SumcheckAdaptive
{
  public:
    SumcheckAdaptive(Router *router,
                     RoutingUnit *routingUnit,
                     int entriesPerCluster,
                     int meshRows,
                     double congestionWeight,
                     SumcheckRoutingMode mode,
                     uint32_t seed);
    AdaptiveEntryDecision chooseEntry(
        int vnet, int destinationWorker,
        const std::vector<int> &candidateOutports);
    
    void resetStats();
    int getEntryChoiceCount(int entryIdx);
    int getRerouteCount();
  
  private:
    double computeScore(int entryRouterId, int destWorker,
                        int vnet, int candidateOutport);
    int manhattanDist(int srcRouterId, int destRouterId);

    Router *m_router;
    RoutingUnit *m_routingUnit;
    int m_entriesPerCluster;
    int m_meshRows;
    double m_congestionWeight;
    SumcheckRoutingMode m_mode;

    unsigned m_tiePointer;
    std::vector<int> m_entryChoiceCounts;
    int m_rerouteCount;

    Random m_rng;
};

}
}
}

#endif