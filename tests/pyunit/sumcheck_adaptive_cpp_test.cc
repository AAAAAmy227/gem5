#include <array>
#include <cassert>

#include "mem/ruby/network/garnet/SumcheckConfig.hh"

int
main()
{
    using namespace gem5::ruby::garnet::sumcheck;

    const std::array<int, 4> capacities{{8, 8, 0, 0}};
    const std::array<int, 4> congested{{0, 8, 0, 0}};
    const int non_nearest_destination = workerId(0, Coord{1, 1});
    const auto non_nearest = chooseAdaptiveEntry(
        non_nearest_destination, 2, false,
        congested, capacities, 4.0, 0);
    assert(nearestEntryIndex(non_nearest_destination, 2, false) == 0);
    assert(non_nearest.index == 1);
    assert(!non_nearest.tied);

    const std::array<int, 4> equal_credits{{8, 8, 0, 0}};
    const int tied_destination = workerId(0, Coord{1, 2});
    const auto first = chooseAdaptiveEntry(
        tied_destination, 2, false,
        equal_credits, capacities, 4.0, 0);
    const auto second = chooseAdaptiveEntry(
        tied_destination, 2, false,
        equal_credits, capacities, 4.0, first.next_tie_pointer);
    assert(first.tied && second.tied);
    assert(first.index == 0 && second.index == 1);

    assert(vcOffsetBegin(VcClass::Up) == 0);
    assert(vcOffsetEnd(VcClass::Up, 4) == 2);
    assert(vcOffsetBegin(VcClass::Down) == 2);
    assert(vcOffsetEnd(VcClass::Down, 4) == 4);
    assert(routeVcClass(RootId, 0, 32) == VcClass::Down);
    assert(routeVcClass(RootId, 0, RootId) == VcClass::Up);
    return 0;
}
