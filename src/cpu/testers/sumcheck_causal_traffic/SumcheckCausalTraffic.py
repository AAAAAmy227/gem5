from m5.objects.ClockedObject import ClockedObject
from m5.params import *
from m5.proxy import *


class SumcheckCausalTraffic(ClockedObject):
    type = "SumcheckCausalTraffic"
    cxx_header = "cpu/testers/sumcheck_causal_traffic/SumcheckCausalTraffic.hh"
    cxx_class = "gem5::SumcheckCausalTraffic"

    block_offset = Param.Int(6, "block offset in bits")
    node_id = Param.Int(0, "Node ID of this tester")
    node_type = Param.Int(0, "Node type: 0=SOURCE, 1=WORKER, 2=NEITHER")
    source_id = Param.Int(0, "Source node ID (for workers to send back to)")
    num_workers = Param.Int(1, "Number of worker nodes")
    worker_ids = VectorParam.Int([], "List of worker node IDs")
    num_sumcheck_rounds = Param.Int(10, "Total number of sumcheck rounds")
    simulate_rounds = Param.Int(3, "Number of rounds to simulate")
    poly_degree = Param.Int(3, "Polynomial degree")
    element_bytes = Param.Int(32, "Bytes per 256-bit element")
    multiply_latency = Param.Int(3, "Cycles for 256-bit multiply mod prime")
    add_latency = Param.Int(1, "Cycles for 256-bit addition")
    inj_vnet = Param.Int(2, "Vnet to inject packets in")

    test = RequestPort("Port to the memory system to test")
    system = Param.System(Parent.any, "System we belong to")
