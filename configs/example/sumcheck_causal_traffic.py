import m5
from m5.objects import *
from m5.defines import buildEnv
from m5.util import addToPath
import os, argparse, sys

addToPath("../")

from common import Options
from ruby import Ruby

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

# -- Determine source router coordinates --
mesh_rows = args.mesh_rows
num_routers = mesh_rows * mesh_rows

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
num_cpus = num_routers + 1  # 1 SOURCE + num_routers WORKERs

# Override num_cpus (Options.addNoISAOptions sets a default)
args.num_cpus = num_cpus

print(f"Mesh: {mesh_rows}x{mesh_rows} ({num_routers} routers)")
print(f"Source at ({src_x}, {src_y}), router_id={src_router_id}")
print(f"Total CPUs: {num_cpus} (1 SOURCE + {num_routers} WORKERs)")

# -- Create SumcheckCausalTraffic instances --
# CPU 0 = SOURCE, CPU 1..num_routers = WORKERs

router_to_worker = {}
router_to_worker[src_router_id] = [0, 1]
other_routers = [r for r in range(num_routers) if r != src_router_id]
for i in range(2, num_cpus):
    router_to_worker[other_routers[i - 2]] = [i]

cpus = []
worker_router_ids = []

for cpu_id in range(1, num_cpus):
    if cpu_id == 1:
        router_id = src_router_id
    else:
        router_id = other_routers[cpu_id - 2]
    worker_router_ids.append(router_id)

for i in range(num_cpus):
    tester = SumcheckCausalTraffic(
        node_id=i,
        node_type=0 if i == 0 else 1,  # 0=SOURCE, 1=WORKER
        source_id=src_router_id,
        num_workers=num_routers,
        worker_ids=worker_router_ids,
        num_sumcheck_rounds=args.num_sumcheck_rounds,
        simulate_rounds=args.simulate_rounds,
        poly_degree=args.poly_degree,
        element_bytes=args.element_bytes,
        multiply_latency=args.multiply_latency,
        add_latency=args.add_latency,
        block_offset=6,
        inj_vnet=0,
    )
    cpus.append(tester)

# create the desired simulated system
system = System(cpu=cpus, mem_ranges=[AddrRange(args.mem_size)])

# Create a top-level voltage domain and clock domain
system.voltage_domain = VoltageDomain(voltage=args.sys_voltage)

system.clk_domain = SrcClockDomain(
    clock=args.sys_clock, voltage_domain=system.voltage_domain
)

# Set src_router_id on args so MeshSumcheck topology can read it
args.src_router_id = src_router_id

# Set topology to MeshSumcheck
args.topology = "MeshSumcheck"

Ruby.create_system(args, False, system)

# Create a separate clock domain for Ruby
system.ruby.clk_domain = SrcClockDomain(
    clock=args.ruby_clock, voltage_domain=system.voltage_domain
)

# -- Connect tester ports to ruby ports --
for i in range(num_cpus):
    cpus[i].test = system.ruby._cpu_ports[i].in_ports

# -- Set NI sumcheck_tester for notifyArrival callback --
# The NI's sumcheck_tester is set from GarnetNetwork.py's Param.
# We need to wire it here because the NI instances are created
# inside Ruby.create_system and we need to match them to testers.
# RubySequencer connects to NI via the network. The NI list is
# in system.ruby.network.netifs, indexed in the same order as
# the L1 controllers (which are in the same order as cpus).


for router_id in range(num_routers):
    dir_ni = system.ruby.network.netifs[num_cpus + router_id]
    workers = router_to_worker.get(router_id, [])
    for cpu_idx in workers:
        tester = cpus[cpu_idx]
        if int(tester.node_type) == 0:
            dir_ni.sumcheck_tester_src = tester
        elif int(tester.node_type) == 1:
            dir_ni.sumcheck_tester_worker = tester

system.ruby.network.netifs[0].sumcheck_tester_src = cpus[0]
for i in range(1, num_cpus):
    system.ruby.network.netifs[i].sumcheck_tester_worker = cpus[i]

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
