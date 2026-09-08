from m5.objects import *
from m5.util import fatal

from topologies.BaseTopology import SimpleTopology
from topologies.SumcheckModel import HierarchyModel, check_p


class SumcheckHierarchy(SimpleTopology):
    description = "SumcheckHierarchy"

    def __init__(self, controllers):
        self.nodes = controllers

    def makeTopology(self, options, network, IntLink, ExtLink, Router):
        p = options.entries_per_cluster
        try:
            check_p(p)
            model = HierarchyModel(
                num_clusters=options.num_clusters,
                rows=options.mesh_rows,
                cols=options.mesh_rows,
            )
            model.entry_coordinates(p)
        except ValueError as error:
            fatal(str(error))
        if options.routing_algorithm != 3:
            fatal("SumcheckHierarchy requires --routing-algorithm=3")
        if getattr(options, "entry_placement", "staggered") != "staggered":
            fatal("SumcheckHierarchy only supports staggered entry placement")

        routers = [
            Router(router_id=i, latency=options.router_latency)
            for i in range(model.num_routers)
        ]
        network.routers = routers
        root_ni_lanes = options.root_ni_lanes
        root_dir_lanes = getattr(options, 'root_dir_lanes', root_ni_lanes)
        root_ejection_directory_ids = set(
            model.root_ejection_directory_ids(root_dir_lanes)
        )
        expected_l1_controllers = model.num_workers + root_ni_lanes
        if options.num_cpus != expected_l1_controllers:
            fatal(
                "SumcheckHierarchy expected "
                f"{expected_l1_controllers} L1 controllers; "
                f"got {options.num_cpus}"
            )

        ext_links = []
        for index, node in enumerate(self.nodes):
            if index < options.num_cpus:
                # One L1/NI per worker, followed by all root injection
                # lanes. Every root lane enters the root router.
                router_id = (
                    index if index < model.num_workers else model.root
                )
            else:
                directory_id = index - options.num_cpus
                if directory_id < model.root:
                    router_id = directory_id
                elif directory_id in root_ejection_directory_ids:
                    # These are response/ejection endpoints, one per root NI
                    # lane. They do not represent replicated logical storage.
                    router_id = model.root
                else:
                    # Padding directories required by power-of-two address
                    # interleaving are unused by the Sumcheck workload.
                    router_id = model.root
            ext_links.append(ExtLink(
                link_id=index, ext_node=node, int_node=routers[router_id],
                latency=options.link_latency))
        network.ext_links = ext_links

        link_id = len(network.ext_links)
        int_links = []
        for link in model.physical_links(p):
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
