#include "mem/ruby/network/garnet/SumcheckAdaptive.hh"

#include <cassert>
#include <cmath>
#include <random>

#include "base/logging.hh"
#include "mem/ruby/network/garnet/Router.hh"

namespace gem5
{

namespace ruby
{

namespace garnet
{

SumcheckAdaptive::SumcheckAdaptive(
    Router *router,
    RoutingUnit *routingUnit,
    int entriesPerCluster,
    int meshRows,
    double congestionWeight,
    SumcheckRoutingMode mode,
    uint32_t seed)
    : m_router(router),
      m_routingUnit(routingUnit),
      m_entriesPerCluster(entriesPerCluster),
      m_meshRows(meshRows),
      m_congestionWeight(congestionWeight),
      m_mode(mode),
      m_tiePointer(0),
      m_entryChoiceCounts(entriesPerCluster, 0),
      m_rerouteCount(0),
      m_rng(seed)
{}

AdaptiveEntryDecision
SumcheckAdaptive::chooseEntry(int vnet, int destinationWorker,
                              const std::vector<int> &candidateOutports)
{
    int p = m_entriesPerCluster;
    fatal_if(p != candidateOutports.size(),
        "The number of entries for gateway is not consistent");
    std::vector<double> scores(p);

    for (int i = 0; i < p; i++) {
        int entryRouterId = m_router->getOutportRouterId(
            candidateOutports[i]);
        scores[i] = computeScore(entryRouterId, destinationWorker,
                                 vnet, candidateOutports[i]);
    }

    int fixed = 0;
    int fixedDist = manhattanDist(
        m_router->getOutportRouterId(candidateOutports[0]),
        destinationWorker);
    for (int i = 1; i < p; i++) {
        int d = manhattanDist(
            m_router->getOutportRouterId(candidateOutports[i]),
            destinationWorker);
        if (d < fixedDist) {
            fixedDist = d;
            fixed = i;
        }
    }

    int selected = 0;
    bool tied = false;

    if (m_mode == MIN_SCORE_) {
        selected = m_tiePointer;
        double minScore = scores[m_tiePointer];
        for (int j = 1; j < p; j++) {
            int i = (m_tiePointer + j) % p;
            if (scores[i] < minScore - 1e-9) {
                minScore = scores[i];
                selected = i;
                tied = false;
            } else if (std::abs(scores[i] - minScore) <= 1e-9) {
                tied = true;
            }
        }
        if (tied) {
            m_tiePointer = selected + 1;
            if (m_tiePointer == p) {
                m_tiePointer = 0;
            }
        }
    } else {
        const double eps = 0.1;
        std::vector<double> probs(p);
        double sum = 0.0;
        for (int i = 0; i < p; i++) {
            probs[i] = 1.0 / (scores[i] + eps);
            sum += probs[i];
        }
        for (int i = 0; i < p; i++) {
            probs[i] /= sum;
        }
        std::uniform_real_distribution<double> dist(0.0, 1.0);
        double r = dist(m_rng.gen);
        double acc = 0.0;
        selected = p - 1;  // fallback
        for (int i = 0; i < p; i++) {
            acc += probs[i];
            if (r <= acc) {
                selected = i;
                break;
            }
        }
    }

    m_entryChoiceCounts[selected]++;
    if (selected != fixed) {
        m_rerouteCount++;
    }
    AdaptiveEntryDecision result;
    result.selected = selected;
    result.fixed = fixed;
    result.tied = tied;
    return result;
}

double
SumcheckAdaptive::computeScore(int entryRouterId, int destWorker,
                               int vnet, int candidateOutport)
{
    int dist = manhattanDist(entryRouterId, destWorker);
    int credits = m_router->getVnetCredits(candidateOutport, vnet);
    int maxCredits = m_router->getVnetMaxCredits(candidateOutport, vnet);

    double congestion = 1.0 - (double)credits / (double)maxCredits;
    return (double)dist + m_congestionWeight * congestion;
}

int
SumcheckAdaptive::manhattanDist(int srcRouterId, int destRouterId)
{
    int num_routers = m_meshRows * m_meshRows;
    int src = srcRouterId % num_routers;
    int dst = destRouterId % num_routers;
    int src_row = src / m_meshRows;
    int src_col = src % m_meshRows;
    int dst_row = dst / m_meshRows;
    int dst_col = dst % m_meshRows;
    return std::abs(dst_row - src_row) + std::abs(dst_col - src_col);
}

void
SumcheckAdaptive::resetStats()
{
    std::fill(m_entryChoiceCounts.begin(), m_entryChoiceCounts.end(), 0);
    m_rerouteCount = 0;
    m_tiePointer = 0;
}

int
SumcheckAdaptive::getEntryChoiceCount(int entryIdx)
{
    assert(entryIdx >= 0 && entryIdx < m_entriesPerCluster);
    return m_entryChoiceCounts[entryIdx];
}

int
SumcheckAdaptive::getRerouteCount()
{
    return m_rerouteCount;
}

}
}
}