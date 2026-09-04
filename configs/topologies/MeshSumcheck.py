from m5.params import *
from m5.objects import *

from common import FileSystemConfig

from topologies.BaseTopology import SimpleTopology

# Mesh topology for Sumcheck Causal Traffic.
# Supports placing SOURCE and one WORKER on the same router
# (specified by options.src_router_id), while all other
# WORKERs occupy one router each. XY routing is enforced
# (using link weights) to guarantee deadlock freedom.


class MeshSumcheck(SimpleTopology):
    description = "MeshSumcheck"

    def __init__(self, controllers):
        self.nodes = controllers

    def makeTopology(self, options, network, IntLink, ExtLink, Router):
        nodes = self.nodes

        num_cpus = options.num_cpus
        num_rows = options.mesh_rows
        num_routers = num_rows * num_rows
        src_router_id = options.src_router_id

        link_latency = options.link_latency  # used by simple and garnet
        router_latency = options.router_latency  # only used by garnet

        assert num_rows > 0 and num_rows <= num_routers
        num_columns = int(num_routers / num_rows)
        assert num_columns * num_rows == num_routers

        # There is one router with two CPUs (src/worker)
        assert (
            num_cpus == num_routers + 1
        ), f"""Expected num_cpus={num_routers+1}
            (1 src + {num_routers} workers), got {num_cpus}"""

        routers = [
            Router(router_id=i, latency=router_latency)
            for i in range(num_routers)
        ]
        network.routers = routers

        link_count = 0

        other_routers = [r for r in range(num_routers) if r != src_router_id]

        ext_links = []
        for i in range(num_cpus):
            if i == 0 or i == 1:
                router_id = src_router_id  # CPU0 & CPU1 on the same router
            else:
                router_id = other_routers[i - 2]

            ext_links.append(
                ExtLink(
                    link_id=link_count,
                    ext_node=nodes[i],
                    int_node=routers[router_id],
                    latency=link_latency,
                )
            )
            link_count += 1

        num_dir_nodes = len(nodes) - num_cpus
        for i in range(num_dir_nodes):
            router_id = i % num_routers
            ext_links.append(
                ExtLink(
                    link_id=link_count,
                    ext_node=nodes[num_cpus + i],
                    int_node=routers[router_id],
                    latency=link_latency,
                )
            )
            link_count += 1

        network.ext_links = ext_links
        # Create the mesh links.
        int_links = []

        # East output to West input links (weight = 1)
        for row in range(num_rows):
            for col in range(num_columns):
                if col + 1 < num_columns:
                    east_out = col + (row * num_columns)
                    west_in = (col + 1) + (row * num_columns)
                    int_links.append(
                        IntLink(
                            link_id=link_count,
                            src_node=routers[east_out],
                            dst_node=routers[west_in],
                            src_outport="East",
                            dst_inport="West",
                            latency=link_latency,
                            weight=1,
                        )
                    )
                    link_count += 1

        # West output to East input links (weight = 1)
        for row in range(num_rows):
            for col in range(num_columns):
                if col + 1 < num_columns:
                    east_in = col + (row * num_columns)
                    west_out = (col + 1) + (row * num_columns)
                    int_links.append(
                        IntLink(
                            link_id=link_count,
                            src_node=routers[west_out],
                            dst_node=routers[east_in],
                            src_outport="West",
                            dst_inport="East",
                            latency=link_latency,
                            weight=1,
                        )
                    )
                    link_count += 1

        # North output to South input links (weight = 2)
        for col in range(num_columns):
            for row in range(num_rows):
                if row + 1 < num_rows:
                    north_out = col + (row * num_columns)
                    south_in = col + ((row + 1) * num_columns)
                    int_links.append(
                        IntLink(
                            link_id=link_count,
                            src_node=routers[north_out],
                            dst_node=routers[south_in],
                            src_outport="North",
                            dst_inport="South",
                            latency=link_latency,
                            weight=2,
                        )
                    )
                    link_count += 1

        # South output to North input links (weight = 2)
        for col in range(num_columns):
            for row in range(num_rows):
                if row + 1 < num_rows:
                    north_in = col + (row * num_columns)
                    south_out = col + ((row + 1) * num_columns)
                    int_links.append(
                        IntLink(
                            link_id=link_count,
                            src_node=routers[south_out],
                            dst_node=routers[north_in],
                            src_outport="South",
                            dst_inport="North",
                            latency=link_latency,
                            weight=2,
                        )
                    )
                    link_count += 1

        network.int_links = int_links

    # Register nodes with filesystem
    def registerTopology(self, options):
        for i in range(options.num_cpus):
            FileSystemConfig.register_node(
                [i], MemorySize(options.mem_size) // options.num_cpus, i
            )
