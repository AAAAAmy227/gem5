from m5.objects import *
from m5.util import fatal

from topologies.BaseTopology import SimpleTopology
from topologies.SumcheckModel import NUM_ROUTERS, check_p, physical_links


class SumcheckHierarchy(SimpleTopology):
    description = "SumcheckHierarchy"

    def __init__(self, controllers):
        self.nodes = controllers

    def makeTopology(self, options, network, IntLink, ExtLink, Router):
        p = options.entries_per_cluster
        try:
            check_p(p)
        except ValueError as error:
            fatal(str(error))
        if len(self.nodes) != NUM_ROUTERS:
            fatal(f"SumcheckHierarchy requires {NUM_ROUTERS} controllers; got {len(self.nodes)}")
        if options.routing_algorithm != 3:
            fatal("SumcheckHierarchy requires --routing-algorithm=3")
        if getattr(options, "entry_placement", "staggered") != "staggered":
            fatal("SumcheckHierarchy only supports staggered entry placement")

        routers = [
            Router(router_id=i, latency=options.router_latency)
            for i in range(NUM_ROUTERS)
        ]
        network.routers = routers
        network.ext_links = [
            ExtLink(
                link_id=i, ext_node=node, int_node=routers[i],
                latency=options.link_latency)
            for i, node in enumerate(self.nodes)
        ]

        link_id = NUM_ROUTERS
        int_links = []
        for link in physical_links(p):
            latency = options.link_latency
            if link.kind == "gateway_entry":
                latency = getattr(options, "gateway_entry_link_latency", latency)
            elif link.kind == "root_gateway":
                latency = getattr(options, "root_gateway_link_latency", latency)
            for source, destination, outport, inport in (
                (link.a, link.b, link.a_port, link.b_port),
                (link.b, link.a, link.b_port, link.a_port),
            ):
                int_links.append(IntLink(
                    link_id=link_id,
                    src_node=routers[source], dst_node=routers[destination],
                    src_outport=outport, dst_inport=inport,
                    latency=latency, weight=1))
                link_id += 1
        network.int_links = int_links
