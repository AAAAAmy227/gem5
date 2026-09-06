/*
 * Copyright (c) 2008 Princeton University
 * Copyright (c) 2016 Georgia Institute of Technology
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met: redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer;
 * redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution;
 * neither the name of the copyright holders nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */


#include "mem/ruby/network/garnet/RoutingUnit.hh"

#if __has_include("mem/ruby/network/garnet/SumcheckAdaptive.hh")
#include "mem/ruby/network/garnet/SumcheckAdaptive.hh"
#define GEM5_HAS_SUMCHECK_ADAPTIVE 1
#endif

#include <string>
#include <vector>

#include "base/logging.hh"

#include "base/cast.hh"
#include "base/compiler.hh"
#include "debug/RubyNetwork.hh"
#include "mem/ruby/network/garnet/InputUnit.hh"
#include "mem/ruby/network/garnet/Router.hh"
#include "mem/ruby/slicc_interface/Message.hh"

namespace gem5
{

namespace ruby
{

namespace garnet
{

RoutingUnit::RoutingUnit(Router *router)
{
    m_router = router;
    m_sumcheck_adaptive = nullptr;
    m_sumcheck_num_clusters = 0;
    m_sumcheck_mesh_rows = 0;
    m_sumcheck_entries_per_cluster = 0;
    m_routing_table.clear();
    m_weight_table.clear();
}

RoutingUnit::RoutingUnit(Router *router, const GarnetRouterParams &p)
{
    m_router = router;
    m_sumcheck_num_clusters = p.num_clusters;
    m_sumcheck_mesh_rows = p.mesh_rows;
    m_sumcheck_entries_per_cluster = p.entries_per_cluster;
    if (p.topology == "SumcheckHierarchy") {
        m_sumcheck_adaptive = new SumcheckAdaptive(
            router, this, p.entries_per_cluster, p.mesh_rows,
            p.entry_congestion_weight,
            p.sumcheck_routing == "fixed" ? MIN_SCORE_ : RANDOM_SCORE_,
            p.sumcheck_seed);
    } else {
        m_sumcheck_adaptive = nullptr;
    }
    m_routing_table.clear();
    m_weight_table.clear();
}

void
RoutingUnit::addRoute(std::vector<NetDest>& routing_table_entry)
{
    if (routing_table_entry.size() > m_routing_table.size()) {
        m_routing_table.resize(routing_table_entry.size());
    }
    for (int v = 0; v < routing_table_entry.size(); v++) {
        m_routing_table[v].push_back(routing_table_entry[v]);
    }
}

void
RoutingUnit::addWeight(int link_weight)
{
    m_weight_table.push_back(link_weight);
}

bool
RoutingUnit::supportsVnet(int vnet, std::vector<int> sVnets)
{
    // If all vnets are supported, return true
    if (sVnets.size() == 0) {
        return true;
    }

    // Find the vnet in the vector, return true
    if (std::find(sVnets.begin(), sVnets.end(), vnet) != sVnets.end()) {
        return true;
    }

    // Not supported vnet
    return false;
}

/*
 * This is the default routing algorithm in garnet.
 * The routing table is populated during topology creation.
 * Routes can be biased via weight assignments in the topology file.
 * Correct weight assignments are critical to provide deadlock avoidance.
 */
int
RoutingUnit::lookupRoutingTable(int vnet, NetDest msg_destination)
{
    // First find all possible output link candidates
    // For ordered vnet, just choose the first
    // (to make sure different packets don't choose different routes)
    // For unordered vnet, randomly choose any of the links
    // To have a strict ordering between links, they should be given
    // different weights in the topology file

    int output_link = -1;
    int min_weight = INFINITE_;
    std::vector<int> output_link_candidates;
    int num_candidates = 0;

    // Identify the minimum weight among the candidate output links
    for (int link = 0; link < m_routing_table[vnet].size(); link++) {
        if (msg_destination.intersectionIsNotEmpty(
            m_routing_table[vnet][link])) {

        if (m_weight_table[link] <= min_weight)
            min_weight = m_weight_table[link];
        }
    }

    // Collect all candidate output links with this minimum weight
    for (int link = 0; link < m_routing_table[vnet].size(); link++) {
        if (msg_destination.intersectionIsNotEmpty(
            m_routing_table[vnet][link])) {

            if (m_weight_table[link] == min_weight) {
                num_candidates++;
                output_link_candidates.push_back(link);
            }
        }
    }

    if (output_link_candidates.size() == 0) {
        fatal("Fatal Error:: No Route exists from this Router.");
        exit(0);
    }

    // Randomly select any candidate output link
    int candidate = 0;
    if (!(m_router->get_net_ptr())->isVNetOrdered(vnet))
        candidate = rand() % num_candidates;

    output_link = output_link_candidates.at(candidate);
    return output_link;
}


void
RoutingUnit::addInDirection(PortDirection inport_dirn, int inport_idx)
{
    m_inports_dirn2idx[inport_dirn] = inport_idx;
    m_inports_idx2dirn[inport_idx]  = inport_dirn;
}

void
RoutingUnit::addOutDirection(PortDirection outport_dirn, int outport_idx)
{
    m_outports_dirn2idx[outport_dirn] = outport_idx;
    m_outports_idx2dirn[outport_idx]  = outport_dirn;
}

// outportCompute() is called by the InputUnit
// It calls the routing table by default.
// A template for adaptive topology-specific routing algorithm
// implementations using port directions rather than a static routing
// table is provided here.

int
RoutingUnit::outportCompute(RouteInfo route, int inport,
                            PortDirection inport_dirn)
{
    int outport = -1;

    RoutingAlgorithm routing_algorithm =
        (RoutingAlgorithm) m_router->get_net_ptr()->getRoutingAlgorithm();
    if (routing_algorithm == SUMCHECK_) {
        fatal_if(route.vnet != 0, "Sumcheck only supports vnet 0");
        return route.dest_router == m_router->get_id() ?
            lookupRoutingTable(route.vnet, route.net_dest) :
            outportComputeSumcheck(route);
    }

    if (route.dest_router == m_router->get_id()) {

        // Multiple NIs may be connected to this router,
        // all with output port direction = "Local"
        // Get exact outport id from table
        outport = lookupRoutingTable(route.vnet, route.net_dest);
        return outport;
    }
    // Routing Algorithm set in GarnetNetwork.py
    // Can be over-ridden from command line using --routing-algorithm = 1
    switch (routing_algorithm) {
        case TABLE_:  outport =
            lookupRoutingTable(route.vnet, route.net_dest); break;
        case XY_:     outport =
            outportComputeXY(route, inport, inport_dirn); break;
        // any custom algorithm
        case CUSTOM_: outport =
            outportComputeCustom(route, inport, inport_dirn); break;
        case SUMCHECK_: break; // handled above
        default: outport =
            lookupRoutingTable(route.vnet, route.net_dest); break;
    }

    assert(outport != -1);
    return outport;
}

// XY routing implemented using port directions
// Only for reference purpose in a Mesh
// By default Garnet uses the routing table
int
RoutingUnit::outportComputeXY(RouteInfo route,
                              int inport,
                              PortDirection inport_dirn)
{
    PortDirection outport_dirn = "Unknown";

    [[maybe_unused]] int num_rows = m_router->get_net_ptr()->getNumRows();
    int num_cols = m_router->get_net_ptr()->getNumCols();
    assert(num_rows > 0 && num_cols > 0);

    int my_id = m_router->get_id();
    int my_x = my_id % num_cols;
    int my_y = my_id / num_cols;

    int dest_id = route.dest_router;
    int dest_x = dest_id % num_cols;
    int dest_y = dest_id / num_cols;

    int x_hops = abs(dest_x - my_x);
    int y_hops = abs(dest_y - my_y);

    bool x_dirn = (dest_x >= my_x);
    bool y_dirn = (dest_y >= my_y);

    // already checked that in outportCompute() function
    assert(!(x_hops == 0 && y_hops == 0));

    if (x_hops > 0) {
        if (x_dirn) {
            assert(inport_dirn == "Local" || inport_dirn == "West");
            outport_dirn = "East";
        } else {
            assert(inport_dirn == "Local" || inport_dirn == "East");
            outport_dirn = "West";
        }
    } else if (y_hops > 0) {
        if (y_dirn) {
            // "Local" or "South" or "West" or "East"
            assert(inport_dirn != "North");
            outport_dirn = "North";
        } else {
            // "Local" or "North" or "West" or "East"
            assert(inport_dirn != "South");
            outport_dirn = "South";
        }
    } else {
        // x_hops == 0 and y_hops == 0
        // this is not possible
        // already checked that in outportCompute() function
        panic("x_hops == y_hops == 0");
    }

    return m_outports_dirn2idx[outport_dirn];
}

// Template for implementing custom routing algorithm
// using port directions. (Example adaptive)
int
RoutingUnit::outportComputeCustom(RouteInfo route,
                                 int inport,
                                 PortDirection inport_dirn)
{
    PortDirection outport_dirn = "Unknown";
    int my_id = m_router->get_id();
    int dest_id = route.dest_router;
    int num_routers = m_router->get_net_ptr()->getNumCols();
    int cw_dist = (dest_id - my_id + num_routers)%num_routers; //clockwise
    int ccw_dist = (my_id - dest_id + num_routers)%num_routers; //counterclockwise
    assert(!(cw_dist == 0 && ccw_dist == 0));
    assert(cw_dist+ccw_dist == num_routers);
    if (cw_dist <= ccw_dist) 
    {
        assert(inport_dirn == "Local" || inport_dirn == "Up");
        outport_dirn = "Down";
    }
    else
    {
        assert(inport_dirn == "Local" || inport_dirn == "Down");
        outport_dirn = "Up";
    }

    return m_outports_dirn2idx[outport_dirn];
    
    panic("%s placeholder executed", __FUNCTION__);
}

namespace
{
constexpr unsigned MaxEntriesPerCluster = 4;

std::pair<int, int>
entryCoord(unsigned width, unsigned entries, unsigned index)
{
    if (entries == 1)
        return {(width - 1) / 2, (width - 1) / 2};

    const std::pair<int, int> coordinates[MaxEntriesPerCluster] = {
        {0, (width - 1) / 2},
        {(width - 1) / 2, width - 1},
        {width / 2, 0},
        {width - 1, width / 2},
    };
    if (entries == 2)
        return index == 0 ? coordinates[0] : coordinates[3];
    return coordinates[index];
}

int
entryRouter(int cluster, unsigned width, unsigned entries, unsigned index)
{
    auto [row, col] = entryCoord(width, entries, index);
    return cluster * width * width + row * width + col;
}

unsigned
nearestEntry(int worker, unsigned width, unsigned entries)
{
    const int workersPerCluster = width * width;
    const int local = worker % workersPerCluster;
    const int row = local / width;
    const int col = local % width;
    unsigned best = 0;
    int best_distance = 2 * width;
    for (unsigned index = 0; index < entries; ++index) {
        auto [entry_row, entry_col] = entryCoord(width, entries, index);
        int distance = std::abs(row - entry_row) + std::abs(col - entry_col);
        if (distance < best_distance) {
            best = index;
            best_distance = distance;
        }
    }
    return best;
}
} // anonymous namespace

int
RoutingUnit::outportForDirection(const PortDirection &direction) const
{
    auto found = m_outports_dirn2idx.find(direction);
    fatal_if(found == m_outports_dirn2idx.end(),
             "Router %d lacks Sumcheck outport %s",
             m_router->get_id(), direction.c_str());
    return found->second;
}

int
RoutingUnit::outportComputeSumcheck(RouteInfo route)
{
#ifndef GEM5_HAS_SUMCHECK_ADAPTIVE
    fatal("SumcheckAdaptive.hh is required for Sumcheck routing");
#else
    const int current = m_router->get_id();
    const int source = route.src_router;
    const int destination = route.dest_router;
    const unsigned clusters = m_sumcheck_num_clusters;
    const unsigned width = m_sumcheck_mesh_rows;
    const unsigned entries = m_sumcheck_entries_per_cluster;
    fatal_if(clusters == 0, "Sumcheck requires at least one cluster");
    fatal_if(width == 0, "Sumcheck cluster width must be positive");
    fatal_if(entries == 0 || entries > MaxEntriesPerCluster ||
             (entries & (entries - 1)) != 0,
             "Invalid Sumcheck entry count %u", entries);

    const int workersPerCluster = width * width;
    const int numWorkers = clusters * workersPerCluster;
    const int gatewayBase = numWorkers;
    const int root = gatewayBase + clusters;
    auto isWorker = [numWorkers](int id) {
        return id >= 0 && id < numWorkers;
    };
    auto isGateway = [gatewayBase, root](int id) {
        return id >= gatewayBase && id < root;
    };
    auto clusterOfWorker = [workersPerCluster](int id) {
        return id / workersPerCluster;
    };
    auto clusterOfGateway = [gatewayBase](int id) {
        return id - gatewayBase;
    };

    // Only classify a packet when it is injected. At later hops, routing is
    // determined by the current router's role in the hierarchy.
    if (source == current) {
        const bool rootToWorker =
            source == root && isWorker(destination);
        const bool workerToRoot =
            isWorker(source) && destination == root;
        fatal_if(!rootToWorker && !workerToRoot,
                 "Unsupported Sumcheck flow %d->%d", source, destination);
    }

    auto meshOutport = [&](int target) {
        fatal_if(!isWorker(current) || !isWorker(target) ||
                 clusterOfWorker(current) != clusterOfWorker(target),
                 "Illegal Sumcheck mesh step %d->%d", current, target);
        const int here = current % workersPerCluster;
        const int there = target % workersPerCluster;
        if (here / width < there / width)
            return outportForDirection("Dim0Pos");
        if (here / width > there / width)
            return outportForDirection("Dim0Neg");
        if (here % width < there % width)
            return outportForDirection("Dim1Pos");
        if (here % width > there % width)
            return outportForDirection("Dim1Neg");
        fatal("Mesh step requested at destination router %d", current);
    };

    if (isWorker(current)) {
        if (destination != root)
            return meshOutport(destination);

        const int target = entryRouter(clusterOfWorker(source), width, entries,
            nearestEntry(source, width, entries));
        return current == target ? outportForDirection("Gateway") :
                                   meshOutport(target);
    }

    if (current == root)
        return outportForDirection(
            "RootToG" + std::to_string(clusterOfWorker(destination)));

    if (isGateway(current)) {
        if (destination == root)
            return outportForDirection("RootUp");

        fatal_if(!isWorker(destination) ||
                 clusterOfWorker(destination) != clusterOfGateway(current),
                 "Illegal Sumcheck gateway step %d->%d", current,
                 destination);
        std::vector<int> candidateOutports;
        candidateOutports.reserve(entries);
        for (unsigned index = 0; index < entries; ++index) {
            int outport = outportForDirection("Entry" + std::to_string(index));
            fatal_if(m_router->getOutportRouterId(outport) !=
                     entryRouter(clusterOfGateway(current), width, entries,
                                 index),
                     "Gateway %d Entry%u is wired to the wrong router",
                     current, index);
            candidateOutports.push_back(outport);
        }
        fatal_if(!m_sumcheck_adaptive,
                 "Gateway %d has no SumcheckAdaptive selector", current);
        AdaptiveEntryDecision decision = m_sumcheck_adaptive->chooseEntry(
            route.vnet, route.dest_router, candidateOutports);
        return candidateOutports[decision.selected];
    }

    fatal("Illegal Sumcheck current router %d", current);
#endif
}

} // namespace garnet
} // namespace ruby
} // namespace gem5
