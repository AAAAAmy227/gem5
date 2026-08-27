"""8x8 XY baseline with the 69 Sumcheck roles as real endpoints."""

from m5.objects import *
from m5.util import fatal

from topologies.BaseTopology import SimpleTopology
from topologies.SumcheckConfig import MESH_CONTROLLER_TO_ROUTER


class SumcheckMesh(SimpleTopology):
    description = "SumcheckMesh"

    controller_to_router = MESH_CONTROLLER_TO_ROUTER

    def __init__(self, controllers):
        self.nodes = controllers

    def makeTopology(self, options, network, IntLink, ExtLink, Router):
        if len(self.nodes) != 69:
            fatal(f"SumcheckMesh requires 69 endpoints; got {len(self.nodes)}")
        if options.mesh_rows != 8 or options.routing_algorithm != 1:
            fatal("SumcheckMesh requires --mesh-rows=8 --routing-algorithm=1")

        routers = [
            Router(router_id=index, latency=options.router_latency)
            for index in range(64)
        ]
        network.routers = routers
        link_id = 0
        network.ext_links = []
        for controller, router_id in zip(
            self.nodes, self.controller_to_router
        ):
            network.ext_links.append(
                ExtLink(
                    link_id=link_id,
                    ext_node=controller,
                    int_node=routers[router_id],
                    latency=options.link_latency,
                )
            )
            link_id += 1

        network.int_links = []
        for row in range(8):
            for col in range(8):
                current = row * 8 + col
                if col + 1 < 8:
                    east = current + 1
                    network.int_links.extend((
                        IntLink(link_id=link_id, src_node=routers[current],
                            dst_node=routers[east], src_outport="East",
                            dst_inport="West", latency=options.link_latency,
                            weight=1),
                        IntLink(link_id=link_id + 1, src_node=routers[east],
                            dst_node=routers[current], src_outport="West",
                            dst_inport="East", latency=options.link_latency,
                            weight=1),
                    ))
                    link_id += 2
                if row + 1 < 8:
                    south = current + 8
                    network.int_links.extend((
                        IntLink(link_id=link_id, src_node=routers[current],
                            dst_node=routers[south], src_outport="North",
                            dst_inport="South", latency=options.link_latency,
                            weight=2),
                        IntLink(link_id=link_id + 1, src_node=routers[south],
                            dst_node=routers[current], src_outport="South",
                            dst_inport="North", latency=options.link_latency,
                            weight=2),
                    ))
                    link_id += 2
