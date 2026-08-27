from m5.objects import *
from m5.params import *
from m5.util import fatal

from topologies.BaseTopology import SimpleTopology
from topologies.SumcheckConfig import (
    CONTROLLER_TO_ROUTER,
    NUM_ROUTERS,
    build_undirected_links,
    validate_configuration,
)


class SumcheckHierarchy(SimpleTopology):
    """Four 4x4 worker meshes joined through gateways and a root."""

    description = "SumcheckHierarchy"

    def __init__(self, controllers):
        self.nodes = controllers

    def makeTopology(self, options, network, IntLink, ExtLink, Router):
        try:
            validate_configuration(
                options.entries_per_cluster, options.entry_placement
            )
        except ValueError as error:
            fatal(str(error))

        if options.mesh_rows != 0:
            fatal("SumcheckHierarchy requires --mesh-rows=0")
        if options.routing_algorithm != 3:
            fatal(
                "SumcheckHierarchy requires --routing-algorithm=3 "
                "(algorithm 2 remains reserved for Lab3 Ring)"
            )
        if len(self.nodes) == NUM_ROUTERS:
            # Phase-3 causal path: exact logical endpoint/NI/router identity.
            controller_to_router = tuple(range(NUM_ROUTERS))
        elif len(self.nodes) == len(CONTROLLER_TO_ROUTER):
            # Preserve the earlier asymmetric Garnet synthetic smoke harness.
            controller_to_router = CONTROLLER_TO_ROUTER
        else:
            fatal(
                "SumcheckHierarchy requires either the 69 exact causal "
                "endpoints or the 72-controller legacy smoke harness; "
                f"got {len(self.nodes)}"
            )

        routers = [
            Router(router_id=router_id, latency=options.router_latency)
            for router_id in range(NUM_ROUTERS)
        ]
        network.routers = routers

        link_id = 0
        ext_links = []
        for controller, router_id in zip(self.nodes, controller_to_router):
            ext_links.append(
                ExtLink(
                    link_id=link_id,
                    ext_node=controller,
                    int_node=routers[router_id],
                    latency=options.link_latency,
                )
            )
            link_id += 1
        network.ext_links = ext_links

        latency_by_class = {
            "mesh": options.link_latency,
            "gateway_entry": options.gateway_entry_link_latency,
            "root_gateway": options.root_gateway_link_latency,
        }
        int_links = []
        for link in build_undirected_links(
            options.entries_per_cluster, options.entry_placement
        ):
            latency = latency_by_class[link.latency_class]
            int_links.append(
                IntLink(
                    link_id=link_id,
                    src_node=routers[link.node_a],
                    dst_node=routers[link.node_b],
                    src_outport=link.port_a,
                    dst_inport=link.port_b,
                    latency=latency,
                    weight=1,
                )
            )
            link_id += 1
            int_links.append(
                IntLink(
                    link_id=link_id,
                    src_node=routers[link.node_b],
                    dst_node=routers[link.node_a],
                    src_outport=link.port_b,
                    dst_inport=link.port_a,
                    latency=latency,
                    weight=1,
                )
            )
            link_id += 1
        network.int_links = int_links
