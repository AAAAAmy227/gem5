// This file is generated from configs/topologies/SumcheckConfig.py.
// Run tests/pyunit/pyunit_sumcheck_topology.py to verify it is current.

#ifndef __MEM_RUBY_NETWORK_GARNET_SUMCHECK_CONFIG_HH__
#define __MEM_RUBY_NETWORK_GARNET_SUMCHECK_CONFIG_HH__

#include <array>
#include <cassert>
#include <limits>

namespace gem5
{
namespace ruby
{
namespace garnet
{
namespace sumcheck
{

inline constexpr int NumClusters = 4;
inline constexpr int ClusterRows = 4;
inline constexpr int ClusterCols = 4;
inline constexpr int WorkersPerCluster = 16;
inline constexpr int NumWorkers = 64;
inline constexpr int GatewayBaseId = 64;
inline constexpr int RootId = 68;
inline constexpr int NumRouters = 69;

struct Coord
{
    int row;
    int col;
};

enum class VcClass
{
    Up,
    Down,
    Any,
};

struct AdaptiveEntryChoice
{
    int index;
    unsigned next_tie_pointer;
    bool tied;
};

inline constexpr std::array<Coord, 4> EntriesP1 = {{Coord{1, 1}, Coord{0, 0}, Coord{0, 0}, Coord{0, 0}}};
inline constexpr std::array<Coord, 4> EntriesP2 = {{Coord{0, 1}, Coord{3, 2}, Coord{0, 0}, Coord{0, 0}}};
inline constexpr std::array<Coord, 4> EntriesP4 = {{Coord{0, 1}, Coord{1, 3}, Coord{2, 0}, Coord{3, 2}}};
inline constexpr std::array<Coord, 4> EntriesP4Corners = {{Coord{0, 0}, Coord{0, 3}, Coord{3, 0}, Coord{3, 3}}};

constexpr bool isWorker(int router_id)
{
    return router_id >= 0 && router_id < NumWorkers;
}

constexpr bool isGateway(int router_id)
{
    return router_id >= GatewayBaseId && router_id < RootId;
}

constexpr bool isRoot(int router_id)
{
    return router_id == RootId;
}

constexpr bool isRouter(int router_id)
{
    return router_id >= 0 && router_id < NumRouters;
}

constexpr int workerCluster(int router_id)
{
    return router_id / WorkersPerCluster;
}

constexpr Coord workerCoord(int router_id)
{
    const int local = router_id % WorkersPerCluster;
    return Coord{local / ClusterCols, local % ClusterCols};
}

constexpr int workerId(int cluster, Coord coord)
{
    return cluster * WorkersPerCluster + coord.row * ClusterCols + coord.col;
}

constexpr int gatewayId(int cluster)
{
    return GatewayBaseId + cluster;
}

constexpr int gatewayCluster(int router_id)
{
    return router_id - GatewayBaseId;
}

constexpr bool validEntryConfiguration(unsigned count, bool corners)
{
    return (count == 1 && !corners) || (count == 2 && !corners) ||
           count == 4;
}

inline const std::array<Coord, 4>&
entryTable(unsigned count, bool corners)
{
    assert(validEntryConfiguration(count, corners));
    if (count == 1)
        return EntriesP1;
    if (count == 2)
        return EntriesP2;
    return corners ? EntriesP4Corners : EntriesP4;
}

constexpr int absDistance(int value)
{
    return value < 0 ? -value : value;
}

inline int
nearestEntryIndex(int worker_id, unsigned count, bool corners)
{
    assert(isWorker(worker_id));
    const Coord destination = workerCoord(worker_id);
    const auto &entries = entryTable(count, corners);
    int best_index = 0;
    int best_distance = ClusterRows + ClusterCols;
    for (unsigned index = 0; index < count; ++index) {
        const int distance = absDistance(entries[index].row - destination.row) +
                             absDistance(entries[index].col - destination.col);
        if (distance < best_distance) {
            best_distance = distance;
            best_index = index;
        }
    }
    return best_index;
}

inline AdaptiveEntryChoice
chooseAdaptiveEntry(int worker_id, unsigned count, bool corners,
                    const std::array<int, 4> &free_credits,
                    const std::array<int, 4> &capacities,
                    double congestion_weight, unsigned tie_pointer)
{
    assert(isWorker(worker_id));
    assert(validEntryConfiguration(count, corners));
    assert(congestion_weight >= 0.0);
    assert(tie_pointer < count);
    const Coord destination = workerCoord(worker_id);
    const auto &entries = entryTable(count, corners);
    std::array<double, 4> scores{};
    double best_score = std::numeric_limits<double>::infinity();
    for (unsigned entry = 0; entry < count; ++entry) {
        assert(capacities[entry] > 0);
        assert(free_credits[entry] >= 0 &&
               free_credits[entry] <= capacities[entry]);
        const int distance =
            absDistance(entries[entry].row - destination.row) +
            absDistance(entries[entry].col - destination.col);
        scores[entry] = distance + congestion_weight *
            (1.0 - static_cast<double>(free_credits[entry]) /
                   capacities[entry]);
        if (scores[entry] < best_score)
            best_score = scores[entry];
    }

    std::array<bool, 4> minimum{};
    int tie_count = 0;
    for (unsigned entry = 0; entry < count; ++entry) {
        double difference = scores[entry] - best_score;
        if (difference < 0.0)
            difference = -difference;
        if (difference <= 1e-12) {
            minimum[entry] = true;
            ++tie_count;
        }
    }

    if (tie_count == 1) {
        for (unsigned entry = 0; entry < count; ++entry) {
            if (minimum[entry])
                return AdaptiveEntryChoice{
                    static_cast<int>(entry), tie_pointer, false};
        }
    }

    for (unsigned step = 0; step < count; ++step) {
        const unsigned entry = (tie_pointer + step) % count;
        if (minimum[entry])
            return AdaptiveEntryChoice{
                static_cast<int>(entry), (entry + 1) % count, true};
    }
    assert(false);
    return AdaptiveEntryChoice{0, tie_pointer, false};
}

constexpr int
vcOffsetBegin(VcClass vc_class)
{
    return vc_class == VcClass::Down ? 2 : 0;
}

constexpr int
vcOffsetEnd(VcClass vc_class, int vcs_per_vnet)
{
    return vc_class == VcClass::Up ? 2 :
           vc_class == VcClass::Down ? 4 : vcs_per_vnet;
}

inline VcClass
routeVcClass(int current, int source, int destination)
{
    assert(isRouter(current) && isRouter(source) && isRouter(destination));
    if (source == destination)
        return VcClass::Up;

    if (isRoot(current))
        return current == destination ? VcClass::Up : VcClass::Down;

    if (isGateway(current)) {
        const int cluster = gatewayCluster(current);
        if (isWorker(destination) && workerCluster(destination) == cluster)
            return VcClass::Down;
        if (current == destination) {
            if (isWorker(source) && workerCluster(source) == cluster)
                return VcClass::Up;
            return VcClass::Down;
        }
        return VcClass::Up;
    }

    if (isWorker(current)) {
        const int cluster = workerCluster(current);
        if (isWorker(destination) && workerCluster(destination) == cluster) {
            if (isWorker(source) && workerCluster(source) == cluster)
                return VcClass::Up;
            return VcClass::Down;
        }
        return VcClass::Up;
    }

    assert(false);
    return VcClass::Any;
}

} // namespace sumcheck
} // namespace garnet
} // namespace ruby
} // namespace gem5

#endif // __MEM_RUBY_NETWORK_GARNET_SUMCHECK_CONFIG_HH__
