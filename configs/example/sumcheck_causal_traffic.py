import m5
from m5.objects import *
from m5.defines import buildEnv
from m5.util import addToPath
import os, argparse, sys

addToPath("../")

from common import Options
from ruby import Ruby
from topologies.SumcheckModel import (
    DEFAULT_CLUSTER_ROWS,
    DEFAULT_NUM_CLUSTERS,
    HierarchyModel,
    SUPPORTED_ENTRY_COUNTS,
)

# Get paths we might need.  It's expected this file is in m5/configs/example.
config_path = os.path.dirname(os.path.abspath(__file__))
config_root = os.path.dirname(config_path)
m5_root = os.path.dirname(config_root)

parser = argparse.ArgumentParser()
Options.addNoISAOptions(parser)

# -- Sumcheck workload parameters --
parser.add_argument(
    "--simulate-rounds",
    type=int,
    default=5,
    help="Number of sumcheck rounds to simulate",
)
parser.add_argument(
    "--num-sumcheck-rounds",
    type=int,
    default=15,
    help="Total number of sumcheck rounds (for packet size calc)",
)
parser.add_argument(
    "--poly-degree",
    type=int,
    default=3,
    help="Polynomial degree of the sumcheck polynomial",
)
parser.add_argument(
    "--element-bytes",
    type=int,
    default=32,
    help="Bytes per 256-bit finite field element",
)
parser.add_argument(
    "--multiply-latency",
    type=int,
    default=3,
    help="Cycles for a 256-bit modular multiply",
)
parser.add_argument(
    "--add-latency",
    type=int,
    default=1,
    help="Cycles for a 256-bit modular addition",
)

# -- Hierarchy parameters (only used when topology=SumcheckHierarchy) --

parser.add_argument(
    "--sumcheck-routing",
    type=str,
    default="fixed",
    choices=["fixed", "adaptive"],
    help="Routing option: fixed (select minimal score) "
         "or adaptive ( ~ 1/(score+eps) )"
)
parser.add_argument(
    "--entries-per-cluster",
    type=int,
    default=max(SUPPORTED_ENTRY_COUNTS),
    choices=SUPPORTED_ENTRY_COUNTS,
    help="Number of entry candidates per gateway cluster",
)
parser.add_argument(
    "--entry-congestion-weight",
    type=float,
    default=0.0,
    help="Congestion weight lambda for adaptive routing",
)
parser.add_argument(
    "--sumcheck-seed",
    type=int,
    default=42,
    help="Random seed for SumcheckAdaptive RNG",
)
parser.add_argument(
    "--sumcheck-watchdog-cycles",
    type=int,
    default=100000,
    help="Progress watchdog timeout in ticks. "
         "If no progress for this many ticks, report stuck state and exit.",
)
parser.add_argument(
    "--num-clusters",
    type=int,
    default=DEFAULT_NUM_CLUSTERS,
    help="Number of clusters (gateways) routers in SumcheckHierarchy",
)
parser.add_argument(
    "--root-ni-lanes",
    type=int,
    default=0,
    help="Number of parallel root injection/ejection NI lanes. "
         "0 selects one lane per cluster.",
)

# -- Source placement --
parser.add_argument(
    "--src-x",
    type=int,
    default=None,
    help="X coordinate of the source router (0-indexed)",
)
parser.add_argument(
    "--src-y",
    type=int,
    default=None,
    help="Y coordinate of the source router (0-indexed)",
)
parser.add_argument(
    "--src-center",
    action="store_true",
    default=False,
    help="Place source at the center of the mesh",
)
parser.add_argument(
    "--src-corner",
    action="store_true",
    default=False,
    help="Place source at corner (0,0) of the mesh",
)

#
# Add the ruby specific and protocol specific options
#
Ruby.define_options(parser)

args = parser.parse_args()

assert args.topology in ("MeshSumcheck", "SumcheckHierarchy"), (
    f"Unsupported topology: {args.topology}. "
    "Use --topology=MeshSumcheck or --topology=SumcheckHierarchy"
)

cpus = []
mesh_rows = args.mesh_rows

if args.topology == "MeshSumcheck":
    # -- Determine source router coordinates --
    num_routers = mesh_rows * mesh_rows
    num_workers = num_routers
    num_clusters = args.num_clusters
    if num_clusters <= 0 or num_workers % num_clusters:
        parser.error(
            "Mesh worker count must be divisible by --num-clusters"
        )
    workers_per_cluster = num_workers // num_clusters
    root_ni_lanes = args.root_ni_lanes or num_clusters
    if not 1 <= root_ni_lanes <= num_clusters:
        parser.error(
            "root_ni_lanes must be between 1 and num_clusters"
        )
    args.root_ni_lanes = root_ni_lanes

    root_directory_ids = tuple(
        num_routers + lane for lane in range(root_ni_lanes)
    )
    required_dirs = root_directory_ids[-1] + 1
    min_num_dirs = 1 << (required_dirs - 1).bit_length()
    if args.num_dirs < min_num_dirs:
        args.num_dirs = min_num_dirs
    elif args.num_dirs & (args.num_dirs - 1):
        parser.error("--num-dirs must be a power of two")

    if args.src_x is not None and args.src_y is not None:
        src_x = args.src_x
        src_y = args.src_y
    elif args.src_center:
        src_x = mesh_rows // 2
        src_y = mesh_rows // 2
    else:
        # default: corner (0,0)
        src_x = 0
        src_y = 0

    src_router_id = src_y * mesh_rows + src_x
    args.src_router_id = src_router_id
    num_cpu_controllers = root_ni_lanes + num_workers

    # Override num_cpus (Options.addNoISAOptions sets a default)
    args.num_cpus = num_cpu_controllers

    print(f"Mesh: {mesh_rows}x{mesh_rows} ({num_routers} routers)")
    print(f"Source at ({src_x}, {src_y}), router_id={src_router_id}")
    print(f"Root NI lanes: {root_ni_lanes}")
    print(f"Total L1 controllers: {num_cpu_controllers}")

    worker_router_ids = list(range(num_workers))
    destination_bits = (args.num_dirs - 1).bit_length()

    for worker in range(num_workers):
        source_directory_id = root_directory_ids[
            (worker // workers_per_cluster) % root_ni_lanes
        ]
        cpus.append(SumcheckCausalTraffic(
            node_id=worker,
            node_type=1,
            worker_index=worker,
            workers_per_cluster=workers_per_cluster,
            destination_bits=destination_bits,
            source_id=source_directory_id,
            num_workers=num_workers,
            worker_ids=worker_router_ids,
            num_sumcheck_rounds=args.num_sumcheck_rounds,
            simulate_rounds=args.simulate_rounds,
            poly_degree=args.poly_degree,
            element_bytes=args.element_bytes,
            multiply_latency=args.multiply_latency,
            add_latency=args.add_latency,
            block_offset=6,
            inj_vnet=0,
        ))
    cpus.append(SumcheckCausalTraffic(
        node_id=num_workers,
        node_type=0,
        worker_index=-1,
        workers_per_cluster=workers_per_cluster,
        destination_bits=destination_bits,
        source_id=root_directory_ids[0],
        num_workers=num_workers,
        worker_ids=worker_router_ids,
        num_sumcheck_rounds=args.num_sumcheck_rounds,
        simulate_rounds=args.simulate_rounds,
        poly_degree=args.poly_degree,
        element_bytes=args.element_bytes,
        multiply_latency=args.multiply_latency,
        add_latency=args.add_latency,
        block_offset=6,
        inj_vnet=0,
    ))
else:
    if args.num_clusters <= 0:
        parser.error("--num-clusters must be positive")
    if mesh_rows == 0:
        mesh_rows = DEFAULT_CLUSTER_ROWS
        args.mesh_rows = mesh_rows
    assert args.routing_algorithm == 3, (
        f"Unsupported routing algorithm: {args.routing_algorithm}. "
        "Only routing_alorithm=3 is allowed for SumcheckHierarchy"
    )
    num_clusters = args.num_clusters
    model = HierarchyModel(
        num_clusters=num_clusters,
        rows=mesh_rows,
        cols=mesh_rows,
    )
    root_ni_lanes = args.root_ni_lanes or num_clusters
    try:
        model.check_root_ni_lanes(root_ni_lanes)
    except ValueError as error:
        parser.error(str(error))
    args.root_ni_lanes = root_ni_lanes

    num_workers = model.num_workers
    num_routers = model.num_routers
    src_router_id = model.root
    args.src_router_id = src_router_id

    # Workers have one NI each. The SOURCE tester is connected to
    # root_ni_lanes independent controllers/NIs.
    num_cpu_controllers = num_workers + root_ni_lanes
    args.num_cpus = num_cpu_controllers

    min_num_dirs = model.required_directory_count(root_ni_lanes)
    if args.num_dirs < min_num_dirs:
        args.num_dirs = min_num_dirs
    elif args.num_dirs & (args.num_dirs - 1):
        parser.error("--num-dirs must be a power of two")

    print(f"SumcheckHierarchy: {num_clusters} clusters, "
          f"each {mesh_rows}x{mesh_rows} mesh")
    print(f"Total routers: {num_routers} "
          f"({num_workers} workers + {num_clusters} gateways "
          f"+ 1 root)")
    print(f"Root at router_id={src_router_id}")
    print(f"Root NI lanes: {root_ni_lanes} "
          f"(cluster c uses lane c % {root_ni_lanes})")
    print(f"Total L1 controllers: {num_cpu_controllers}")

    worker_router_ids = list(range(num_workers))
    root_directory_ids = model.root_directory_ids(root_ni_lanes)
    destination_bits = (args.num_dirs - 1).bit_length()

    for i in range(num_workers):
        source_directory_id = root_directory_ids[
            model.lane_for_worker(i, root_ni_lanes)
        ]
        cpus.append(SumcheckCausalTraffic(
            node_id=i,
            node_type=1,
            worker_index=i,
            workers_per_cluster=model.workers_per_cluster,
            destination_bits=destination_bits,
            source_id=source_directory_id,
            num_workers=num_workers,
            worker_ids=worker_router_ids,
            num_sumcheck_rounds=args.num_sumcheck_rounds,
            simulate_rounds=args.simulate_rounds,
            poly_degree=args.poly_degree,
            element_bytes=args.element_bytes,
            multiply_latency=args.multiply_latency,
            add_latency=args.add_latency,
            block_offset=6,
            inj_vnet=0,
        ))
    cpus.append(SumcheckCausalTraffic(
        node_id=src_router_id,
        node_type=0,
        worker_index=-1,
        workers_per_cluster=model.workers_per_cluster,
        destination_bits=destination_bits,
        source_id=root_directory_ids[0],
        num_workers=num_workers,
        worker_ids=worker_router_ids,
        num_sumcheck_rounds=args.num_sumcheck_rounds,
        simulate_rounds=args.simulate_rounds,
        poly_degree=args.poly_degree,
        element_bytes=args.element_bytes,
        multiply_latency=args.multiply_latency,
        add_latency=args.add_latency,
        block_offset=6,
        inj_vnet=0,
    ))

# create the desired simulated system
system = System(cpu=cpus, mem_ranges=[AddrRange(args.mem_size)])

# Create a top-level voltage domain and clock domain
system.voltage_domain = VoltageDomain(voltage=args.sys_voltage)

system.clk_domain = SrcClockDomain(
    clock=args.sys_clock, voltage_domain=system.voltage_domain
)

Ruby.create_system(args, False, system)

# Create a separate clock domain for Ruby
system.ruby.clk_domain = SrcClockDomain(
    clock=args.ruby_clock, voltage_domain=system.voltage_domain
)

# -- Connect tester ports to ruby ports --
for worker in range(num_workers):
    cpus[worker].test = system.ruby._cpu_ports[worker].in_ports
source_tester = cpus[num_workers]
for lane in range(args.root_ni_lanes):
    source_tester.test = system.ruby._cpu_ports[
        num_workers + lane
    ].in_ports

# -- Set NI sumcheck_tester for notifyArrival callback --
# The NI's sumcheck_tester is set from GarnetNetwork.py's Param.
# We need to wire it here because the NI instances are created
# inside Ruby.create_system and we need to match them to testers.
# RubySequencer connects to NI via the network. The NI list is
# in system.ruby.network.netifs, indexed in the same order as
# the L1 controllers (which are in the same order as cpus).

directory_ni_base = num_cpu_controllers
for worker in range(num_workers):
    system.ruby.network.netifs[
        directory_ni_base + worker
    ].sumcheck_tester_worker = cpus[worker]
for directory_id in root_directory_ids:
    system.ruby.network.netifs[
        directory_ni_base + directory_id
    ].sumcheck_tester_src = source_tester

# -- Run simulation --
root = Root(full_system=False, system=system)
root.system.mem_mode = "timing"

# Not much point in this being higher than the L1 latency
m5.ticks.setGlobalFrequency("500ps")

# instantiate configuration
m5.instantiate()

# simulate until program terminates
exit_event = m5.simulate(args.abs_max_tick)

print("Exiting @ tick", m5.curTick(), "because", exit_event.getCause())
