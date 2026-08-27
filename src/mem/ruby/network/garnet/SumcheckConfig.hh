// This file is generated from configs/topologies/SumcheckConfig.py.
// Run tests/pyunit/pyunit_sumcheck_topology.py to verify it is current.

#ifndef __MEM_RUBY_NETWORK_GARNET_SUMCHECK_CONFIG_HH__
#define __MEM_RUBY_NETWORK_GARNET_SUMCHECK_CONFIG_HH__

#include <array>
#include <cassert>

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

} // namespace sumcheck
} // namespace garnet
} // namespace ruby
} // namespace gem5

#endif // __MEM_RUBY_NETWORK_GARNET_SUMCHECK_CONFIG_HH__
